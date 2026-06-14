# Day 32 — F4 HITL Approval Gate (KM #190–191 LangGraph HITL)

**Date:** 2026-06-13
**Feature:** F4 — Task Generation (Week 5, Day 4 of 7)
**KM:** #190–191 LangGraph HITL
**Status:** HITL approval gate built and verified end-to-end. A `Task` row
can no longer be created without a human `resolve_approval(approved=True)`
call.

---

## What Was Built

| File | Change |
|------|--------|
| `src/f4_tasks/hitl_agent.py` | NEW — 3-node `StateGraph` (`draft` -> `await_approval` -> `finalize`), `InMemorySaver` checkpointer, `run_with_approval()` / `resolve_approval()`. |
| `scripts/review_pending_tasks.py` | NEW — CLI for Sarah: lists pending drafts, prompts approve/edit-due-date/reject. |
| `tests/test_f4_hitl.py` | NEW — 4 tests, in-memory SQLite, fake `draft_fn` (no LLM calls). |
| `docs/HITL-Approval-Workflow-v1.md` | NEW — flow diagram, real CLI walkthrough, maps onto Task-Board-UX-v1. |
| `docs/ARCHITECTURE.md` | New entries for all of the above. |

---

## Roadmap v2.2 — Day 32 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | #190–191 LangGraph HITL | `interrupt()` / `Command(resume=...)` in `hitl_agent.py` |
| Engineering | LangGraph: High impact -> human approval before task creation | `build_graph()`'s `await_approval` node pauses before `finalize` |
| Product | Approval workflow UX for high-impact tasks | `docs/HITL-Approval-Workflow-v1.md` |
| Deliverable | HITL task approval flow | `scripts/review_pending_tasks.py`, verified on 2 real findings |

---

## What Changed and Why

Day 31's `agent.run()` drafted a task and immediately called `session.add(Task(...))`
— the moment a finding was processed, it became a live task with
`status=open`. There was no point at which a human decision was *required*.
`docs/Task-Board-UX-v1.md`'s "Approve" button had nothing to approve against
— the task already existed.

KM #190–191 (LangGraph HITL) provides `interrupt()` and `Command(resume=...)`:
a graph node can call `interrupt(value)`, which raises a special exception
that LangGraph catches, persists the current state via a checkpointer, and
returns control to the caller with `value` exposed in `result["__interrupt__"]`.
The graph stays paused — literally cannot proceed to its next node — until
something calls `graph.invoke(Command(resume=...), config={"configurable":
{"thread_id": ...}})` with the same `thread_id`.

`hitl_agent.py` splits Day 31's single `run()` into three nodes:
- `draft` — same `generate_task_for_finding()` call as Day 31 (1 LLM call).
- `await_approval` — `interrupt(drafted_task)`. Nothing after this point
  has run yet.
- `finalize` — the ONLY place `Task`/`AuditLog` rows are written. Runs only
  on resume, with the human's `{"approved": bool, "edits": dict|None}`.

This means: **drafting and persisting are now separate operations**, and the
gap between them is exactly where Sarah's review happens.

---

## Result

```
2 drafted task(s) awaiting review.

[Task 1: Fair-Lending-ECOA-Policy Section 1.1 vs Equal Credit Opportunity
 Act (Regulation B)] -> approved (y)
  -> {'status': 'created', 'task_id': '8f57f4a0-87b8-4140-8ec1-1344049acdc7'}

[Task 2: Fair-Lending-ECOA-Policy Section 1.2 vs Equal Credit Opportunity
 Act (Regulation B)] -> rejected (n)
  -> {'status': 'rejected'}
```

Verified DB state after the run:
```
Tasks: 1
 - Fair-Lending-ECOA-Policy Section 1.1 - Equal Credit Opportunity Act
   (Regulation B) Update | TaskStatus.OPEN

AuditLogs (system:f4 / human:sarah): 2
 - AuditAction.TASK_CREATE  system:f4
 - AuditAction.OVERRIDE     human:sarah
```

The rejected draft is NOT lost — its full content (title, description,
owner, due_date) is preserved in the `AuditLog(OVERRIDE)` row's
`payload_json`, so there's a complete record of what was drafted and why it
didn't become a task, even though no `Task` row exists for it.

Tests: 4/4 new (`tests/test_f4_hitl.py`), 131/131 total suite passes.

---

## v1 Documented Limitations

- **`InMemorySaver`** — pending approvals are lost if the process restarts
  before review. `SqliteSaver` (same `regwatch.db`) would persist across
  restarts — not built today.
- **CLI only**, not a web UI — but `run_with_approval()` /
  `resolve_approval()` are UI-agnostic; a future web endpoint can drive the
  same functions.
- **Only `due_date` is editable** via the CLI (though `resolve_approval`'s
  `edits` dict accepts any drafted-task field).
- **No batch approval** for high-precision classes (HIGH = 90.9% precision
  per Day 30) — every task reviewed individually. That's Stage 2->3 on the
  Progressive Autonomy Roadmap, intentionally not built yet.

---

## PM Insight

Day 31 built the "brain" (drafting); Day 32 built the "gate" (control).
The interesting design choice was WHERE the gate lives: not as a status
field that a UI checks before showing an "Approve" button (which a future
bug or a different code path could bypass), but as a literal pause in the
agent's execution graph — `finalize` is unreachable without
`resolve_approval()`. That's a stronger SR 11-7 control: "no AI action
without human review" becomes a property of the SYSTEM'S CONTROL FLOW, not
a UI convention that depends on every future caller respecting it.

The rejected-task audit trail (full draft preserved in `AuditLog.payload_json`
even when no `Task` is created) is also worth flagging — it means a future
"why did the AI suggest X and what happened to it" question is answerable
even for the tasks Sarah said no to, which matters for both compliance
review and for eventually building Sarah's feedback into the system (a gap
`Trust-Strategy-v1.md` flagged on Day 29).

---

## Next: Day 33 (when user says "next")

Per roadmap v2.2 — confirm Day 33's columns before starting (build rule 3) —
do not start Day 33 without explicit "next".
