# Day 10 — F2 Hierarchical Chunking + Explainability Modal

**Date:** 2026-06-02
**Feature:** F2 — AI Summarisation
**KM:** #154–155 Structure-aware chunking
**Status:** Complete — hierarchical chunker built, effective date extracted from 400K doc

---

## What Was Built

| File | Change |
|------|--------|
| `src/f2_summarise/chunker.py` | Added `chunk_hierarchical()` — 6th strategy with table detection, header detection, priority flags |
| `src/f2_summarise/retriever.py` | Priority score boosts for is_date_section (+50), is_institution_section (+30), is_table (+20) |
| `src/f2_summarise/summariser.py` | DEFAULT_CHUNK_STRATEGY = "hierarchical" |
| `docs/wireframes/explainability-modal-v1.md` | Source citations UI — field-level traceability |

---

## Benchmark: Hierarchical vs All Strategies

| Strategy | Score | Key finding |
|----------|-------|-------------|
| sentence | 0.802 | Day 9 winner |
| **hierarchical** | **0.802** | Ties sentence on Fed press releases (no headers to detect) |
| recursive | 0.796 | — |
| regulatory | 0.796 | — |
| fixed_size | 0.638 | — |
| paragraph | 0.383 | — |

**Why hierarchical ties sentence on our test set:**
Our 20 benchmark documents are Fed press releases — short, 800–3,000 chars, no document structure headers. The hierarchical chunker's fallback is sentence splitting, so output is identical. On the 400K CFPB Regulation B (which has real structure), hierarchical pulled up Chunk 365 (effective date) from deep in the document — sentence splitting would have missed it.

---

## Live Test: 400,865-Character CFPB Document

**Document:** Equal Credit Opportunity Act (Regulation B)
**Chunks generated:** 470 (avg 852 chars each)
**Chunks retrieved:** 7 (1.5% of the document)
**Key chunk:** Chunk 365 — effective date buried 365 chunks deep
**Result:** `effective_date: "2026-07-21"` correctly extracted

Without priority retrieval, the retriever would have scored Chunk 365 low (it uses "effective" without a year pattern — "effective July 21, 2026" has the date in a different sentence). The `is_date_section=True` flag boosted it to the top.

---

## KM Concept: #154–155 Structure-Aware Chunking

**What hierarchical chunking does differently:**

Standard chunker sees a 400K document as a flat sequence of characters.

Hierarchical chunker sees:
```
[Document header: PART II — CFPB — 12 CFR Part 1002]
  [Section I: Background]
    [Paragraph 1: ...history of ECOA...]
    [Paragraph 2: ...prior rulemaking...]
  [Section II: Legal Authority]
    [Paragraph 1: ...authority under Dodd-Frank...]
  [Section III: Final Rule Provisions]
    [Subsection A: Disparate Impact]
    [Subsection B: Discouragement]
    [Subsection C: Special Purpose Credit Programs]
  [Section IV: Effective Date and Compliance]   ← IS_DATE_SECTION = True
    [Paragraph: "The final rule is effective July 21, 2026..."]
  [Section V: Regulatory Analyses]
```

Priority retrieval then always includes Section IV regardless of keyword score.

**The three layers of hierarchy:**
1. **Document header** — always chunk 0, always retrieved
2. **Section headers** — tag content with metadata (date section, institution section)
3. **Prose within sections** — sentence-split into sub-chunks

This mirrors how a compliance officer reads a regulation: skim headers, read relevant sections, skip others.

---

## Explainability Modal — Why It's a Trust Feature

The modal shows Sarah which chunk backed each summary field. This serves three purposes:

1. **Verification** — Sarah can spot-check Claude's work in 30 seconds instead of reading the whole document
2. **SR 11-7 compliance** — AI-assisted decisions must be traceable to their source
3. **Trust calibration** — when Sarah sees that the effective date came from "Section IV: Effective Dates", she trusts it more than if it came from "Chunk 42 (general text)"

The `source_citations` field is already in the JSON schema and Claude already populates it. The modal is a UI wrapper around data that already exists.

**Current gap:** Chunks aren't stored in DB. Modal re-chunks on demand for MVP.

---

## PM Insight

**Explainability is a product moat, not just a compliance checkbox.**

Wolters Kluwer charges $50K–$200K per year and gives compliance officers a result. RegWatch AI gives them a result AND shows the work. When Sarah can click "View citations" and see exactly where each field came from, she trusts the tool at a level that black-box tools never achieve.

This matters for the enterprise sale too. An examiner reviewing RegWatch AI's outputs will ask: "How do you know this?" The explainability modal is the answer. Without it, you're asking the examiner to trust an AI. With it, you're showing them the primary source — the same standard they'd apply to human work.

---

## Total Tests

66 unit + 7 integration = 73 total. All passing.

---

## F2 Pipeline — Current State After Day 10

```
raw_content (400K chars)
    ↓ chunk_hierarchical()
470 chunks — headers tagged, tables preserved, date/inst sections flagged
    ↓ retrieve_top_chunks() with priority boosts
7 chunks — date sections always included regardless of keyword score
    ↓ format_chunks_for_prompt()
"[Chunk 365 [DATE SECTION] — Section: IV. Effective Date]\n..."
    ↓ Claude (claude-sonnet-4-20250514, temp=0.2)
{
  "effective_date": "2026-07-21",   ← from Chunk 365
  "affected_institution_types": ["banks", "credit unions"],  ← from Chunk 435
  "confidence_score": 75,
  ...
}
    ↓ write to DB
summary_json saved, status="summarised", review_flag=True (conf < 80)
    ↓ AuditLog
action=SUMMARISE, model=claude-sonnet-4-20250514, chunks_used=7
```
