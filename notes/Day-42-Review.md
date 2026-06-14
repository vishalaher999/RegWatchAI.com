# Day 42 — Task Export (CSV) + Notification System (KM "Review")

**Date:** 2026-06-14
**Roadmap:** Week 6 ("Deploy & Demo"), Day 7 of 7 — last day of Week 6

---

## What Was Built

| Artifact | Type | Status |
|---|---|---|
| `src/f4_tasks/notifications.py` | NEW | Done — renders + queues both Day 33 templates |
| `src/f4_tasks/hitl_agent.py` | EDIT | `finalize()` queues "new task assigned" on approval |
| `scripts/check_overdue_tasks.py` | NEW | Done — queues "task overdue" notifications |
| `scripts/export_tasks.py` | NEW | Done — exports Tasks to CSV |
| `tests/test_f4_notifications.py` | NEW | 4 tests, passing |
| `tests/test_export_tasks.py` | NEW | 2 tests, passing |
| `tests/test_check_overdue_tasks.py` | NEW | 2 tests, passing |
| `.gitignore` | EDIT | Added `exports/` |
| `docs/ARCHITECTURE.md` | EDIT | Day 42 entries added |

---

## Roadmap v2.2 — Day 42 columns

| Column | Content |
|---|---|
| KM reference | "Review" (no specific KM #) |
| Engineering | "Management task export (CSV/PDF); email notification system live" |
| Product | "2 design partner discovery calls (scheduled Week 4, conducted now with live demo to show)" |
| Deliverable | "F5 MVP + GTM package + 2 partner calls" |

---

## What Changed and Why

**`src/f4_tasks/notifications.py`** turns Day 33's two draft email templates
into actual functions that take a `Task` row and produce `{to, subject,
body}`. `write_to_outbox()` appends each one as a JSON line to
`logs/notifications.jsonl` — a queue, not a send. This is deliberately the
stopping point: per the standing project constraint, RegWatch AI / Claude
doesn't send emails on the user's behalf, so "notification system live"
means the generation+queueing logic is live and tested, and the outbox is
the documented seam for a future transactional-email integration.

**`src/f4_tasks/hitl_agent.py`**'s `finalize()` now calls this right after
writing `Task(status=open)` on the approved path — so every task that
clears HITL approval automatically queues a "new task assigned" email for
its owner. Verified this doesn't touch the rejected/`OVERRIDE` path.

**`scripts/check_overdue_tasks.py`** is the other trigger from
`Notification-UX-v1.md` — a scheduled-job-shaped script (same `sys.path`
pattern as `run_daily.py`) that finds `Task` rows past their `due_date` and
not `completed`, and queues an overdue notification for each. v1 has no
dedup — re-running it re-queues for every still-overdue task. That's fine
while nothing is actually sent, but is called out explicitly as something
to fix before a real send path exists.

**`scripts/export_tasks.py`** exports all `Task` rows to `exports/tasks.csv`
(stdlib `csv`, no new dependency). PDF export was in the roadmap line but
needs `reportlab`, which isn't installed (still commented out in
`requirements.txt` from Day 36) — flagged rather than installed
speculatively, per build rule 6.

---

## Result

```
$ python -m pytest tests/ -q
190 passed, 11 deselected, 72 warnings in 17.32s
```

(182 from Day 40 + 8 new: 4 notification tests, 2 export tests, 2
overdue-check tests.)

Live-verified against the real dev DB:
- `python -m scripts.export_tasks` → exported 3 tasks to `exports/tasks.csv`,
  correct columns and content.
- `python -m scripts.check_overdue_tasks` → "Queued 0 overdue-task
  notification(s)" — correct, since the 3 existing tasks all have a 2026-07-21
  due date (in the future relative to today, 2026-06-14).
- Confirmed `finalize()`'s approved path writes a correctly-rendered
  "new task assigned" notification to `logs/notifications.jsonl` via the
  existing `tests/test_f4_hitl.py` approval test.

Both `exports/tasks.csv` and the test-run `logs/notifications.jsonl` were
deleted after verification (both gitignored — generated artifacts, not
checked in).

---

## On "2 design partner discovery calls" and the GTM package

These are calls you conduct — I can't run them. What's ready for them, all
built across Days 39-41:
- `docs/Enterprise-Pilot-Program-v1.md` — the 90-day pilot offer.
- `docs/Model-Card-v1.md` — SR 11-7 + EU AI Act self-assessment, for the
  bank's vendor-risk reviewer.
- `docs/Pricing-v1.md` — 3-tier pricing.
- `docs/Demo-Walkthrough-Script-v1.md` — the live-demo script (once
  `docs/Deployment-Guide-v1.md`'s Docker/Render steps give you a live URL,
  or run it locally against `uvicorn api.main:app --reload`).

---

## v1 Limitations

1. **No real email send path** — outbox only, by design (standing
   constraint). `logs/notifications.jsonl` is the integration point.
2. **No dedup on overdue notifications** — re-running `check_overdue_tasks`
   re-queues for every still-overdue task every time.
3. **CSV export only** — PDF needs `reportlab` (not installed).
4. **2 partner calls** — user-executed, not part of this session's output.

---

## PM Insight

Week 6 is now complete (Days 36-42): audit trail → observability →
guardrails+report → PII+pilot doc → API+Docker → model card+pricing →
export+notifications. Looking back, almost every "Product" deliverable this
week consumed an "Engineering" deliverable from the same or a prior day —
the compliance report reads the guardrail warnings, the pilot doc depends on
PII redaction, the model card cites the audit trail and override dashboard,
and today's notification system is just Day 33's templates finally wired to
a real trigger. Very little of this week was new capability; almost all of
it was making Days 1-35's capability legible and usable by someone other
than the system itself.

---

**Week 6 complete. Next: Day 43 (Week 7 — Integration + Portfolio)** — do not
start without explicit "next".
