# Day 30 — Multi-Query Retrieval (KM #164): First Accuracy Gain Since Day 27

**Date:** 2026-06-13
**Feature:** F3 — Policy Impact Mapping (Week 5, Day 2 of 7)
**KM:** #164 Multi-query retrieval for complex cross-references in regulations
**Status:** Multi-query retrieval implemented in `HybridMatcher`. Accuracy
improved 73.3% (22/30) -> **76.7% (23/30)**. `REGRESSION_BASELINE` ratcheted
up to 23/30. Progressive Autonomy Roadmap published.

---

## What Was Built

| File | Change |
|------|--------|
| `src/f3_impact/matcher.py` | New `HybridMatcher.match_section_multi_query(query_text, policy_name)`, `_merge_chunk_matches()`, `_collapse_to_docs()` (refactored out of `match_section`). `build_matches()` now calls `match_section_multi_query`. |
| `tests/test_f3_matcher.py` | +3 tests: chunk-merge logic, no-named-regulation fallback (identical to single query), extra-query-per-named-regulation. 7 tests total. |
| `evals/f3_eval.py` | `REGRESSION_BASELINE` ratcheted from 0.70 -> 23/30 (0.7667), with updated comment. |
| `tests/test_f3_eval.py` | Updated docstring for the regression test. |
| `data/f3_indexes/matches.json`, `impact_results.json` | Regenerated (gitignored). New distribution: 27 high / 1 medium / 21 low / 198 N/A (was 24/1/14/212). |
| `docs/Progressive-Autonomy-Roadmap-v1.md` | NEW — staged HITL -> automation roadmap, gated on per-class precision. |
| `docs/ARCHITECTURE.md` | Updated `matcher.py` and `evals/f3_eval.py` entries; new entry for the roadmap doc. |

---

## Roadmap v2.2 — Day 30 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | #164 Multi-query retrieval for complex cross-references in regulations | Implemented in `HybridMatcher.match_section_multi_query()` |
| Engineering | Multi-query retrieval for complex cross-references in regulations | `matcher.py` + `tests/test_f3_matcher.py` |
| Product | Progressive autonomy roadmap — HITL → gradual automation | `docs/Progressive-Autonomy-Roadmap-v1.md` |
| Deliverable | Improved F3 matcher | 73.3% -> 76.7% (22/30 -> 23/30) |

---

## What Changed and Why

Day 29 concluded that global embedding-level and threshold-level adjustments
both hit the same kind of ceiling on the 30-pair set: a single adjustment
can't fix Case A without breaking Case B when they differ only in degree, not
kind. The two paths forward were (1) per-pair/per-regulation-type signals, or
(2) a trained classifier.

Multi-query retrieval is path (1), applied at the QUERY side instead of the
embedding or threshold side. For each policy section, `citations.py` already
knows which regulations the policy itself names (`get_named_regulations()`).
Day 30 uses that same signal to issue ADDITIONAL retrieval queries — one per
named regulation, each combining the section text with that regulation's
name — so a policy section that references multiple regulatory frameworks in
one (diluted) embedding gets a dedicated search pass per framework.

`_merge_chunk_matches()` combines the chunk-level results from all queries by
keeping the best `rrf_score` and `dense_score` seen for any chunk across all
queries, then the existing collapse-to-per-document logic runs unchanged.
Policies citing no recognizable regulations (none of the current 3 fixtures
lack this, but future ones might) fall back to exactly one query — provably
identical to the old `match_section()` (tested directly).

---

## Result

```
Accuracy: 23/30 = 76.7%  (was 22/30 = 73.3%)
CI gate target: >= 80% — still FAIL, but closer (3.4 pts gained)

Confusion matrix (true -> predicted):
                              high          medium             low  not_applicable
            high                10               0               0               0
          medium                 1               0               2               0
             low                 0               0               5               1
  not_applicable                 0               0               3               8
```

**Fixed since Day 27:** pair #9 (BSA §10.2 vs Reg B, was LOW -> now correctly
NOT_APPLICABLE) and pair #24 (no longer a mismatch).

**Newly broken:** pair #21 (Fair-Lending-ECOA §3.4 vs Reg B, true MEDIUM —
was correctly LOW under Day 27, now over-predicted HIGH). Net: -1 mismatch on
the BSA/TRID-vs-Reg-B pattern outweighs +1 new mismatch on a true-MEDIUM ECOA
pair. 22 -> 23 net gain.

**Remaining 7 mismatches** (#10, #13, #14, #15, #19, #21, #28) are still
dominated by the same generic-regulation-vs-unrelated-policy and
generic-Federal-Register-notice patterns Day 27/29 diagnosed — multi-query
helped at the margins (BSA §10.2's own query for its named regulations now
pulls in more specific competing matches that outrank the generic Reg B
chunk) but didn't eliminate the pattern.

---

## Precision Table (new, drives the autonomy roadmap)

| Predicted class | Total predicted | Correct | Precision |
|---|---|---|---|
| HIGH | 11 | 10 | 90.9% |
| MEDIUM | 0 | 0 | n/a |
| LOW | 10 | 5 | 50.0% |
| NOT_APPLICABLE | 9 | 8 | 88.9% |

HIGH and NOT_APPLICABLE are both ~90% — the two most reliable predicted
classes. LOW is a coin flip. MEDIUM has never been predicted by the
classifier, so it has zero data points. `docs/Progressive-Autonomy-Roadmap-v1.md`
uses this table as the gating mechanism for staged automation — Stage 1
surfaces HIGH/NOT_APPLICABLE findings without a review-queue delay; LOW/MEDIUM
stay fully manual.

---

## PM Insight

Today's result is genuinely good news, but the SIZE of the gain (+3.4 pts)
matters as much as its direction. This is a query-side, per-regulation signal
— exactly the "non-uniform" lever Day 29 said was missing — and it produced
the first net improvement since Day 27's named-regulation-match feature
(+33.3 pts). The fact that this lever moved the needle by single digits, not
double digits, is itself informative: it suggests the remaining ~7 errors are
genuinely hard cases (generic regulatory boilerplate vs. substantive overlap)
that need either more/better golden-set examples to calibrate against, or a
trained classifier (KM #17/#20) — not another query- or threshold-side trick.
That's a more specific Week 5 conclusion than Day 29's, and it's consistent
with both.

The Progressive Autonomy Roadmap turns today's confusion matrix into a
forward-looking artifact: instead of treating 76.7% as one number to compare
against 80%, it breaks the number down by WHICH KINDS of F3 output Sarah
could eventually trust more, and ties that directly to F4's design.

---

## Next: Day 31 (when user says "next")

Per roadmap v2.2 — confirm Day 31's columns before starting (build rule 3) —
do not start Day 31 without explicit "next".
