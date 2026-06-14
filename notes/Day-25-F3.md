# Day 25 — Impact Classifier v1 (High/Med/Low/N-A)

**Date:** 2026-06-13
**Feature:** F3 — Policy Impact Mapping (Week 4, Day 4 of 7)
**KM:** #17/#20 LogReg/XGBoost (documented as future calibration path, not built v1)
**Status:** Classifier built, tested, run on real data. dense_score turned out to be a genuinely useful signal — with one honest caveat.

---

## What Was Built

| File | Change |
|------|--------|
| `src/f3_impact/matcher.py` | Each match now carries `dense_score` (cosine similarity) alongside `score` (RRF) |
| `src/f3_impact/classifier.py` | `classify_impact()`, `classify_matches()`, `ImpactLevel` enum — threshold-based v1 |
| `tests/test_f3_classifier.py` | 3 tests: threshold boundaries, end-to-end classification, empty-matches case |
| `data/f3_indexes/impact_results.json` | Generated: 251 matches, each with `impact_level` |
| `docs/wireframes/section-output-ux-v1.md` | Product: per-section impact card |
| `docs/ARCHITECTURE.md` | New entries |

---

## Roadmap v2.2 — Day 25 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | #17/#20 LogReg/XGBoost | Documented as the Day 26+ upgrade path (needs labeled data); v1 uses explainable thresholds instead |
| Engineering | Impact classifier High/Med/Low/N/A | `classifier.py` — `classify_impact(dense_score)` with 0.55/0.45/0.35 thresholds |
| Product | Section-level output UX | `docs/wireframes/section-output-ux-v1.md` — per-section card, ranked matches with impact badges |
| Deliverable | Impact classifier | Run on real data: 251 matches classified — 27 High, 47 Medium, 78 Low, 99 N/A |

---

## Why dense_score, Not RRF Score

Day 24 found RRF scores cluster near their floor (~0.03) — almost no
separation between sections. `dense_score` (cosine similarity from the
mpnet embedding) has real range: 0.21 to 0.79 across today's run. That
range is exactly what a threshold rule needs.

```python
HIGH_THRESHOLD = 0.55
MEDIUM_THRESHOLD = 0.45
LOW_THRESHOLD = 0.35
```

---

## Verified Results

```
Impact level distribution across all matches:
  high            27
  medium          47
  low             78
  not_applicable  99
```

A healthy-looking distribution — not everything dumped into one bucket.

---

## The Good News: Some HIGH Matches Are Genuinely Correct

`Fair-Lending-ECOA-Policy` is literally about ECOA/Regulation B — and the
classifier found real signal:

```
§2.1 (Prohibited Bases Under ECOA/Regulation B) -> HIGH
    "Equal Credit Opportunity Act (Regulation B)"  dense=0.761

§3.3 (Special Purpose Credit Programs (SPCP)) -> HIGH
    "Equal Credit Opportunity Act (Regulation B)"  dense=0.789

§8.2 (Training Topics) -> HIGH
    "Equal Credit Opportunity Act (Regulation B)"  dense=0.765
```

These are exactly the kind of match F3 exists to surface — a real
regulation in the DB (Federal Register's "Equal Credit Opportunity Act
(Regulation B)") correctly identified as highly relevant to the ECOA
policy's most directly-related sections. **dense_score is a real signal.**

---

## The Honest Caveat: One Document Dominates

The same "Equal Credit Opportunity Act (Regulation B)" document also
shows up as HIGH or MEDIUM against **BSA-AML-Policy** and
**TRID-Mortgage-Disclosure-Policy** sections — policies that aren't
primarily about ECOA:

```
BSA-AML-Policy §10.2 (Consequences) -> HIGH
    "Equal Credit Opportunity Act (Regulation B)"  dense=0.557

TRID-Mortgage-Disclosure-Policy §3.1 (Closing Disclosure Timing) -> HIGH
    "Equal Credit Opportunity Act (Regulation B)"  dense=0.581
```

**Likely cause:** "Equal Credit Opportunity Act (Regulation B)" is one of
the longest, most detailed regulatory documents in the 25-doc corpus —
its chunks contain a lot of general banking-compliance language
("institution," "must," "requirement," "disclosure") that embeds
moderately close to *any* policy section, regardless of actual topical
relevance.

**This is not necessarily wrong** — TRID §3.1 (Closing Disclosure Timing)
*could* legitimately relate to Reg B's disclosure requirements. But it
could also be a false positive driven by generic compliance vocabulary
rather than substantive overlap. **Only labeled data can tell us which.**

---

## Why This Is Exactly What Day 26 Is For

This is the calibration question Day 26's 30 labeled pairs must answer:
- Are TRID §3.1 / BSA §10.2 vs. "Reg B" correctly HIGH, or false positives
  from a long, generic document dominating the embedding space?
- Do the 0.55/0.45/0.35 thresholds need to move?
- Would a trained classifier (KM #17/#20, LogReg over `[dense_score,
  rrf_score, bm25_keyword_overlap]`) separate "topically relevant" from
  "generically similar" better than dense_score alone?

**No changes made today** — the v1 classifier is documented as exactly
that: v1, with real findings (good and caveated) for Day 26 to validate
against ground truth.

---

## PM Insight: Two Findings, Both Worth Having

Day 24 found a *data coverage* problem (no CTR-specific regulations
exist in the dev DB). Day 25 found a *signal quality* problem (one long
generic document may be over-matching). Both are the kind of finding
that only shows up when you run the real pipeline on real data — and
both are exactly what Day 26's labeled eval exists to quantify and fix.

The pipeline is now end-to-end: extractor -> dual index -> hybrid
matcher -> classifier -> `impact_results.json`. Day 26 isn't "build the
eval pipeline in the abstract" — it's "use the 30 labeled pairs to find
out if today's 27 HIGH findings are mostly right or mostly wrong."

---

## Next: Day 26 (when user says "next")

Per roadmap v2.2: KM #246 Golden dataset | Eng: Label 30 reg-policy pairs,
build F3 eval pipeline, CI gate 80% | Product: Build vs buy matrix |
Deliverable: F3 eval pipeline live; 30 pairs labeled.

This is the big one — it directly tests today's two findings (the good
ECOA matches and the questionable cross-policy "Reg B" matches) against
human judgment.
