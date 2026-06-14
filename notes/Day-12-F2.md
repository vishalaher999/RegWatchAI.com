# Day 12 — F2 NER: Date & Entity Extraction

**Date:** 2026-06-02
**Feature:** F2 — AI Summarisation
**KM:** #82 NER (Named Entity Recognition)
**Status:** Complete — NER pipeline live, 90/90 tests passing

---

## What Was Built

| File | Purpose |
|------|---------|
| `src/f2_summarise/ner.py` | Date extractor (regex), institution type extractor, citation extractor, cross-validation |
| `src/f2_summarise/summariser.py` | NER wired in post-LLM, confidence adjustment, NER fields in AuditLog |
| `docs/wireframes/fallback-ux-v1.md` | Three failure states + NER-filled field indicator + review queue |
| `tests/test_f2_ner.py` | 24 NER tests — date patterns, institution types, classification, cross-validation |

---

## KM Concept: #82 Named Entity Recognition (NER)

NER = identifying and classifying named entities in text.
General NER: people, organisations, locations, dates.
Regulatory NER (what we built): effective dates, compliance deadlines, institution types, regulation citations.

**Two approaches to NER:**

| Approach | How | When to use |
|----------|-----|-------------|
| Rule-based (ours) | Regex patterns + context classification | Highly predictable patterns (dates, § citations, institution names) |
| ML-based (e.g. spaCy) | Trained model on labeled corpus | Complex, ambiguous entities needing semantic understanding |
| LLM-based | Prompt Claude to extract entities | Ambiguous/contextual entities ("the deadline in the last paragraph") |

We use rule-based because regulatory date formats are highly predictable — "January 1, 2027", "2027-01-01", "Jan. 1, 2027" cover >90% of cases. Regex finds them in microseconds with zero cost and zero hallucination risk. The LLM handles the semantic interpretation ("what does this date mean?") not the pattern matching ("is this text a date?").

---

## Date Classification Algorithm

```
for each date found:
    look at context_before[-40:] and context_after[:40]
    
    if "takes effect on / becomes effective / in effect on" in before:
        → effective date
    if "must comply by / compliance deadline / no later than" in before:
        → compliance deadline
    if effective context in after:
        → effective (secondary signal)
    if compliance context in after:
        → compliance (secondary signal)
    else:
        → general date
```

**Key engineering lesson from Day 12:** Context window size matters enormously for NER classification. A 120-char window picked up "takes effect on" from a previous sentence when classifying the next date. A 40-char window correctly sees only the immediate phrase before each date. This is a common NER pitfall — the window must be large enough to capture the context phrase but small enough to not pick up adjacent sentences.

---

## Cross-Validation Logic

```python
# LLM said "effective_date": "2026-07-21"
# NER found "2026-07-21" as effective date
# → Agreement → confidence_delta += 5

# LLM said "effective_date": null
# NER found "2027-01-01" as effective date
# → NER fills null → summary["effective_date"] = "2027-01-01"
# → confidence_delta = 0 (one source, not verified)

# LLM said "effective_date": "2026-06-01"
# NER found "2026-07-21" as effective date
# → Disagreement → confidence_delta -= 5
# → summary["_ner_effective_date_conflict"] = "2026-07-21"
```

The AuditLog now contains `ner_effective_date`, `ner_compliance_deadline`, `confidence_delta_from_ner` — making NER's contribution traceable.

---

## Why Short Fed Press Releases Show No NER Dates

The 5 test documents are Fed press releases (700-2,000 chars). They don't contain explicit "effective date:" sections — they're announcements, not regulations. NER returns no dates for these, which is correct. NER will show significant value on structured documents like:
- Federal Register rules with "Effective Date" sections
- CFPB final rules (400K chars, explicit date sections)
- FinCEN guidance with compliance deadlines

The CFPB Reg B document (400K chars) had the July 21 effective date correctly extracted by NER in Day 10 — the same extraction pipeline now cross-validates against the LLM output.

---

## Tests: 90 Passing

| Suite | Tests |
|-------|-------|
| F1: classifier | 14 |
| F1: dedup | 4 |
| F1: anomaly | 10 |
| F1: fulltext | 16 |
| F2: summariser | 22 |
| F2: NER | 24 |
| **Total fast** | **90** |
| F1: integration | 7 |

---

## PM Insight

**NER is the "second opinion" for dates.**

Without NER: Claude says "effective_date: null" → Sarah either accepts null or reads the full 400K document.

With NER: Claude says "effective_date: null" → NER scans full document → finds "July 21, 2026" in section IV → fills field → AuditLog shows NER as source → Sarah sees "[NER]" badge → knows to verify before acting.

This is the difference between "the AI doesn't know" and "the AI doesn't know but here's what pattern-matching found." The second is more useful. The badge is a trust mechanism: it tells Sarah exactly how confident to be in each field and where the information came from.

The cross-validation logic also provides a self-check: if LLM and NER agree on a date, confidence goes up. If they disagree, confidence goes down and the document goes to the review queue. Two independent methods disagreeing is evidence that something is ambiguous — exactly the right time to route to human review.
