# Day 37 — F5 Observability (LangSmith Traces + Override Dashboard)

**Date:** 2026-06-13
**Feature:** F5 — Audit Trail (Week 6, Day 2 of 7)
**KM concept:** #241 LangSmith
**Status:** `langsmith_trace_id` (existed but unused since early in the project) now populated for F2 SUMMARISE and F4 TASK_CREATE. Override rate report built and run. 157/157 tests passing.

---

## What Was Built

| File | Change |
|------|--------|
| `src/f2_summarise/summariser.py` | `_call_claude` wrapped in `@traceable`; now returns `(text, trace_id)`. `trace_id` from `get_current_run_tree().id`, gracefully `None` if tracing unavailable. Passed into `AuditLog(SUMMARISE).langsmith_trace_id`. |
| `src/f4_tasks/agent.py` | `generate_task_for_finding` wraps `agent.invoke(...)` in `collect_runs()`, returns the root LangGraph run's id as `_langsmith_trace_id`. `run()` pops it and stores on `AuditLog(TASK_CREATE).langsmith_trace_id`. **Also fixed:** `run()` was missing `session.commit()` — Task/AuditLog rows were never persisted, only `tasks.json`. |
| `src/f4_tasks/hitl_agent.py` | `finalize()` does the same trace_id pop/store for the HITL approval path. |
| `src/f4_tasks/audit.py` (NEW) | `_trace_suffix(log)` appends `" | trace=<id>"` to SUMMARISE/TASK_CREATE trail summaries when present. |
| `scripts/override_rate_report.py` (NEW) | `compute_override_rate()` — queries TASK_CREATE/OVERRIDE rows, returns total tasks, tasks edited, override rate %, edits-by-field, rejected HITL drafts. |
| `docs/Override-Rate-Dashboard-v1.md` (NEW) | Wireframe + real numbers from the report + decision-trace-view docs. |
| `tests/test_f2_tracing.py` (NEW) | 3 tests — trace_id captured / None / None-on-exception. |
| `tests/test_f4_audit.py` | +1 test — trace suffix shown/hidden in trail. |
| `tests/test_override_rate.py` (NEW) | 2 tests — zero case, rate + field breakdown + rejected drafts. |
| `docs/ARCHITECTURE.md` | New entries for `summariser.py` (first-ever entry for this file), `override_rate_report.py`, `Override-Rate-Dashboard-v1.md`; updated entries for `agent.py`, `hitl_agent.py`, `audit.py`. |

---

## Roadmap v2.2 — Day 37 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | #241 LangSmith | -- |
| Engineering | LangSmith traces linked to audit records; decision trace view | `langsmith_trace_id` populated for SUMMARISE/TASK_CREATE; `| trace=<id>` in `get_task_audit_trail` |
| Product | Override rate dashboard (% summaries/tasks human-edited) | `docs/Override-Rate-Dashboard-v1.md` + `scripts/override_rate_report.py` |
| Deliverable | Observability + override dashboard | Both of the above, verified against real data |

---

## What Changed and Why

`AuditLog.langsmith_trace_id` (`src/models.py`) existed since early in the
project — its docstring says it "links to the full LLM trace for AI
actions" — but a grep confirmed nothing ever wrote it. Day 37's roadmap item
is literally "make that true."

**Design choices:**
- F2 uses the raw `anthropic.Anthropic` SDK, not auto-traced — `@traceable`
  on `_call_claude` is the minimal wrap. Reading `get_current_run_tree()`
  *after* the API call (not via a decorator-injected argument) keeps the
  function's call sites unchanged except for the new `trace_id` return value.
- F4 uses LangGraph (`create_react_agent` + `.invoke()`), which auto-traces
  when `LANGCHAIN_TRACING_V2=true`. `collect_runs()` captures *every* run in
  the graph (one per tool call/step) plus a root `"LangGraph"` run
  (`parent_run_id is None`) — that root run is the one meaningful as "the
  trace for this task". Picking the wrong run (e.g. `traced_runs[0]`, which
  is the first-*completed* run, not the root) was caught during live
  verification.
- Both `agent.py` and `hitl_agent.py` needed the same trace_id plumbing
  (one for the unattended `run()` path, one for the HITL approval path) —
  `_langsmith_trace_id` is passed as a private key on the drafted-task dict
  and popped before `Task(**task_dict)` so it never leaks into the `Task`
  row or `tasks.json`.
- `_trace_suffix()` is additive — `AuditLog` rows without a trace_id (every
  row before today, and any future row if `LANGCHAIN_API_KEY` is unset)
  render exactly as before.

---

## Bug Found and Fixed (incidental to Day 37)

While verifying trace_id end-to-end, re-running `python -m src.f4_tasks.agent`
didn't add a new `Task`/`AuditLog` row to the DB even though it printed
"Generated 1 task(s)" and rewrote `tasks.json`. Root cause: `run()`'s
`with get_session() as session:` block never called `session.commit()` —
unlike `log_map_decisions` (Day 36) and `hitl_agent.finalize()`, which do.
Every `python -m src.f4_tasks.agent` run since Day 31 silently only wrote
`tasks.json`, never the DB. Fixed with one `session.commit()` at the end of
the loop. This is why the DB had only 2 Tasks (both from `hitl_agent`/HITL
flows) before today.

---

## Result

```
$ python -c "from src.f4_tasks.agent import run; run(limit=1)"
Generated 1 task(s)

$ python -m scripts.override_rate_report
Override Rate Report
========================================
Tasks created:          3
Tasks human-edited:     0
Override rate:          0.0%
Rejected drafts (HITL): 1

Edits by field:
  (none)

$ python -m scripts.show_task_audit_trail b7190a3e-5831-46d1-b7ce-9148c14000e3
...
  2026-06-13T17:57:27  [task_create]  Task created by F4 (model=claude-sonnet-4-20250514,
                       prompt_version=v2, approved_by=system:f4, edits_applied={})
                       | trace=019ec221-7e22-7190-a95c-ef07b90306e0
```

Full suite (151 from Day 36 + 6 new this session): **157 passed, 11
deselected**.

---

## v1 Limitations

- **Trace IDs aren't clickable in LangSmith.** `.env`'s `LANGCHAIN_API_KEY`
  is a placeholder (`your_langsmith_api_key_here`) — the LangSmith client
  generates real UUID7 run IDs locally (useful for DB correlation/debugging)
  but the API rejects ingestion with `403 Forbidden`. A real key is needed
  for the "decision trace view" to actually open a trace.
- **"% summaries human-edited" is not computed.** `AuditAction.OVERRIDE` is
  only ever written for `Task` edits — F2 summaries have no
  edit/correction mechanism in the schema. Documented as a v2 gap.
- **Small sample size** (3 tasks total) — the override rate (0.0%) is
  correct but not statistically meaningful yet.
- Override dashboard is a wireframe + CLI report only — no frontend.

---

## PM Insight

Today's most valuable output wasn't the LangSmith wiring itself — it was
the side effect of *verifying* it: discovering that `agent.run()` had been
silently not persisting to the DB since Day 31 (only `tasks.json` was ever
written). That's a "the eval/verification step found a real bug" example —
the same loop CLAUDE.md's eval-first rule is meant to produce, just one day
later than the wiring it was attached to. Worth remembering: any "Run:"
verification step that only checks a JSON file output, not the DB, can hide
this class of bug.

---

## Next: Day 38 (when user says "next")

Per roadmap v2.2 — Day 38: KM #263 Citations + #269 Guardrails. "Citation
forcing on summaries; guardrails on outputs" (Engineering) / "Compliance
report template (weekly PDF export)" (Product) / "Safety layer + report
template" (Deliverable). Confirm Day 38's columns before starting (build
rule 3) — do not start without explicit "next".
