# Audit Log Viewer UX v1 — F5 Wireframe
# Filter by date, actor, action

**Date:** 2026-06-13
**Feature:** F5 — Audit Trail (Week 6, Day 1 of 7)
**Status:** Wireframe only. No frontend code yet — describes the UI that
the `AuditLog` table (`src/models.py`) now feeds, after Day 36 closed the
INGEST and MAP coverage gaps documented in `docs/F4-Audit-Report-v1.md`.

---

## Why now

Before Day 36, an `AuditLog` table query would mostly show `summarise`,
`task_create`, and `override` rows — `ingest` entries existed but weren't
tied to a document, and `map` entries didn't exist at all. A viewer built on
top of that data would have had two blank-looking filters. Day 36 makes all
five `AuditAction` values (`ingest`, `summarise`, `map`, `task_create`,
`override`) meaningful and `doc_id`/`task_id`-linked, so this is the first
day a "filter by action" viewer would show something in every column.

---

## Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Audit Log                                                                  │
│                                                                              │
│  Date range: [2026-06-01] to [2026-06-13]   Actor: [All v]  Action: [All v]│
│                                                                              │
├──────────────┬──────────┬─────────────┬──────────────────────────────────┤
│ Timestamp     │ Action    │ Actor       │ Summary                          │
├──────────────┼──────────┼─────────────┼──────────────────────────────────┤
│ 06-13 17:34   │ map       │ system      │ Fair-Lending-ECOA-Policy §1.1 vs │
│               │           │             │ Equal Credit Opportunity Act     │
│               │           │             │ (Reg B) -> HIGH (dense=0.68)     │
├──────────────┼──────────┼─────────────┼──────────────────────────────────┤
│ 06-13 17:20   │ task_create│ system:f4  │ Task created, prompt_version=v2, │
│               │           │             │ approved_by=human:sarah          │
├──────────────┼──────────┼─────────────┼──────────────────────────────────┤
│ 06-05 02:38   │ summarise │ system:f2  │ confidence=87, review_flag=False │
├──────────────┼──────────┼─────────────┼──────────────────────────────────┤
│ 06-04 13:58   │ ingest    │ system      │ fed: "Equal Credit Opportunity   │
│               │           │             │ Act (Regulation B)" (final_rule) │
└──────────────┴──────────┴─────────────┴──────────────────────────────────┘
```

Each row's **Summary** column is exactly the string `_summarize_entry()`
(`src/f4_tasks/audit.py`) produces for that `AuditLog` row — the viewer
doesn't need its own formatting logic, it reuses Day 34's function.

---

## Filters

| Filter | Source field | Notes |
|--------|-------------|-------|
| Date range | `AuditLog.timestamp` | Defaults to last 7 days |
| Actor | `AuditLog.actor` | `"system"`, `"system:f2"`, `"system:f4"`, `"human:sarah"`, etc. |
| Action | `AuditLog.action` | All 5 `AuditAction` values now populated (Day 36) |
| Document / Task | `AuditLog.doc_id` or `payload_json["task_id"]` | Optional — "show me everything about this regulation/task", i.e. `get_task_audit_trail` rendered as a table instead of CLI text |

---

## Row click -> drill-down

Clicking a `map` or `summarise` row (which has `doc_id`) jumps to that
`RegulatoryDocument`'s full trail. Clicking a `task_create`/`override` row
(which has `payload_json["task_id"]`) jumps to that `Task`'s full trail —
i.e. the same view `scripts/show_task_audit_trail.py` prints, rendered as a
table. This reuses `get_task_audit_trail()` unchanged.

---

## v1 scope and gaps

- **Read-only.** No editing or deleting rows — `AuditLog` is documented as
  immutable (`src/models.py` docstring); the viewer must not violate that.
- **`map` entries are per-(policy section, regulation) pair, not
  per-Task** — a regulation with 5 HIGH findings across different policy
  sections will show 5 `map` rows. The Action filter + drill-down (above) is
  how a user narrows from "everything" to "this one finding."
- **Duplicate entries on re-runs are expected**, not a bug — re-running F2's
  summariser or F3's classifier on the same document writes a NEW row each
  time (same pattern Day 34 observed with 5 `summarise` entries for one
  regulation). The viewer should show all of them, not deduplicate — that
  history is the point.
- **No pagination/perf design yet** — fine at current data volumes
  (hundreds of `map` rows from Day 36's first real run); will need it before
  a pilot client with a larger policy library.
- **No export** — `docs/Notification-UX-v1.md`'s weekly report and Day 38's
  "compliance report template" are the planned export paths, not this viewer.

---

## How this connects to the rest of RegWatch

- Built directly on Day 34's `get_task_audit_trail`/`_summarize_entry`
  (`src/f4_tasks/audit.py`) and Day 36's `log_document_ingest`
  (`src/f1_ingest/ingest.py`) / `log_map_decisions` (`src/f3_impact/classifier.py`).
- This is the "Audit log viewer UX" deliverable for Day 36 (KM #242); Day 37
  (LangSmith traces linked to audit records) extends each row with a "view
  full trace" link, same as `Task-Board-UX-v1.md`'s evidence trail already
  sketches for `task_create` rows.
