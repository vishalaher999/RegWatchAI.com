# Notification UX v1 — Task Email Templates (Day 33)

**Status:** Draft templates only. RegWatch AI / Claude does not send emails on
the user's behalf — these are content for a future notification service
(e.g. triggered from `finalize` in `src/f4_tasks/hitl_agent.py`, or a
scheduled job checking `Task.due_date`) to use, reviewed and sent by a human
or an approved transactional-email integration.

---

## 1. New Task Assigned

**Trigger:** `resolve_approval(approved=True)` creates a `Task` row
(`src/f4_tasks/hitl_agent.py`'s `finalize` node, `AuditLog(TASK_CREATE)`
written).

**Recipient:** the `Task.owner` ("Sarah" or "Mike").

**Subject:**
```
[RegWatch AI] New compliance task: {title}
```

**Body:**
```
Hi {owner},

A new compliance task has been created from RegWatch AI's regulatory
monitoring.

Task: {title}
Due: {due_date}

{description}

Source: {source_policy_name} Section {source_section_id}
Regulation: {source_regulation_title}
Impact level: {source_impact_level}

View and manage this task in the Task Board.

— RegWatch AI
```

---

## 2. Task Overdue

**Trigger:** a scheduled check finds a `Task` where `due_date < today` and
`status != "completed"`.

**Recipient:** the `Task.owner`.

**Subject:**
```
[RegWatch AI] Overdue: {title}
```

**Body:**
```
Hi {owner},

The following compliance task is now overdue.

Task: {title}
Was due: {due_date}
Current status: {status}

{description}

Regulation: {source_regulation_title}
Linked regulations: {linked_regulations_json, if any}

Please update its status or due date in the Task Board, or use
set_due_date / assign_owner if it needs to be reassigned or rescheduled.

— RegWatch AI
```

---

## v1 Limitations

- No actual send path — templates only. Wiring these to a transactional
  email provider (and getting explicit sign-off that automated outbound
  email is in scope) is a separate, future decision.
- "Task overdue" assumes a scheduled job exists to scan `Task.due_date`;
  no such job is built yet.
- Both templates assume a single recipient (`Task.owner`); no CC/escalation
  path (e.g. notifying Mike if Sarah's task goes overdue) is defined.
