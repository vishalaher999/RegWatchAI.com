# HITL Approval Workflow v1 — F4 Task Approval

**Date:** 2026-06-13
**Feature:** F4 — Task Generation (Week 5, Day 4 of 7)
**Status:** Implemented in `src/f4_tasks/hitl_agent.py` + `scripts/review_pending_tasks.py`.
Extends `docs/Task-Board-UX-v1.md`'s "Approve" button (mockup-only) into a real
flow — verified end-to-end on real F3 HIGH findings (Day 32 notes).

---

## What changed since Task-Board-UX-v1

Day 31 generated tasks and wrote them straight to the DB as `status=open`.
The "Approve" button in `Task-Board-UX-v1.md` had nothing to approve — the
task already existed.

Day 32 inserts a real gate: drafting and persisting are now two separate
steps, with a human decision in between. **A `Task` row literally cannot be
created without `resolve_approval(..., approved=True)` being called** — this
is enforced by LangGraph's `interrupt()`, not by a UI convention.

---

## Flow

```
 F3 HIGH finding
       |
       v
  ┌─────────┐     run_with_approval()
  │  draft  │ --- (1 ReAct agent call per finding,
  └─────────┘      same as Day 31's agent.py)
       |
       v
  ┌─────────────────┐
  │ await_approval   │ <-- graph PAUSES here (interrupt)
  │ (pending state)  │     state persisted via InMemorySaver,
  └─────────────────┘     keyed by thread_id
       |
       |  resolve_approval(thread_id, approved, edits)
       v
  ┌──────────┐
  │ finalize │
  └──────────┘
   /            \
  approved=True   approved=False
   |                 |
   v                 v
 Task(status=open)   (no Task row)
 + AuditLog          + AuditLog
   TASK_CREATE          OVERRIDE
   (edits applied)      (rejected_task
                          in payload)
```

---

## CLI walkthrough (`scripts/review_pending_tasks.py`)

```
2 drafted task(s) awaiting review.

=================================================================
Title:       Fair-Lending-ECOA-Policy Section 1.1 - Equal Credit
             Opportunity Act (Regulation B) Update
Owner:       Sarah
Due date:    2026-07-21
Description: This policy section needs review due to significant
             changes in the legal landscape and credit markets
             since the 1976 Act. The regulation notes that "..."
=================================================================
Approve (y) / Edit due date (e) / Reject (n)? y
-> {'status': 'created', 'task_id': '8f57f4a0-...'}

=================================================================
Title:       Fair-Lending-ECOA-Policy Section 1.2 - Equal Credit
             Opportunity Act (Regulation B)
...
=================================================================
Approve (y) / Edit due date (e) / Reject (n)? n
-> {'status': 'rejected'}
```

Verified result: exactly 1 `Task` row (`status=open`), 1 `AuditLog
(TASK_CREATE)` row, and 1 `AuditLog(OVERRIDE)` row recording the rejected
draft (with the full rejected task in `payload_json` — nothing is silently
discarded).

---

## How this maps to the Task Board (future)

`Task-Board-UX-v1.md`'s "Open" column will show `Task` rows AFTER approval —
i.e. only tasks that already passed this gate. A future UI would replace the
CLI's y/e/n prompts with the "Approve / Edit / Dismiss" buttons on a new
**"Pending Review"** column, sourced from `run_with_approval()`'s pending
list rather than the `Task` table (pending items aren't `Task` rows yet).

---

## v1 Limitations (documented)

- **`InMemorySaver` checkpointer** — pending approvals are lost if the
  process restarts before `resolve_approval()` is called. A future day
  could swap to `SqliteSaver` (same `regwatch.db` file) for persistence
  across restarts.
- **CLI only** — `scripts/review_pending_tasks.py` is a terminal tool, not a
  web UI. The graph/state design (thread_id, drafted_task, decision) is
  UI-agnostic, so a future web endpoint can drive the same
  `run_with_approval()` / `resolve_approval()` functions.
- **Only `due_date` is editable** in v1. Editing `title`/`description`/`owner`
  is supported by `resolve_approval(edits=...)` (any drafted-task key can be
  overridden) but the CLI only prompts for `due_date`.
- **No batch approval** for high-precision classes yet — every task is
  reviewed individually, even though Day 30's precision table shows HIGH
  predictions are 90.9% correct. That's Stage 2->3 territory in
  `docs/Progressive-Autonomy-Roadmap-v1.md`, intentionally not built yet.
