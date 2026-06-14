# Incident Response Plan v1 — AI Failures (Day 35)

**Status:** v1 process document. No incidents have occurred yet — this is
written proactively, alongside `docs/RCA-Hallucinated-Deadline-v1.md`'s
pre-mortem, so the team knows what to do *before* something goes wrong.

**Scope:** "AI failure" here means RegWatch's AI output (a summary, an
impact classification, a drafted task) is wrong, misleading, or causes a
human to act on incorrect information — not infrastructure outages (API
down, DB unreachable), which are standard ops incidents.

---

## 1. Detection

How an AI failure becomes visible, roughly in order of how early it's
caught:

| Layer | Signal |
|-------|--------|
| F2 confidence/`review_flag` | Summary confidence below threshold -> review queue, before it reaches F3/F4 |
| F3/F4 eval CI gates | `evals/f3_eval.py` (>=80% impact accuracy), `evals/f4_eval.py` (100% structural validity) -- regressions block merges, not live data |
| Day 33 tool validation | `create_task`/`assign_owner`/`set_due_date` reject malformed `owner`/`due_date` at the tool-call boundary |
| Day 32 HITL review | Sarah rejects a drafted task (`AuditLog(OVERRIDE)` with `rejected_task` in payload) |
| **Post-approval** (the hard case) | A `Task` was approved and is now `open`, but its content is wrong -- e.g. Day 34's hallucinated-deadline scenario. Currently relies on a human noticing (no automated re-check). |

**Known gap:** everything above the line catches *malformed* or
*low-confidence* output. Nothing catches *plausible-but-wrong* output that
passed every check -- that's the Day 34 RCA's root cause, and the main
reason this plan exists.

---

## 2. Severity Triage

| Severity | Definition | Example |
|----------|-----------|---------|
| **SEV-1** | An approved `Task` (or summary Sarah relied on) contains materially wrong information that could affect a compliance decision (wrong deadline, wrong regulation cited, wrong policy section). | Day 34's hallucinated `compliance_deadline` scenario. |
| **SEV-2** | An AI output is wrong but caught before being acted on (HITL rejection, eval failure, review queue). | F3 misclassifies impact level; Sarah rejects in HITL. |
| **SEV-3** | Cosmetic/structural issue with no compliance impact (e.g. a title doesn't reference the regulation name, but the task content is otherwise correct). | `evals/f4_eval.py` structural check fails on title format. |

---

## 3. Response Steps (SEV-1)

1. **Contain** — do not let the bad `Task` continue to drive action.
   Use Day 33's `set_due_date`/`assign_owner` to correct it, or change
   `status` if the task should be paused. Every correction writes
   `AuditLog(OVERRIDE)` automatically -- no extra step needed to preserve
   the record of what was wrong and what it was corrected to.

2. **Investigate** — use Day 34's `scripts/show_task_audit_trail.py
   <task_id>` to see every F2 summarisation run for the source regulation
   (confidence scores, `review_flag` history, prompt versions) and every
   F4 decision (model, prompt version, who approved). This answers "what
   did the AI know, and when, and who signed off."

3. **Identify scope** — check whether the same root cause affects other
   `Task` rows. E.g. if F2's NER mis-extracted a deadline for one
   regulation, check `data/f3_indexes/impact_results.json` for other HIGH
   findings on the same `regulation_doc_id` and any `Task` rows with that
   `source_regulation_doc_id`.

4. **Notify** — Sarah (task owner) and Mike (compliance reporting) should
   be informed of the correction and its cause. (Per standing project
   constraint, RegWatch/Claude drafts notifications -- see
   `docs/Notification-UX-v1.md` -- but does not send them automatically.)

5. **Root-cause** — write a 5 Whys RCA (template below), modeled on
   `docs/RCA-Hallucinated-Deadline-v1.md`.

6. **Remediate** — turn the RCA's "Recommended Follow-Ups" into scoped
   future-day work (same pattern as Day 34's RCA listing F3 `AuditAction.MAP`
   logging, deadline source-sentence grounding, etc.).

---

## 4. 5 Whys RCA Template

```
## The Incident
[What happened, to which Task/RegulatoryDocument, when noticed and by whom]

## Five Whys
1. Why did [the visible symptom] happen?
2. Why did [answer to 1] happen?
3. Why did [answer to 2] happen?
4. Why didn't [the relevant automated check] catch it?
5. Why didn't [the relevant human review step] catch it?

## Root Cause
[One or two sentences -- the underlying gap, not the symptom]

## What Existing Tooling Does/Doesn't Cover
[e.g. get_task_audit_trail showed X but not Y]

## Recommended Follow-Ups
[Concrete, scoped -- not "be more careful"]
```

---

## 5. SR 11-7 Alignment

This plan operationalizes two SR 11-7 principles already built into RegWatch:

- **"Every AI decision logs model version + prompt version + inputs"**
  (CLAUDE.md) -- this is what makes step 2 (Investigate) possible at all.
- **Effective challenge / ongoing monitoring** -- the eval CI gates (F1
  ≥90%, F2 ≥0.85 faithfulness, F3 ≥80% impact accuracy) are the *ongoing
  monitoring* layer; this incident response plan is what happens when
  something gets through them anyway.

---

## v1 Limitations

- No automated SEV-1 detection -- relies on a human noticing a wrong
  approved `Task`. Day 34's RCA's "re-validation on re-summarisation"
  follow-up would help here.
- No paging/alerting integration -- "Notify" is manual.
- Not yet exercised on a real incident -- this is an untested process,
  same caveat as any pre-mortem.
