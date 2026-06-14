# Day 31 — F4 v1: ReAct Task-Drafting Agent (KM #177)

**Date:** 2026-06-13
**Feature:** F4 — Task Generation (Week 5, Day 3 of 7)
**KM:** #177 ReAct
**Status:** F4 v1 built and run end-to-end. Generated 5 tasks from F3 HIGH
findings, all 5 pass the new structural eval (100% — CI gate met on first run).

---

## What Was Built

| File | Change |
|------|--------|
| `src/models.py` | New `TaskStatus` enum (`open`/`in_progress`/`completed`) and `Task` table — F4's output, with `source_*` fields for traceability back to the originating F3 finding. |
| `src/f4_tasks/prompts.py` | NEW — `PROMPT_VERSION = "v1"`, `PRIMARY_MODEL`/`FALLBACK_MODEL` (same as F2), `SYSTEM_PROMPT` for the ReAct agent. |
| `src/f4_tasks/tools.py` | NEW — `get_regulation_deadline` and `get_policy_section_text`, LangChain `@tool`-wrapped lookups over F2's NER output and F3's policy fixtures. |
| `src/f4_tasks/agent.py` | NEW — `create_react_agent` (LangGraph) + `ChatAnthropic`, `load_high_findings()`, `run()` — generates tasks, writes `Task`/`AuditLog` rows and `data/f4_tasks/tasks.json`. |
| `evals/f4_eval.py` | NEW — structural/traceability eval. CI gate = 100% pass rate. |
| `tests/test_f4_tools.py`, `tests/test_f4_eval.py` | NEW — 14 tests total, no LLM calls. |
| `requirements.txt` | Added `langgraph==1.2.5`, `langchain-anthropic==1.4.6` under the F4 section. |
| `docs/Task-Board-UX-v1.md` | NEW — Kanban wireframe (Open/In Progress/Completed) with task card + evidence trail + Approve action. |
| `docs/ARCHITECTURE.md` | New entries for all of the above. |
| `data/f4_tasks/tasks.json` | Generated — 5 tasks from real Anthropic API calls (gitignored). |

---

## Roadmap v2.2 — Day 31 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | #177 ReAct | `create_react_agent` (LangGraph prebuilt) + `ChatAnthropic`, 2 tools |
| Engineering | Task generation agent v1 | `src/f4_tasks/agent.py`, `tools.py`, `prompts.py` |
| Product | (carried from Day 31 plan) Task Board UX wireframe | `docs/Task-Board-UX-v1.md` |
| Deliverable | First AI-drafted compliance tasks from F3 HIGH findings | `data/f4_tasks/tasks.json` (5 tasks) |

---

## What Was Built and Why

F3 ends with `impact_results.json` — a list of (policy section, regulation)
pairs with an `impact_level`. That's information; it isn't yet something
Sarah can act on. F4's job is to turn a HIGH finding into a concrete task:
*what to review, why, and by when.*

A ReAct agent (not a single prompt) was chosen because the task needs two
pieces of grounded context the model can't know on its own:
1. **The actual policy section text** (`get_policy_section_text`) — so the
   description references what the CURRENT policy says, not a guess.
2. **The regulation's compliance deadline** (`get_regulation_deadline`,
   sourced from F2's NER extraction) — so `due_date` is grounded in a real
   date when one exists, not invented.

The agent calls both tools, then returns a single JSON object (title,
description, owner, due_date) which `agent.py` parses directly — no
structured-output API needed for v1, just a strict prompt contract.

---

## Eval-First Framing (build rule 7)

No golden "good task" labels exist — there's no way yet to say a generated
title or due date is *correct*. So Day 31's CI gate is **structural, not
semantic**: every task must (1) reference its source policy section AND
regulation in the title, (2) have `owner` in `{"Sarah","Mike"}`, (3) have a
valid ISO `due_date`, (4) include a real verbatim excerpt from the matched
regulation text in its description (checked via longest-common-substring,
`autojunk=False`, >= 30 chars).

This is the same honest-caveat pattern as F3's Claude-labeled golden set:
the eval proves the AGENT FOLLOWED THE PROCESS (used real evidence, cited
its sources, produced parseable output) — not that the resulting task is a
*good* one. Semantic quality (is this due date actually right? is this the
most important task Sarah should do?) is an explicit gap for a future day,
once there's a way to get Sarah's judgment into a golden set.

---

## Result

```
Generated 5 tasks -> data/f4_tasks/tasks.json
  - Fair-Lending-ECOA-Policy Section 1.1 - Equal Credit Opportunity Act (Regulation B)   (due 2026-07-21, owner=Sarah)
  - Fair-Lending-ECOA-Policy Section 1.2 - Equal Credit Opportunity Act (Regulation B)   (due 2026-07-21, owner=Sarah)
  - Fair-Lending-ECOA-Policy Section 1.3 - Equal Credit Opportunity Act (Regulation B)   (due 2026-07-21, owner=Sarah)
  - Fair-Lending-ECOA-Policy Section 1.3 - Small Business Lending Under the ECOA (Reg B) (due 2026-07-13, owner=Sarah)
  - Fair-Lending-ECOA-Policy Section 2.1 - Equal Credit Opportunity Act (Regulation B)   (due 2026-07-21, owner=Sarah)

evals/f4_eval.py: 5/5 tasks pass (100.0%) — CI gate met
tests: 14/14 new tests pass; 127/127 total tests pass
```

4 of 5 tasks ground `due_date` in Regulation B's real `compliance_deadline`
(2026-07-21, from F2's NER). The 5th finding (Small Business Lending Under
ECOA / Reg B §1071) had no deadline in its summary, so the agent correctly
fell back to the 30-day default SLA (2026-07-13 = 2026-06-13 + 30 days) and
added the documented note in its description, exactly as the prompt
specified.

---

## v1 Documented Limitations

- **5 of 27 HIGH findings** processed (Anthropic API cost control). All 27
  could be run later with `run(limit=27)`.
- **`owner="Sarah"` always.** She's the only persona CLAUDE.md maps to task
  approval; Mike's monitoring/reporting role doesn't have a task-ownership
  analog yet.
- **No semantic quality eval.** Structural validity != "this is the right
  task with the right deadline" — see Eval-First section above.
- **No HITL approval flow yet.** `docs/Task-Board-UX-v1.md` shows an
  "Approve" button conceptually; nothing is wired up. Per the Progressive
  Autonomy Roadmap, every F4-generated task still requires Sarah's review —
  F4 v1 drafts, it doesn't act.
- **LangSmith ingest 403s** during the run (pre-existing, not introduced
  today) — non-fatal, agent completed normally. Not investigated today;
  flag if it recurs and blocks something real.

---

## PM Insight

Day 31 closes the loop on the "moat" framing from earlier weeks: F1 finds
the regulation, F2 explains it, F3 says which policy it affects and how
much, and now F4 turns that into something with an owner and a date. The
ReAct pattern's value here wasn't reasoning depth — it was FORCING the model
to fetch two specific pieces of ground truth (current policy text, real
deadline) before writing anything, which is exactly the SR 11-7 "don't let
the model invent facts it could look up" discipline. The 30-day-SLA
fallback firing correctly on the one finding without a deadline is a small
but real signal that the agent is following the conditional logic in the
prompt, not just pattern-matching to "always cite a date."

---

## Next: Day 32 (when user says "next")

Per roadmap v2.2 — confirm Day 32's columns before starting (build rule 3) —
do not start Day 32 without explicit "next".
