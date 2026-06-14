# 5 Whys RCA — F2 Hallucinates a Compliance Deadline (Day 34)

**Status:** Hypothetical incident, written proactively (per roadmap v2.2's
Day 34 Product column) before it has happened — a pre-mortem, not a
postmortem. Used to drive today's deliverable (`get_task_audit_trail`) and
to scope future work.

---

## The Incident

A new CFPB final rule is ingested (F1) and summarised (F2). F2's NER step
extracts `compliance_deadline = "2026-01-01"` and writes it into
`RegulatoryDocument.summary_json`. The *actual* compliance deadline stated
in the rule's text is `2026-07-21` — F2's NER picked up an unrelated date
mentioned elsewhere in the document (e.g. a comment-period close date).

F3 maps this regulation to `Fair-Lending-ECOA-Policy` Section 1.1 as HIGH
impact. F4's agent calls `get_regulation_deadline`, gets back
`compliance_deadline = "2026-01-01"`, and drafts a Task with
`due_date = "2026-01-01"` — six months earlier than the real deadline.
Sarah approves it via the HITL flow (Day 32). The task now sits in her
queue with a due date that is simply wrong, and nothing in the system has
said otherwise.

---

## Five Whys

**1. Why did the Task have the wrong due_date (2026-01-01 instead of
2026-07-21)?**
Because F4's `create_task` tool call used the value returned by
`get_regulation_deadline`, which read `compliance_deadline` straight from
`RegulatoryDocument.summary_json` — and that value was wrong.

**2. Why was `compliance_deadline` wrong in `summary_json`?**
Because F2's NER step (`src/f2_summarise/ner.py`) extracted a date from the
document that *looks like* a compliance deadline (a date near regulatory
language) but is not the one the rule actually designates as the compliance
deadline. NER does pattern/context matching, not semantic verification
against the rule's actual effective-date clause.

**3. Why didn't F2's confidence scoring or review queue catch this?**
Because `confidence_score` and `review_flag` are computed from the
*summarisation* quality overall (faithfulness to chunks, RAGAS-style
checks) — they are not a per-field check on whether `compliance_deadline`
specifically is correct. A summary can be 87% confident and well-grounded
in its chunks while still containing one wrong extracted date, because the
overall confidence score isn't sensitive to a single field. (Looking at the
real trail pulled today for the one Task that exists in the DB: its
`review_flag` was `True` for three earlier summarisation runs and only
became `False` at confidence=87 on the *fourth* run — re-summarisation
already changes these fields over time, but nothing re-validates a
previously-approved Task against a newer summary.)

**4. Why didn't Day 33's `create_task` validation catch it?**
Because `CreateTaskArgs.due_date`'s `field_validator` only checks that the
string is a *valid ISO date* (`date.fromisoformat`) — it has no way to know
whether `2026-01-01` is the *correct* deadline for this regulation. Format
validation and correctness validation are different problems; Day 33 only
solved the first one.

**5. Why didn't Sarah's HITL review (Day 32) catch it?**
Because the drafted task Sarah sees is `{title, description, owner,
due_date}` — a due date and a description that quotes regulation text, but
not the specific sentence(s) F2's NER used to derive `compliance_deadline`.
Sarah has no quick way to cross-check "is this due date actually what the
regulation says" without opening the source document herself, which the
approval UI doesn't prompt her to do for a routine-looking date.

---

## Root Cause

**No step in the pipeline treats `compliance_deadline` as a high-stakes
field requiring its own evidence trail.** It's extracted once by F2,
trusted by F3/F4, format-validated by Day 33, and displayed to Sarah without
the *source sentence* that produced it — so a wrong-but-plausible date can
flow from ingestion to an approved task with every intermediate check
passing.

A secondary contributing factor, found while building today's audit trail:
**the audit log itself can't fully reconstruct this chain.** `AuditAction.MAP`
is never written by F3 (`src/f3_impact/`) — there's no audit record of which
F3 run produced the HIGH match that led to this task, only the regenerable
`data/f3_indexes/impact_results.json`. And F1's `AuditAction.INGEST` entries
are per-agency-run, not per-document, so they can't be tied to this specific
regulation either. `get_task_audit_trail()` (built today) can show every F2
SUMMARISE run and the F4 TASK_CREATE/OVERRIDE history for a task, but cannot
show *when or how* F3 decided this was a HIGH match.

---

## What Today's Deliverable Does and Doesn't Fix

`get_task_audit_trail()` / `scripts/show_task_audit_trail.py` give Sarah (or
an examiner) a single place to see: every F2 summarisation attempt for the
source regulation (with `confidence_score`, `review_flag`,
`ner_compliance_deadline` if added to the payload), and the full F4 history
for the task (who approved it, what model/prompt versions, every later
edit). That's a real improvement for "what happened and when" —
**investigation**, not **prevention**.

It does **not**:
- Verify `compliance_deadline` is correct.
- Surface the source sentence F2's NER used, alongside the task, for Sarah
  to cross-check.
- Write an `AuditAction.MAP` entry for F3, so the trail still has a gap
  between "regulation summarised" and "task created."

---

## Recommended Follow-Ups (not built today — future days)

1. **F3 should write `AuditAction.MAP` entries** (one per matching run, or
   per HIGH finding) so `get_task_audit_trail` can show the impact-mapping
   step, not just summarise -> task_create.
2. **`get_regulation_deadline` could return the source sentence/span** that
   F2's NER used for `compliance_deadline`/`effective_date` (if F2 starts
   storing it), and `create_task`'s description could be required to
   reference it — giving Sarah's review something concrete to check.
3. **A "deadline confidence" sub-score**, separate from overall summary
   confidence, that specifically reflects how directly the extracted date
   ties to compliance-deadline language vs. an incidentally-nearby date.
4. **Re-validation on re-summarisation**: if F2 re-summarises a document
   whose `compliance_deadline` changes, any open `Task` sourced from it
   should be flagged for re-review (currently nothing connects a later
   SUMMARISE run back to an already-created Task).

These are documented as gaps, consistent with the project's "honest caveat"
pattern (same as F3's golden-set limitations) — not silently left for
someone to discover later.
