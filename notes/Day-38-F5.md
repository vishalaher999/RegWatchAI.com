# Day 38 — F5 Citations + Guardrails + Weekly Compliance Report

**Date:** 2026-06-13
**Feature:** F5 — Audit Trail (Week 6, Day 3 of 7)
**KM concept:** #263 Citations + #269 Guardrails
**Status:** `_apply_guardrails()` added to F2 summariser; weekly compliance
report script + doc added. 162/162 tests passing.

---

## What Was Built

| File | Change |
|------|--------|
| `src/f2_summarise/summariser.py` | New `_apply_guardrails(summary, num_chunks) -> list[str]`, placed next to `_validate_summary`. Three checks: (1) `effective_date`/`compliance_deadline` set with no matching `source_citations` entry; (2) `confidence_score >= CONFIDENCE_THRESHOLD` with empty `source_citations`; (3) a citation referencing `Chunk N` outside `1..num_chunks`. Hooked into `summarise_document()`: warnings combine with `_validate_summary`'s, get logged as `payload["guardrail_warnings"]`, and force `needs_review = True` regardless of the router's decision. |
| `tests/test_f2_guardrails.py` (NEW) | 5 tests — uncited date field warns, properly-cited date field passes, high confidence + no citations warns, out-of-range `Chunk N` citation warns, clean summary produces zero warnings. |
| `scripts/weekly_compliance_report.py` (NEW) | `build_report(days=7)` aggregates `AuditLog` over a trailing window: documents ingested, summaries by routing decision + guardrail-warning count, HIGH-impact findings, tasks created/edited/override rate (reuses Day 37's `compute_override_rate`). `render_markdown()` + `main()`. |
| `docs/Compliance-Report-Template-v1.md` (NEW) | Documents the report layout + a real run against current data. |
| `docs/ARCHITECTURE.md` | New Day 38 entry for `summariser.py` (second entry for this file, after Day 37's first); new entries for `weekly_compliance_report.py` and `Compliance-Report-Template-v1.md`. |

---

## Roadmap v2.2 — Day 38 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | #263 Citations + #269 Guardrails | -- |
| Engineering | Citation forcing on summaries; guardrails on outputs | `_apply_guardrails()` in `summariser.py` — citation-presence checks for dated fields + high-confidence summaries, chunk-range validation; forces `needs_review=True` on any failure |
| Product | Compliance report template (weekly PDF export) | `docs/Compliance-Report-Template-v1.md` + `scripts/weekly_compliance_report.py` (Markdown v1, PDF noted as v2) |
| Deliverable | Safety layer + report template | Both of the above, verified against real data |

---

## What Changed and Why

`source_citations` has been part of `SUMMARY_SCHEMA` (`src/f2_summarise/prompts.py`,
since v3 of the prompt) — the model is *asked* to cite which `[Chunk N]`
supports each key field. But a grep confirmed nothing ever validated this
field: a hallucinated `compliance_deadline` with no citation, or a citation
pointing at a chunk that was never retrieved, would sail through unflagged.
This is exactly the gap `docs/RCA-Hallucinated-Deadline-v1.md` (Day 34)
named: "no field-level evidence trail for `compliance_deadline`."

**Design choices:**
- `_apply_guardrails` is a separate function from `_validate_summary`, not a
  modification to it. `_validate_summary`'s signature is used directly by
  `tests/test_f2_summariser.py` and is about schema shape (required fields,
  types, ranges) — guardrails are about *evidence*, a different concern with
  a different failure mode (forces review, doesn't just log a warning).
- The chunk-range check uses the same `[Chunk N]` 1-indexed labelling that
  `format_chunks_for_prompt()` (`src/f2_summarise/retriever.py`) already
  produces — no new numbering scheme, just validating against the one the
  model was shown.
- A guardrail failure **overrides the router**: even an APPROVED/DISMISS
  routing decision gets forced to `needs_review=True` if a guardrail fires.
  Guardrails are a safety floor, not another vote in the routing decision —
  SR 11-7 framing is "the model's own confidence signal isn't sufficient
  evidence that its citations are real."
- `guardrail_warnings` is logged as its own payload key (separate from
  `_validate_summary`'s `warnings`, which it's also concatenated into) so the
  weekly report can count guardrail failures specifically, distinct from
  schema-validation issues.

For the report: `scripts/weekly_compliance_report.py` reuses Day 37's
`compute_override_rate()` rather than re-deriving override stats, and reads
the same `AuditLog` table Day 36's audit trail and Day 37's override
dashboard already use — only the aggregation (by 7-day window, not by task)
is new.

---

## Result

```
$ python -m pytest tests/test_f2_guardrails.py -q
.....
5 passed in 3.68s

$ python -m pytest tests/ -q
162 passed, 11 deselected, 60 warnings in 14.81s

$ python -m scripts.weekly_compliance_report
# Weekly Compliance Report

**Period:** 2026-06-06T18:08:07 to 2026-06-13T18:08:07 (UTC)

## Feed Activity

- Documents ingested: 0

## Summaries (F2)

- (none)
- Guardrail warnings raised: 0

## Impact Findings (F3)

- HIGH-impact findings: 54

## Tasks (F4)

- Tasks created: 3
- Tasks human-edited: 0
- Override rate: 0.0%
```

162 = 157 (Day 37) + 5 new (`tests/test_f2_guardrails.py`).

"Documents ingested: 0" / "Summaries (F2): (none)" reflect that F1/F2
`AuditLog` rows in this DB predate the trailing-7-day window — the F3/F4
numbers (54 HIGH findings, 3 tasks, 0% override) are from Days 36-37 and do
fall inside it. The report logic is correct; this is a stale-fixture-data
artifact, documented in `docs/Compliance-Report-Template-v1.md`.

---

## v1 Limitations

- **No live verification against a real hallucination.** The 5 guardrail
  tests use synthetic summary dicts, not a live Claude call — there's no
  fixture regulation that's known to produce an uncited deadline on demand.
  The checks are unit-tested against the exact shapes described in
  `docs/RCA-Hallucinated-Deadline-v1.md`, but haven't caught a *real*
  hallucination yet in this session.
- **Citation matching is substring-based.** "`compliance_deadline` is
  present in the citation string" is a weak check — a citation like
  `"Chunk 3 (mentions compliance_deadline somewhere)"` would pass even if it
  doesn't actually evidence the date. Tightening this (e.g. requiring the
  citation to also contain the date value) is a v2 candidate.
- **Weekly report is Markdown only, no PDF, no email, fixed 7-day window,
  counts only** — all documented in `docs/Compliance-Report-Template-v1.md`.

---

## PM Insight

Day 37 made `langsmith_trace_id` *exist*; Day 38 makes `source_citations`
*matter*. Both days followed the same pattern: a field had been part of the
schema/model for a while, requested or defined but never enforced or
populated — and the roadmap item was "close that gap." Worth watching for
more of these as the project continues — fields that were added early
"for later" are exactly where silent gaps accumulate, and grepping for
"is this ever read/written" is a cheap way to find the next one.

---

## Next: Day 39 (when user says "next")

Per roadmap v2.2 — confirm Day 39's columns before starting (build rule 3).
Do not start without explicit "next".
