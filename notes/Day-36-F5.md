# Day 36 — F5 Compliance Logging (Audit Log v1)

**Date:** 2026-06-13
**Feature:** F5 — Audit Trail (Week 6, Day 1 of 7)
**KM concept:** #242 Compliance logging
**Status:** Both gaps flagged in Day 34/35 closed. 151/151 tests passing.

---

## What Was Built

| File | Change |
|------|--------|
| `src/f1_ingest/ingest.py` | `log_document_ingest(session, doc, agency_slug)` (NEW) — writes one `AuditLog(INGEST, doc_id=doc.id)` per newly-saved document. |
| `src/f3_impact/classifier.py` | `log_map_decisions(results)` (NEW) — writes one `AuditLog(MAP, doc_id=regulation_doc_id)` per classified (policy section, regulation) match, with `dense_score`/`named_regulation_match`/`impact_level`/thresholds in the payload. Called from `main()`. |
| `src/f4_tasks/audit.py` | `get_task_audit_trail` extended to pull in the new `INGEST` entries (doc-scoped) and `MAP` entries (doc-scoped + filtered to this task's `source_policy_name`/`source_section_id`). |
| `scripts/show_task_audit_trail.py` | Added `sys.stdout.reconfigure(encoding="utf-8")` — without it the `§` character in F3 MAP summaries broke on Windows' console codepage. |
| `tests/test_f1_audit.py` (NEW) | 1 test — `log_document_ingest` writes a doc-scoped `AuditLog(INGEST)` with correct payload. |
| `tests/test_f3_audit.py` (NEW) | 2 tests — one MAP entry per match with correct payload/thresholds; zero entries for a section with no matches. |
| `tests/test_f4_audit.py` | +1 test — trail includes INGEST + MAP entries, and a MAP entry for a *different* policy section is correctly excluded. |
| `docs/Audit-Log-Viewer-UX-v1.md` (NEW) | Product deliverable — wireframe for a filterable audit log viewer (date/actor/action), drill-down via `get_task_audit_trail`. |
| `docs/ARCHITECTURE.md` | Updated entries for `ingest.py`, `classifier.py`, `audit.py`, `show_task_audit_trail.py`, `F4-Audit-Report-v1.md`; new entry for `Audit-Log-Viewer-UX-v1.md`. |

---

## Roadmap v2.2 — Day 36 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | #242 Compliance logging | -- |
| Engineering | Immutable audit log: ingest, summarise, map, task, override | All 5 `AuditAction` values now written and doc/task-scoped |
| Product | Audit log viewer UX (filter by date, user, action) | `docs/Audit-Log-Viewer-UX-v1.md` |
| Deliverable | Audit log v1 | `log_document_ingest` + `log_map_decisions` + extended `get_task_audit_trail` |

---

## What Changed and Why

Days 34-35 documented two specific gaps in `docs/F4-Audit-Report-v1.md`
Section 7:

1. F1's `INGEST` entries were per-agency-run, with no `doc_id` — couldn't
   trace an ingest event to a specific `RegulatoryDocument`.
2. F3 never wrote `AuditAction.MAP` at all — no record of *why* a policy
   section was matched to a regulation at a given impact level.

Both were called out as "known gaps, not fixed" — Day 36's roadmap item
(KM #242, "Immutable audit log: ingest, summarise, map, task, override")
is the natural place to fix them, since it's literally asking for all 5
actions to be covered.

**Design choices:**
- F1: kept the existing per-agency-run summary log AND added a per-document
  log, rather than replacing one with the other — the run-level summary
  (fetched/new/duplicates/anomalies counts) is still useful as a quick
  health check, while the per-document log is what makes a `Task`'s trail
  traceable to ingestion.
- F3: `log_map_decisions` is a separate function from `classify_matches`,
  not folded into it — `classify_matches` stays pure/file-based (matches
  the existing test pattern in `test_f3_classifier.py`), while the new
  function is DB-writing and separately tested with an in-memory engine
  (matches the `test_f4_audit.py` pattern).
- F4 audit.py: MAP entries are doc_id-scoped like SUMMARISE, but ALSO
  filtered by `policy_name`/`section_id` — a single regulation can be MAP'd
  against many policy sections (Day 36's real run produced 247 MAP entries
  across the whole policy library), and a Task's trail should only show the
  MAP decision for *its* finding, not all 247.

---

## Result

Re-ran `python -m src.f3_impact.classifier` against the real F3 indexes:

```
Logged 247 AuditLog(MAP) entries
```

Then re-ran Day 35's real task's trail:

```
python -m scripts.show_task_audit_trail 67fc89e1-792d-4d1a-8e08-ee67d43375f9

Audit trail for task 67fc89e1-792d-4d1a-8e08-ee67d43375f9:

  2026-06-04T13:58:30  [summarise]    confidence=75, review_flag=True
  2026-06-04T14:30:37  [summarise]    confidence=77, review_flag=True
  2026-06-04T16:18:52  [summarise]    confidence=77, review_flag=True
  2026-06-04T16:28:22  [summarise]    confidence=77, review_flag=True
  2026-06-05T02:38:16  [summarise]    confidence=87, review_flag=False
  2026-06-13T17:20:11  [task_create]  prompt_version=v2, approved_by=human:sarah
  2026-06-13T17:34:50  [map]  Fair-Lending-ECOA-Policy §1.1 vs Equal Credit
                        Opportunity Act (Regulation B), dense_score=0.68,
                        named_regulation_match=True, impact_level=high
  2026-06-13T17:34:59  [map]  (same finding — second classifier run)
```

Trail grew from 6 entries (Day 35) to 8. No `[ingest]` entry — this
regulation was ingested before Day 36's per-document logging existed (see
"v1 Limitations" below). The two `[map]` entries are from running the
classifier twice during verification — same "each run is its own audit
event" pattern Day 34 documented for repeated `summarise` runs.

Full suite (147 from Day 35 + 4 new this session): **151 passed, 11
deselected**.

---

## v1 Limitations

- **No retroactive INGEST entries.** Documents ingested before Day 36 have
  no per-document `INGEST` row — their trails will start at `summarise` or
  `map`, not `ingest`, until/unless a backfill script is written. Not
  planned — same "no migration tooling" caveat as Day 34's column-migration
  note.
- **MAP entries accumulate per run.** 247 entries from one classifier run
  across the whole policy library — re-running daily (once F3 is on a
  schedule) will grow this table steadily. No retention/archival policy
  defined yet.
- **No automated alert if a HIGH finding has zero MAP/TASK_CREATE follow-through** —
  still the FN-detection gap from `docs/F4-Audit-Report-v1.md` Section 5/7.
- Audit Log Viewer (`docs/Audit-Log-Viewer-UX-v1.md`) is a wireframe only —
  no frontend code.

---

## PM Insight

This is the cleanest example yet of the "review day finds real work" loop:
Day 35 was explicitly a review/exit day, its only output was a report
(`F4-Audit-Report-v1.md`) with a numbered gap list, and Day 36's roadmap
item happened to map almost exactly onto that list. The gap list did the
planning for today — "Engineering: immutable audit log: ingest, summarise,
map, task, override" decomposed directly into "which 2 of these 5 are we
missing, and what's the smallest change to add them."

The `247 MAP entries from one run` number is also a useful early signal:
it's the first time a single F5 logging change has produced a large volume
of rows from a single command. Worth keeping an eye on as F3 starts running
on a schedule rather than ad hoc — the "no retention policy" limitation
above will become real before long.

---

## Next: Day 37 (when user says "next")

Per roadmap v2.2 — Day 37: KM #241 LangSmith. "LangSmith traces linked to
audit records; decision trace view" (Engineering) / "Override rate
dashboard (% summaries/tasks human-edited)" (Product) / "Observability +
override dashboard" (Deliverable). Confirm Day 37's columns before
starting (build rule 3) — do not start without explicit "next".
