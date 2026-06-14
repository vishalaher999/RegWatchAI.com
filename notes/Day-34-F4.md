# Day 34 — F4 Audit Trail (KM #198)

**Date:** 2026-06-13
**Feature:** F4 — Task Generation (Week 5, Day 6 of 7)
**KM:** #198 Audit trail
**Status:** Task-level audit trail built and verified against real DB data.
A proactive 5 Whys RCA scoped the remaining audit gaps. 147/147 tests pass.

---

## What Was Built

| File | Change |
|------|--------|
| `src/f4_tasks/audit.py` | NEW — `get_task_audit_trail(task_id)` combines F2 `SUMMARISE` history (by `doc_id`) with F4 `TASK_CREATE`/`OVERRIDE` history (by `task_id` in `payload_json`) into one chronological trail. `format_trail()` renders plain text. |
| `scripts/show_task_audit_trail.py` | NEW — CLI: `python -m scripts.show_task_audit_trail <task_id>`. |
| `tests/test_f4_audit.py` | NEW — 6 tests, in-memory SQLite. |
| `docs/RCA-Hallucinated-Deadline-v1.md` | NEW — proactive 5 Whys RCA on a hypothetical F2-hallucinated-deadline incident. |
| `docs/ARCHITECTURE.md` | New entries for all of the above, plus a migration note. |
| `regwatch.db` | `ALTER TABLE task ADD COLUMN linked_regulations_json TEXT` (non-destructive — see "Unplanned Fix" below). |

---

## Roadmap v2.2 — Day 34 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | #198 Audit trail | `get_task_audit_trail()` in `src/f4_tasks/audit.py` |
| Engineering | Log every task creation: who approved, model version, sources | Already logged (Day 31/32 `AuditLog(TASK_CREATE)` payload has `model`, `prompt_version`, `approved_by`, source ids) — Day 34 ASSEMBLES these into one trail per task |
| Product | 5 Whys RCA — summary hallucinated a deadline | `docs/RCA-Hallucinated-Deadline-v1.md` |
| Deliverable | Task audit logging | `scripts/show_task_audit_trail.py`, verified on the real Task from Day 32 |

---

## What Changed and Why

The "Engineering" column for Day 34 reads like new logging work, but
checking what already exists (Day 31's `run()` and Day 32's `finalize` node)
showed `AuditLog(TASK_CREATE)` already records `model`, `prompt_version`,
`approved_by`, and the source finding's ids in `payload_json`. What was
missing wasn't *logging* — it was **assembly**: no function turned the
scattered `AuditLog` rows for a task (one `SUMMARISE` per F2 run on the
source regulation, one `TASK_CREATE`, any number of `OVERRIDE`s from Day 33's
management tools) into a single chronological story.

`get_task_audit_trail(task_id)`:
1. Loads the `Task`, reads `source_regulation_doc_id`.
2. Queries `AuditLog` where `doc_id == source_regulation_doc_id AND action ==
   SUMMARISE` — every F2 run on the regulation that produced this task.
3. Queries `AuditLog` where `action IN (TASK_CREATE, OVERRIDE)` and filters
   in Python for `payload_json["task_id"] == task_id` (these rows don't set
   `doc_id` to the task, only to the regulation for `TASK_CREATE` — the
   `task_id` link lives in the payload).
4. Sorts everything by `timestamp` and returns
   `{timestamp, action, actor, summary}` per row, with `_summarize_entry()`
   producing a human-readable line per action type.

---

## Result

Ran against the one real `Task` row in `regwatch.db` (from Day 32's verified
run):

```
Audit trail for task 8f57f4a0-87b8-4140-8ec1-1344049acdc7:

  2026-06-04T13:58:30  [summarise]    Regulation summarised by F2 (model=claude-sonnet-4-20250514, prompt_version=None, confidence=75, review_flag=True)
  2026-06-04T14:30:37  [summarise]    Regulation summarised by F2 (model=claude-sonnet-4-20250514, prompt_version=v2, confidence=77, review_flag=True)
  2026-06-04T16:18:52  [summarise]    Regulation summarised by F2 (model=claude-sonnet-4-20250514, prompt_version=v2, confidence=77, review_flag=True)
  2026-06-04T16:28:22  [summarise]    Regulation summarised by F2 (model=claude-sonnet-4-20250514, prompt_version=v2, confidence=77, review_flag=True)
  2026-06-05T02:38:16  [summarise]    Regulation summarised by F2 (model=claude-sonnet-4-20250514, prompt_version=v3, confidence=87, review_flag=False)
  2026-06-13T16:51:42  [task_create]  Task created by F4 (model=claude-sonnet-4-20250514, prompt_version=v1, approved_by=human:sarah, edits_applied={})
```

This trail is exactly what motivated the RCA: 4 of the 5 SUMMARISE runs had
`review_flag=True` (low confidence), and the `TASK_CREATE` happened nearly
9 days after the LAST summarisation — nothing connects "F2 re-summarised
this and confidence changed" to "should this already-created Task be
re-checked."

Tests: 6/6 new (`tests/test_f4_audit.py`), 147/147 total suite.

---

## Unplanned Fix: Task Table Migration

Verifying `audit.py` against the real DB failed with `no such column:
task.linked_regulations_json` — Day 33 added that field to the `Task`
SQLModel class, but `create_db_and_tables()` only runs
`SQLModel.metadata.create_all()`, which does not alter existing tables. The
column was missing from the live `regwatch.db`.

Fixed with a one-time, additive `ALTER TABLE task ADD COLUMN
linked_regulations_json TEXT` (nullable, no data loss). Documented in
`docs/ARCHITECTURE.md`'s `src/models.py` entry: there's no migration tool
(Alembic etc.) yet, so future field additions to existing tables need the
same manual step.

---

## v1 Documented Limitations

- `get_task_audit_trail` cannot show F1 ingest (per-agency-run, no `doc_id`)
  or F3 mapping (no `AuditAction.MAP` ever written) — see
  `docs/RCA-Hallucinated-Deadline-v1.md`'s "Root Cause" section.
- No deadline-specific evidence/confidence — `compliance_deadline` is
  trusted from `summary_json` with only format validation (Day 33).
- No re-validation trigger: if F2 re-summarises and `compliance_deadline`
  changes, no existing `Task` sourced from that document is flagged.
- No migration tooling — schema changes to existing tables are manual.

---

## PM Insight

This day's "Engineering" column looked like it needed new instrumentation,
but the instrumentation was already there from Day 31/32 — what was missing
was a *reader*. That's a useful pattern to recognize: a lot of "we need more
logging" requests are actually "we have the logs, nobody assembled them
into the view a person needs." Building the assembly function first (before
adding more raw logging) surfaced the actual gaps — F1's per-run INGEST and
F3's missing MAP entries — which are now documented, scoped follow-ups
instead of vague "audit trail isn't complete" worries.

The RCA being *proactive* (written before the incident, not after) is also
worth noting as a pattern: it forced a concrete walk-through of "what would
Sarah actually see" at each pipeline stage, which is how the F1/F3 audit
gaps were found — they weren't visible from reading the code in isolation,
only from tracing one task's full history end to end.

---

## Next: Day 35 (when user says "next")

Per roadmap v2.2 — Day 35 is Week 5's review/exit day: "End-to-end: new rule
-> summary -> impact -> approved task. Incident response plan for AI
failures. Follow up on partner outreach. F4 MVP: tasks from impact
findings." Confirm Day 35's columns before starting (build rule 3) — do not
start without explicit "next".
