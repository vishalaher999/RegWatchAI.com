# F4 Audit Report — Task Generation
# Week 5 Exit | SR 11-7 Model Risk Summary

**Date:** 2026-06-13
**Feature:** F4 — Task Generation (ReAct draft -> HITL approval -> create_task -> audit log)
**Companion docs:** [FP-FN-Risk-Matrix.md](FP-FN-Risk-Matrix.md) (F1/F2 equivalent),
[RAGAS-Baseline-Report-v1.md](RAGAS-Baseline-Report-v1.md) (F2 eval equivalent),
[RCA-Hallucinated-Deadline-v1.md](RCA-Hallucinated-Deadline-v1.md),
[Incident-Response-Plan-v1.md](Incident-Response-Plan-v1.md)

---

## 1. Overview

F4 turns an F3 HIGH-impact finding (policy section <-> regulation pair) into
a draft compliance `Task`, which a human (Sarah) must approve before it's
created. Pipeline:

```
F3 HIGH finding
  -> ReAct agent (lookup tools: get_policy_section_text, get_regulation_deadline)
  -> create_task tool call (Pydantic-validated owner/due_date)
  -> LangGraph HITL interrupt (Day 32)
  -> human approves/rejects
  -> Task row created (or rejected, logged as AuditLog(OVERRIDE))
  -> get_task_audit_trail (Day 34) reconstructs the full history
```

This report documents what's logged, what's been evaluated, the FP/FN risk
profile, and what is NOT yet covered — the same structure F1/F2's audit docs
use, so all three features can be read the same way by an examiner.

---

## 2. Model & Prompt Versions in Use

| Component | Value |
|-----------|-------|
| Primary model | `claude-sonnet-4-20250514` |
| Fallback model | `claude-haiku-4-5-20251001` (offline dev only) |
| Prompt version | `v2` (Day 33 — bare-JSON output replaced with `create_task` tool call) |
| Tool schemas | `create_task`, `assign_owner`, `set_due_date`, `link_regulation` (`src/f4_tasks/tools.py`, Day 33) |

Per CLAUDE.md's hard constraint, every `AuditLog(TASK_CREATE)` and
`AuditLog(OVERRIDE)` entry stores `model` and `prompt_version` alongside the
finding/edit. This is what let Day 34's verification confirm the live system
is actually running prompt v2 (not a stale v1 path) — see Section 4.

---

## 3. AuditLog Coverage

| AuditAction | Written by | Scoped to | Captures |
|-------------|-----------|-----------|----------|
| `SUMMARISE` | F2 | `doc_id` (regulation) | model, prompt_version, confidence_score, review_flag, or error |
| `TASK_CREATE` | F4 (`create_task`) | `task_id` (in payload) | model, prompt_version, approved_by, edits_applied |
| `OVERRIDE` | F4 (`assign_owner`/`set_due_date`/`link_regulation`, and HITL rejection) | `task_id` (in payload) | field, before/after, actor |
| `INGEST` | F1 | per agency-run only — **no `doc_id`** | run-level counts |
| `MAP` | F3 | **never written** | — |

`get_task_audit_trail(task_id)` (Day 34) joins the first three rows above
into one chronological trail. The last two are **known gaps**, documented
since Day 34 and carried into [Incident-Response-Plan-v1.md](Incident-Response-Plan-v1.md):
F1's ingest log can't be traced to a specific document, and F3 never logs a
mapping decision at all, so a `Task`'s trail currently starts at F2
(summarisation), not at ingestion or impact-mapping.

---

## 4. Eval Results

`evals/f4_eval.py` — structural/traceability validation (no golden
"good task" labels exist yet; see eval docstring for the explicitly
documented gap on semantic quality).

```
F4 STRUCTURAL VALIDATION — 5/5 tasks pass (100.0%)
CI gate: 100% structural validity
```

| Check | Result |
|-------|--------|
| Title references source policy section_id + regulation title | 5/5 pass |
| Owner is a valid persona (Sarah/Mike) | 5/5 pass |
| due_date is a valid ISO date | 5/5 pass |
| Description contains a verbatim evidence excerpt from the matched regulation chunk | 5/5 pass |

**Live verification (Day 35):** `scripts/f4_mvp_demo.py` ran the full chain
on a real F3 HIGH finding and produced `Task` `67fc89e1-...` with
`prompt_version=v2` and `approved_by=human:sarah` in its `TASK_CREATE`
audit entry — confirming the v2 tool-call path (not v1's bare-JSON path) is
what's actually live.

**Documented gap:** structural validity (100%) is not the same as semantic
correctness (is the due date *actually* right?). No golden set exists for
this yet — see Section 6.

---

## 5. FP/FN Risk Analysis (F4-specific)

Following the same asymmetry framing as [FP-FN-Risk-Matrix.md](FP-FN-Risk-Matrix.md):

### False Negative: a real HIGH-impact finding never becomes a task

**Scenario:** F3 correctly flags a HIGH finding, but the F4 agent fails to
call `create_task` (e.g. malformed tool args get rejected and the agent
gives up) — the finding silently produces no task.

**Consequence:** Same as F2's FN — a real compliance requirement never
reaches Sarah. **Severity: CRITICAL.**

**Mitigation:** `create_task`'s Pydantic validation (Day 33) rejects bad
`owner`/`due_date` and feeds the error back to the model to retry, rather
than failing silently. **Gap:** there is no alerting if an F3 HIGH finding
has zero corresponding `Task` rows after some time window — this is a
manual/periodic check today.

### False Positive: F4 drafts a task with wrong content

**Scenario:** Day 34's RCA scenario — F2's NER mis-extracts a
`compliance_deadline`, F4's `get_regulation_deadline` returns the wrong
date, and the draft `Task` has an incorrect `due_date`.

**Consequence:** Sarah may approve a task with a wrong deadline.
**Severity: HIGH** (per RCA, this is the SEV-1 case in
[Incident-Response-Plan-v1.md](Incident-Response-Plan-v1.md)).

**Mitigation:**
- HITL gate (Day 32) — a human reviews title/owner/due_date/description
  before creation, so this is "false positive caught before action" *if*
  Sarah catches it.
- `set_due_date`/`assign_owner`/`link_regulation` (Day 33) allow
  post-creation correction, each writing `AuditLog(OVERRIDE)`.
- `get_task_audit_trail` (Day 34) lets an investigator reconstruct exactly
  which F2 run produced the deadline that fed the task.

**Gap:** nothing currently re-validates a `compliance_deadline` against the
source regulation text at the point F4 reads it — the RCA's "source-sentence
grounding for deadlines" follow-up directly addresses this and remains open.

### Asymmetry Summary

| Scenario | Cost | Current control |
|----------|------|------------------|
| HIGH finding never drafted (FN) | Missed compliance deadline -> $500K-$5M exam finding (same as F2) | `create_task` validation + retry; no FN-detection alert (gap) |
| Wrong due_date/content drafted (FP) | Wrong compliance plan if approved; trust erosion if caught | HITL approval gate; post-creation override tools; audit trail for investigation |
| Task rejected in HITL | None — by design | `AuditLog(OVERRIDE)` with `rejected_task` payload |

Consistent with F1/F2's matrix: **when uncertain, the system should produce
a draft for human review rather than silently doing nothing or silently
auto-creating.** F4's HITL gate is the embodiment of that principle for
task creation specifically.

---

## 6. SR 11-7 Alignment

| SR 11-7 Principle | F4 Implementation |
|---|---|
| Model/prompt versioning on every AI decision | `AuditLog(TASK_CREATE/OVERRIDE)` stores `model` + `prompt_version` (verified live = v2, Section 4) |
| Effective challenge / human oversight | LangGraph HITL interrupt (Day 32) — no `Task` is created without explicit approval |
| Ongoing monitoring | `evals/f4_eval.py` CI gate (100% structural validity); this report itself, as a periodic audit |
| Traceability of inputs | `get_task_audit_trail` (Day 34) reconstructs F2 -> F4 history per task |
| Incident response | [Incident-Response-Plan-v1.md](Incident-Response-Plan-v1.md), with this report's Section 5 feeding its severity definitions |

---

## 7. Known Gaps / Follow-Ups (carried forward)

1. **F3 never writes `AuditAction.MAP`** — a `Task`'s audit trail has no
   record of *why* F3 classified the finding as HIGH. (Day 34 RCA, Day 35
   Incident Plan.)
2. **F1 `INGEST` entries aren't doc-scoped** — can't trace a `Task` back to
   the specific ingestion event for its source regulation.
3. **No source-sentence grounding for `compliance_deadline`** — the FP risk
   in Section 5 remains open.
4. **No golden "good task" eval set** — `f4_eval.py` is structural only;
   semantic quality (is the due date/title actually good?) is unmeasured.
5. **No automated FN-detection** — an F3 HIGH finding with zero resulting
   `Task` rows is not flagged.
6. **v1 always assigns `owner="Sarah"`** — Mike's persona has no task-owner
   path yet (documented in `prompts.py` since Day 31).

None of these are new — each is restated here from its original day's notes
specifically so this report is a single place to see F4's full risk posture
without re-reading 5 days of notes.

---

## Review Schedule

Review and update this report:
- After Day 36+ (Week 6) if F4 v2 changes prompt_version, tool schemas, or
  the HITL flow.
- After any of the gaps in Section 7 are closed.
- After first pilot client onboarding (real-world FP/FN data, same trigger
  as [FP-FN-Risk-Matrix.md](FP-FN-Risk-Matrix.md)).

*Last reviewed: 2026-06-13*
