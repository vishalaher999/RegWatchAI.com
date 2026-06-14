# Override Rate Dashboard v1 — F5 Wireframe + Live Numbers

**Date:** 2026-06-13
**Feature:** F5 — Audit Trail (Week 6, Day 2 of 7)
**KM concept:** #241 LangSmith ("Override rate dashboard")
**Status:** Wireframe + a real computation script
(`scripts/override_rate_report.py`) run against current data. No frontend
code.

---

## Why this metric

"% of AI output a human had to change" is the single number that tells
Sarah/Mike whether F4's drafts are trustworthy enough to act on directly, or
whether the human-in-the-loop step is doing real work. It's also the
natural complement to `docs/RAGAS-Baseline-Report-v1.md`'s "Automation Rate
vs Override Rate" table — this is where that number actually gets computed
from `AuditLog`, not estimated.

---

## What v1 measures

`AuditAction.OVERRIDE` rows are written in two places:

- `src/f4_tasks/tools.py` — `assign_owner` / `set_due_date` /
  `link_regulation`, each writing `{"task_id": ..., "field": ..., "before":
  ..., "after": ...}` after a `Task` row already exists.
- `src/f4_tasks/hitl_agent.py` — when a HITL reviewer **rejects** a drafted
  task, writing `{"rejected_task": {...}}` (no `task_id`/`field`, since no
  `Task` row was ever created).

`scripts/override_rate_report.py` queries both, plus `AuditAction.TASK_CREATE`
rows (`{"task_id": ...}`), and computes:

```
override_rate = (tasks with >=1 field-edit OVERRIDE) / (tasks created)
```

---

## Live run (2026-06-13)

```
python -m scripts.override_rate_report

Override Rate Report
========================================
Tasks created:          3
Tasks human-edited:     0
Override rate:          0.0%
Rejected drafts (HITL): 1

Edits by field:
  (none)
```

3 tasks created across Days 31-37, 0 edited after creation, 1 HITL
rejection during Day 32/33 testing. Not a meaningful sample yet — this is
the first day the number exists, not the first day it's trustworthy.

---

## Layout (wireframe)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Observability                                                          │
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │
│  │ Tasks created     │  │ Override rate    │  │ HITL rejection rate │   │
│  │       3           │  │     0.0%         │  │       33%           │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │
│                                                                          │
│  Edits by field                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ owner            ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0     │ │
│  │ due_date         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0     │ │
│  │ linked_regulations ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0     │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

Each TASK_CREATE row with a `langsmith_trace_id` (Day 37) links to a
"View full trace" button — opens the LangSmith run that produced the draft,
for the decision trace view described below.

---

## Decision trace view

Day 37 also wires `AuditLog.langsmith_trace_id` (an existing, previously
unused field — `src/models.py`) for `SUMMARISE` (F2) and `TASK_CREATE` (F4)
rows:

- **F2**: `_call_claude` (`src/f2_summarise/summariser.py`) is wrapped in
  `@traceable`; `get_current_run_tree().id` after the API call becomes the
  `AuditLog(SUMMARISE).langsmith_trace_id`.
- **F4**: `generate_task_for_finding` (`src/f4_tasks/agent.py`) wraps
  `agent.invoke(...)` in `collect_runs()`; the root LangGraph run's id
  becomes `AuditLog(TASK_CREATE).langsmith_trace_id`. Same wiring added to
  `src/f4_tasks/hitl_agent.py`'s `finalize()`.
- `get_task_audit_trail`'s summaries (`src/f4_tasks/audit.py`) now append
  `| trace=<id>` to `summarise`/`task_create` lines when a trace ID is
  present — see `scripts/show_task_audit_trail.py` output below.

```
2026-06-13T17:57:27  [task_create]  Task created by F4 (model=claude-sonnet-4-20250514,
                      prompt_version=v2, approved_by=system:f4, edits_applied={})
                      | trace=019ec221-7e22-7190-a95c-ef07b90306e0
```

**v1 limitation:** `LANGCHAIN_API_KEY` in `.env` is a placeholder, so the
trace ID above is generated locally (a real UUID7) but the run was rejected
by the LangSmith API (`403 Forbidden`) and won't appear in the LangSmith UI.
The ID is still useful for correlating local logs/DB rows. A real
`LANGCHAIN_API_KEY` is needed for the trace to actually open in LangSmith.

---

## v1 scope and gaps

- **No "% summaries human-edited" metric.** `AuditAction.OVERRIDE` is only
  ever written against `Task` rows (`src/f4_tasks/tools.py`). F2 summaries
  have no edit/correction mechanism in the schema — a human reviewing a
  summary in the review queue doesn't currently produce an audit row. v2
  would need an `AuditAction.OVERRIDE` (or new action) written when a
  reviewer edits `summary_json` directly.
- **Small sample size** (3 tasks). The dashboard is correct but not yet
  informative — same caveat Day 36 raised about MAP volume, in reverse.
- **No frontend** — `scripts/override_rate_report.py` is the only
  implementation; the boxes/bars above are a layout sketch for whoever
  builds the F5 frontend.
- **Trace IDs not yet clickable** — would need a real `LANGCHAIN_API_KEY`
  and a URL template (`https://smith.langchain.com/o/<org>/projects/p/<project>/r/<run_id>`)
  to become a link; org ID isn't known until a real LangSmith account is
  connected.

---

## How this connects to the rest of RegWatch

- Builds on Day 36's `get_task_audit_trail`/`_summarize_entry`
  (`src/f4_tasks/audit.py`) and the now-5-action `AuditLog` table.
- Reuses the existing `AuditAction.OVERRIDE` rows from Day 33
  (`src/f4_tasks/tools.py`) and Day 32 (`src/f4_tasks/hitl_agent.py`) —
  no new audit-writing code was needed for the override side of this metric,
  only the read/aggregation side (`scripts/override_rate_report.py`).
- Feeds `docs/RAGAS-Baseline-Report-v1.md`'s "Automation Rate vs Override
  Rate" table and `docs/Audit-Log-Viewer-UX-v1.md`'s planned "view full
  trace" link.
