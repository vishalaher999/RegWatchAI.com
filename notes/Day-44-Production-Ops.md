# Day 44 — Cost Dashboard + Final Eval + SD1 + Portfolio (KM #239/#258, Week 7 Day 2)

**Date:** 2026-06-14
**Roadmap:** Week 7 ("Integration + Portfolio"), Day 2 of 3

---

## What Was Built

| Artifact | Type | Status |
|---|---|---|
| `src/f2_summarise/summariser.py` | EDIT | `_call_claude` now returns token usage; logged to `AuditLog(SUMMARISE)` |
| `scripts/cost_dashboard.py` | NEW | Done — $/query dashboard from F2 token usage |
| `tests/test_cost_dashboard.py` | NEW | 3 tests, passing |
| `tests/test_f2_tracing.py` | EDIT | Updated 3-tuple unpacking for `_call_claude` |
| `evals/final_eval_report.json` | NEW | Final RAGAS eval on the 50-entry golden set |
| `docs/SD1-System-Design-v1.md` | NEW | System design doc — all 5 features + data flow |
| `docs/Portfolio-Page-v1.md` | NEW | Portfolio page content |
| `docs/ARCHITECTURE.md` | EDIT | Day 44 entries added |

---

## Roadmap — Day 44 columns

| Column | Content |
|---|---|
| KM reference | #239 (Cost dashboard), #258 (Final eval) |
| Engineering | Cost dashboard ($/query); final RAGAS eval on golden examples; SD1 system design doc finalized |
| Product | SD1: RegWatch architecture (all 5 features + data flow); portfolio page live |
| Deliverable | Production ops + SD1 + portfolio |

---

## What Changed and Why

**`src/f2_summarise/summariser.py`** — `_call_claude` now reads
`response.usage.input_tokens`/`output_tokens` (via `getattr` with 0/0
defaults so test doubles without a `.usage` attribute don't break) and
returns them as a third tuple element. `summarise_document` threads this
through to the `AuditLog(SUMMARISE)` payload as `input_tokens`/
`output_tokens`, alongside the existing `model` and `prompt_version`. This
is the only production-code change today — everything else is new
scripts/docs/tests built on top of it.

**`scripts/cost_dashboard.py`** sums tokens per model from
`AuditLog(SUMMARISE)` rows and converts to USD with a hardcoded
`PRICING_PER_MTOK` table (Sonnet 4 $3/$15 per MTok in/out, Haiku 4.5 $1/$5 —
published Anthropic list pricing as of this build; update the constant if
pricing changes). Rows without token data (everything summarised before
today) are excluded from `queries_with_token_data` rather than counted as
$0 — otherwise the cost-per-query average would be artificially diluted.
Run live against the dev DB: 95 `SUMMARISE` rows, 0 with token data (all
pre-Day-44) — exactly the expected "no data yet" state, reported honestly
rather than faked.

**`evals/final_eval_report.json`** runs the existing `evals/ragas_eval.py`
harness against the full 50-entry golden set (`fixtures/golden/summaries.json`)
instead of the first 30. Result: still 20/50 summaries found in the dev DB,
identical metrics to the Day 18 baseline (faithfulness 0.783). The roadmap's
KM #258 calls for "100 golden examples" — the actual hand-labeled set has 50,
and only 20 of those have a corresponding summarised document. Both gaps
(50 vs. 100, 20 vs. 50) are recorded in the report's `notes` field and in SD1
§6 rather than silently re-scoped, consistent with Day 43's "honest results"
approach to the F2 faithfulness gap.

**`docs/SD1-System-Design-v1.md`** is the "all 5 features + data flow"
system design doc the roadmap calls for — distinct from
`docs/ARCHITECTURE.md` (a day-by-day build log) in that it's organized for an
external reader: one data-flow diagram covering F1→F5, a data-model summary
table, 7 numbered key design decisions with rationale, an eval/governance
table, and an explicit "Honest Gaps" section (faithfulness gap, golden-set
size, cost-dashboard coverage, notification dedup, no migration tool).

**`docs/Portfolio-Page-v1.md`** is page content (problem statement, pipeline
table, "what makes this different," headline metrics, links to the case
study and SD1) — explicitly framed as *content*, since no frontend/site
exists yet to host it.

---

## Result

```
$ python -m pytest tests/ -q
194 passed, 11 deselected, 84 warnings in 36.13s
```

(191 from Day 43 + 3 new cost-dashboard tests. No regressions.)

```
$ python -m scripts.cost_dashboard
Cost Dashboard ($/query)
========================================
SUMMARISE log entries:      95
  with token data:          0
...
  (none -- no SUMMARISE rows have token data yet)
```

---

## v1 Limitations

1. **Cost dashboard has no historical data** — token logging started today;
   `$/query` will only be meaningful once new documents are summarised.
   Verified the *mechanism* works via `tests/test_cost_dashboard.py`'s
   synthetic `AuditLog` rows, not against a live Anthropic call (no API cost
   incurred today).
2. **Final eval golden set is 50, not 100** — and only 20/50 have matching
   summaries in the dev DB. Closing this requires hand-labeling more
   documents (labeling_method is explicitly "not LLM-generated" per
   `fixtures/golden/summaries.json`), which is real labeling work, not a
   script.
3. **F2 faithfulness gap unchanged** — 0.783 vs. 0.85 target, still open
   (Day 45 target per roadmap).
4. **Cost dashboard covers F2 only** — F3 (reranker) and F4 (LangGraph
   agent) token usage isn't logged. Flagged in SD1 §6 as a v2 item, not
   built speculatively.
5. **No frontend exists** for the portfolio page — content only.

---

## PM Insight

Today's smallest production-code change (one function returning a 3-tuple
instead of a 2-tuple, ~15 lines) is what makes every other Day 44 deliverable
honest rather than aspirational. Without `_call_claude` logging
`response.usage`, "cost dashboard" would have had to either fake numbers or
ship as an empty stub; with it, `scripts/cost_dashboard.py` runs against the
real dev DB today and correctly reports "0 queries have token data yet" —
which is the *true* current state, and becomes a real $/query number the
moment F2 runs again. The SD1 and portfolio docs lean on this same pattern:
both report the F2 faithfulness gap and the 50-vs-100 golden set gap as
explicit open items rather than reframing scope to make Day 44 look more
"done" than it is. Across Days 43-44, "honest gaps section" has become a
recurring artifact shape — worth keeping as a standard section in future
system-design and case-study docs.

---

**Next: Day 45 (Week 7 — Integration + Portfolio, final day)** — do not start
without explicit "next".
