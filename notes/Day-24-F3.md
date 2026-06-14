# Day 24 — Similarity Matcher v1

**Date:** 2026-06-13
**Feature:** F3 — Policy Impact Mapping (Week 4, Day 3 of 7)
**KM:** #159-160 Hybrid search
**Status:** Hybrid matcher built, tested, and run against real data. Important data-coverage gap surfaced.

---

## What Was Built

| File | Change |
|------|--------|
| `src/f3_impact/matcher.py` | `HybridMatcher` — dense + BM25 + RRF matching, `build_matches()` |
| `tests/test_f3_matcher.py` | 4 tests: RRF combine logic, end-to-end matching on fake index |
| `data/f3_indexes/matches.json` | Generated: 72 sections x up to 5 matches each |
| `docs/wireframes/impact-dashboard-v1.md` | Added matches.json field map + Day 24 findings |
| `docs/ARCHITECTURE.md` | New entry for `matcher.py` |

---

## Roadmap v2.2 — Day 24 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | #159-160 Hybrid search | `HybridMatcher` combines dense (`VectorIndex.query`) + BM25 (`rank_bm25`) via RRF — same approach F2 validated Day 16, `RRF_K=60` reused |
| Engineering | Semantic similarity: regulation chunk <-> policy section matching | `match_chunks()` / `match_section()` — chunk-level RRF, collapsed to per-regulation-document |
| Product | Gap detail view | Field map added to `impact-dashboard-v1.md` connecting `matches.json` -> wireframe panels |
| Deliverable | Similarity matcher v1 | `matcher.py`, run against real indexes: 72 sections, 252 matches |

---

## How It Works

For each policy section's text:
1. **Dense**: `regulation_chunks_index.query(text, top_k=20)` — semantic similarity via mpnet embeddings
2. **BM25**: `BM25Okapi` over all 521 chunk texts, ranked by keyword overlap, top 20
3. **RRF**: combine both rankings — `1/(60+rank_dense) + 1/(60+rank_bm25)` — items ranked highly by *both* methods win
4. **Collapse**: chunk-level results -> one row per regulation document (max score, best chunk kept as evidence)
5. Keep top 5 regulations per policy section

All 4 new tests pass, plus the existing 8 F3 tests (12 total).

---

## Verified Results — and an Honest Finding

```
72 policy sections processed, 252 regulation matches found
```

Sample — `BSA-AML-Policy §1.2 - Scope`:
```
0.0323  [cfpb] Equal Credit Opportunity Act (Regulation B)
0.0287  [fed] Federal Reserve Board requests public comment on a proposal...
```

But `BSA-AML-Policy §4.2 - Currency Transaction Reporting (CTR)` — the section
that *should* match a CTR-related regulation — only got:
```
0.0315  [fed] Federal Reserve Board announces it does not object to...
0.0308  [cfpb] Equal Credit Opportunity Act (Regulation B)
0.0303  [fed] Federal Reserve Board issues enforcement action...
```

**This is not a matcher bug.** RRF scores around 0.03 are near the
mathematical floor (`~1/61 + 1/61 ≈ 0.033` for a rank-1/rank-1 hit on
*both* lists) — the matcher is honestly reporting "these are the least
irrelevant of what's available," not "these are strong matches."

**Root cause:** the 25 summarised documents currently in the DB are
whatever the F1 ingestor happened to pull recently (Fed press releases,
ECOA/Reg B items, enforcement actions) — none are about CTR thresholds,
SAR filing, or mortgage disclosure timing, which is what the BSA/TRID/ECOA
policy fixtures actually need to be checked against.

---

## Why This Matters for Day 25-26

Day 25's impact classifier must treat a low RRF score (~0.03, near floor)
as a signal for **Low or N/A impact**, not force every section into
High/Medium just because *something* was returned. A naive classifier
that says "top match exists, therefore Medium impact" would be wrong here
— it would flag §4.2 against an unrelated ECOA document.

Day 26's eval set (`fixtures/golden/impact_pairs.json`, 30 labeled pairs)
is described in CLAUDE.md as **hand-labeled** — meaning it should be
built from *deliberately chosen* regulation-policy pairs (e.g., take a
real CTR-related regulation text and pair it with BSA §4.2), not sampled
from whatever 25 docs happen to be in the dev DB. This was already the
plan, but Day 24's run makes the reason concrete: the current DB content
doesn't have good ground truth for these 3 policies.

**No action taken today** — flagging for Day 26 planning. The matcher
itself is correct and ready; it just needs regulation content worth
matching against.

---

## PM Insight: A "Working" Pipeline vs. a "Useful" Pipeline

Every piece built so far — extractor, dual index, hybrid matcher — works
exactly as designed and is fully tested. But Day 24's run against real
data reveals the gap between "the code runs correctly" and "the output
is useful to Sarah." A heatmap full of 0.03-score, low-confidence matches
to unrelated Fed press releases would actively erode trust in F3 on day one.

This is exactly why CLAUDE.md's eval-first rule and the Day 26 golden set
exist — Day 25's classifier needs a calibrated sense of "what does a real
High-impact match's score look like?" and the only way to know that is
with deliberately-paired data, which Day 26 will build.

---

## Next: Day 25 (when user says "next")

Per roadmap v2.2: KM #17/#20 LogReg/XGBoost | Eng: Impact classifier
High/Med/Low/N/A | Product: Section-level output UX | Deliverable: Impact
classifier.

Given today's finding, Day 25's classifier design should explicitly use
score thresholds calibrated to "what does floor-level noise look like"
(~0.03) vs. a real signal — even before Day 26's labeled set exists, the
classifier shouldn't label everything "Medium" by default.
