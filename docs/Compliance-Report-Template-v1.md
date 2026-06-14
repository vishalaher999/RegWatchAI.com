# Compliance Report Template v1 — F5 Weekly Export

**Date:** 2026-06-13
**Feature:** F5 — Audit Trail (Week 6, Day 3 of 7)
**KM concept:** #263 Citations + #269 Guardrails ("Compliance report template (weekly PDF export)")
**Status:** `scripts/weekly_compliance_report.py` — real script, run against current
data. Outputs Markdown. PDF export is a v2 follow-up.

---

## Who this is for

Mike (risk manager) wants a single document he can forward weekly that
answers: "what did RegWatch see and do this week, and how much of it needed
a human?" Sarah (compliance officer) uses the same document as a starting
point for board/examiner reporting — every number on it traces back to an
`AuditLog` row, per CLAUDE.md's "every AI decision logs model version +
prompt version + inputs."

---

## Report sections

1. **Feed Activity** — documents ingested (`AuditAction.INGEST` rows in the
   period).
2. **Summaries (F2)** — count of summaries by routing decision
   (`AuditAction.SUMMARISE`, `payload["routing_decision"]` from
   `src/f2_summarise/router.py`: APPROVED / REVIEW / ESCALATE / DISMISS),
   plus the count of summaries that raised a Day 38 guardrail warning
   (`payload["guardrail_warnings"]`).
3. **Impact Findings (F3)** — count of HIGH-impact findings
   (`AuditAction.MAP`, `payload["impact_level"] == "high"`).
4. **Tasks (F4)** — tasks created, tasks human-edited, and the override rate
   (reuses Day 37's `compute_override_rate` from
   `scripts/override_rate_report.py`).

All counts are scoped to `AuditLog.timestamp >= now - 7 days`.

---

## Live run (2026-06-13)

```
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

"Documents ingested: 0" and "Summaries (F2): (none)" reflect that this
project's F1/F2 `AuditLog` rows were written on earlier build days, outside
the trailing-7-day window used by this report — the query and report
structure are correct; the data simply predates the window. The F3 (54 HIGH
findings) and F4 (3 tasks, 0% override) numbers are from Days 36-37 and fall
inside the window.

---

## Why guardrail warnings get their own line

Day 38 added `_apply_guardrails()` to `src/f2_summarise/summariser.py`,
closing the gap `docs/RCA-Hallucinated-Deadline-v1.md` identified: a date
field (`effective_date`/`compliance_deadline`) with no matching
`source_citations` entry, a high-confidence summary with no citations at
all, or a citation pointing at a chunk outside the retrieved range, are now
all logged as `payload["guardrail_warnings"]` on the `SUMMARISE` AuditLog
row and force `needs_review = True`. Surfacing the *count* of these on the
weekly report gives Sarah/Mike a leading indicator of citation quality
separate from the routing decision — a summary can be APPROVED by the
router and still have raised a guardrail warning forcing review.

---

## v1 limitations

- **Markdown only, not PDF.** "Weekly PDF export" in the roadmap is the
  target; v1 produces the Markdown body that a v2 step would feed to
  `pandoc report.md -o report.pdf` (or a headless-Chrome/wkhtmltopdf render).
  No PDF tooling was added this session.
- **No email delivery.** The report is printed to stdout; a v2 scheduled job
  (e.g. `scripts/override_rate_report.py`'s cron-style invocation pattern)
  would write it to a file and/or attach it to an email — note the standing
  project constraint that Claude does not send outreach emails on the
  user's behalf, so any email step would need to be a script the user runs.
- **Fixed 7-day window.** `build_report(days=7)` is the only period
  supported; a monthly or custom-range report would need a `--days` CLI flag.
- **No per-document detail.** The report is counts only — it doesn't list
  *which* documents/findings/tasks, unlike `scripts/show_task_audit_trail.py`
  (Day 36) which gives per-task detail. A v2 report could link the two.

---

## How this connects to the rest of RegWatch

- Reuses Day 37's `scripts/override_rate_report.compute_override_rate()`
  directly — no duplicated override-rate logic.
- Reads the same `AuditLog` table as `scripts/show_task_audit_trail.py`
  (Day 36) and `docs/Override-Rate-Dashboard-v1.md` (Day 37), just aggregated
  by time window instead of by task.
- The guardrail-warning count is the first report-level surface of Day 38's
  `_apply_guardrails()` — see `src/f2_summarise/summariser.py` and
  `tests/test_f2_guardrails.py`.
