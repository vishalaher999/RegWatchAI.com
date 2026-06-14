# Day 33 — F4 Tool Schemas (KM #178)

**Date:** 2026-06-13
**Feature:** F4 — Task Generation (Week 5, Day 5 of 7)
**KM:** #178 Tool schemas
**Status:** Agent output is now a validated `create_task` tool call, plus
3 new DB-backed task-management tools. 141/141 tests pass.

---

## What Was Built

| File | Change |
|------|--------|
| `src/models.py` | `Task` gains `linked_regulations_json` (Optional JSON list of `{regulation_doc_id, regulation_title}`). |
| `src/f4_tasks/prompts.py` | `PROMPT_VERSION` bumped `"v1"` -> `"v2"`. `SYSTEM_PROMPT` now instructs the agent to call `create_task(...)` as its final action instead of returning bare JSON. |
| `src/f4_tasks/tools.py` | NEW: `CreateTaskArgs`/`create_task` (Pydantic-validated `owner`/`due_date`). NEW: `assign_owner`, `set_due_date`, `link_regulation` — DB-backed, each writes `AuditLog(OVERRIDE)`. |
| `src/f4_tasks/agent.py` | `build_agent()` adds `create_task` to its tool list. `_parse_agent_output` removed; new `_extract_create_task_args()` reads validated args off the agent's `create_task` tool call. |
| `tests/test_f4_tools.py` | +10 tests: `create_task` schema validation, `assign_owner`/`set_due_date`/`link_regulation` (in-memory SQLite). |
| `docs/Notification-UX-v1.md` | NEW — draft email templates for "new task assigned" / "task overdue" (drafts only, no send path). |
| `docs/ARCHITECTURE.md` | Entries updated for `models.py`, `prompts.py`, `tools.py`, `agent.py`; new entry for `Notification-UX-v1.md`. |

---

## Roadmap v2.2 — Day 33 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | #178 Tool schemas | `CreateTaskArgs`/`create_task` + `AssignOwnerArgs`/`SetDueDateArgs`/`LinkRegulationArgs` in `tools.py` |
| Engineering | Validated tool-call output for task drafts; task-management tools | `create_task` replaces free-JSON output; `assign_owner`/`set_due_date`/`link_regulation` are DB-backed with audit logging |
| Product | Notification UX for task assignment/overdue | `docs/Notification-UX-v1.md` |
| Deliverable | Self-correcting drafting via Pydantic validation | Verified: invalid `owner`/`due_date` raise `ValidationError` at the tool boundary |

---

## What Changed and Why

v1's agent ended its turn with a bare JSON object, parsed by
`_parse_agent_output()` (stripping ```json fences). Nothing validated the
JSON's *shape* until `evals/f4_eval.py` ran afterward — by then, a bad
`owner` or unparseable `due_date` was already baked into `tasks.json` and
(in Day 32's flow) potentially already shown to Sarah as a pending draft.

KM #178 moves that validation to the tool-call boundary. `create_task` has
`args_schema=CreateTaskArgs`, a Pydantic model where:

- `owner: Literal["Sarah", "Mike"]` — any other value fails Pydantic
  validation.
- `due_date: str` with a `@field_validator` calling `date.fromisoformat(v)`
  — a non-ISO string fails validation.

When the agent calls `create_task` with an invalid argument, LangGraph's
`ToolNode` catches the `ValidationError` and returns it to the model as a
`ToolMessage` — the model sees *why* its call failed and can retry with a
corrected value, in the same turn. This is "self-correcting" in a way that
post-hoc eval checks are not: the eval can only report a failure after the
fact, while the tool boundary can make the agent fix it before it ever
becomes a draft.

`generate_task_for_finding()` no longer parses text at all. It scans
`result["messages"]` for the `AIMessage` whose `tool_calls` includes
`name == "create_task"`, and reads `tool_call["args"]` directly — these args
are *already* validated `CreateTaskArgs` data by the time they reach this
code. The function's return shape (`source_*` + `title`/`description`/
`owner`/`due_date`) is unchanged, so `hitl_agent.py`'s `draft` node needed no
changes — confirmed by re-running `tests/test_f4_hitl.py` (still 4/4) and the
full suite (141/141).

The three management tools (`assign_owner`, `set_due_date`, `link_regulation`)
are a different category: they operate on a `Task` row that already exists
(created via Day 32's `resolve_approval`), as human-initiated edits rather
than agent drafts. Each writes `AuditLog(OVERRIDE)` with the before/after
values — per CLAUDE.md's "every AI decision logs model version + prompt
version + inputs" and SR 11-7's emphasis on a complete record of overrides.
`link_regulation` is why `Task.linked_regulations_json` exists: a task can
turn out to be relevant to a regulation beyond the one that originally
produced it, and that needs to be recorded without losing the original
`source_regulation_*` traceability.

---

## Result

Real end-to-end run on 1 HIGH finding (Fair-Lending-ECOA-Policy Section 1.1
vs. Equal Credit Opportunity Act / Regulation B) confirmed `create_task`
tool-call extraction works in practice:

```json
{
  "source_policy_name": "Fair-Lending-ECOA-Policy",
  "source_section_id": "1.1",
  "source_regulation_doc_id": "c5ba5ac6-a2ac-4522-a4b4-23c19d492dd3",
  "source_regulation_title": "Equal Credit Opportunity Act (Regulation B)",
  "source_impact_level": "high",
  "title": "Fair-Lending-ECOA-Policy Section 1.1 - Equal Credit Opportunity Act (Regulation B) Update",
  "description": "...quotes the regulation's matched text verbatim...",
  "owner": "Sarah",
  "due_date": "2026-07-21"
}
```

Tests: 16/16 in `tests/test_f4_tools.py` (6 original + 10 new), 141/141 total
suite.

---

## v1 Documented Limitations (carried over / unchanged)

- `owner="Sarah"` always in drafts (v1 limitation, unchanged in v2) — `Mike`
  is now a *valid* value for `create_task`/`assign_owner`/`set_due_date`'s
  schemas, but the prompt still never asks the agent to choose him.
- No semantic golden set for F4 drafts (still only structural eval).
- `InMemorySaver` checkpointer (Day 32) — unchanged.
- `Notification-UX-v1.md` templates have no send path and no scheduled job
  to detect overdue tasks.

---

## PM Insight

The shift from "validate after the fact" to "validate at the boundary" is
small in code (one Pydantic model) but changes *where* a bad value gets
caught — and therefore who has to deal with it. In v1, a bad `due_date`
would show up in `tasks.json`, then fail `evals/f4_eval.py`'s CI gate, and a
human would have to go figure out which finding produced it. In v2, the
model itself gets the validation error mid-turn and can just... try again.
That's the same "self-correction" pattern as a compiler type error vs. a
runtime crash three steps later — catching it closer to the source means
the agent (or a future developer) has more context to fix it.

The three management tools are the first F4 surface that's explicitly for
*humans editing AI output after the fact* — not drafting, not approving,
but correcting. Each one is small, but together they're the foundation of
"Sarah can fix what the AI got wrong without losing the audit trail," which
is the other half of SR 11-7 (not just "log AI decisions" but "log
overrides too, with enough detail to reconstruct what changed and why").

---

## Next: Day 34 (when user says "next")

Per roadmap v2.2 — confirm Day 34's columns before starting (build rule 3) —
do not start Day 34 without explicit "next".
