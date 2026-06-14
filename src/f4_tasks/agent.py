"""
F4 task generation agent (Day 31, KM #177 ReAct).

Reads F3 HIGH-impact findings from data/f3_indexes/impact_results.json,
runs a LangGraph ReAct agent (Claude + 2 tools) over a subset of them, and
for each one drafts a Task: title, description, owner, due_date.

Writes:
  - data/f4_tasks/tasks.json   (raw output, for the eval + Task Board UX)
  - Task rows in the DB         (via src.database.get_session)
  - AuditLog rows with action=AuditAction.TASK_CREATE, recording model,
    prompt_version, and the source finding -- per CLAUDE.md's
    "every AI decision logs model version + prompt version + inputs".
"""

import json
from datetime import date, timedelta
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.tracers.context import collect_runs
from langgraph.prebuilt import create_react_agent

from src.database import create_db_and_tables, get_session
from src.f4_tasks.prompts import PRIMARY_MODEL, PROMPT_VERSION, SYSTEM_PROMPT
from src.f4_tasks.tools import create_task, get_policy_section_text, get_regulation_deadline
from src.models import AuditAction, AuditLog, Task

IMPACT_RESULTS_PATH = Path("data/f3_indexes/impact_results.json")
TASKS_OUTPUT_PATH = Path("data/f4_tasks/tasks.json")

# v1 default SLA when a regulation has no compliance_deadline/effective_date.
# Documented limitation -- see notes/Day-31-F4.md.
DEFAULT_SLA_DAYS = 30


def load_high_findings() -> list[dict]:
    """
    Flatten impact_results.json into one dict per (policy section, regulation)
    pair where impact_level == "high".

    impact_results.json is structured as a list of policy sections, each
    with a "matches" list of regulation matches -- flattening here gives F4
    one finding per row, which is what the agent operates on.
    """
    sections = json.loads(IMPACT_RESULTS_PATH.read_text(encoding="utf-8"))
    findings = []
    for section in sections:
        section_meta = {
            "policy_name": section["policy_name"],
            "section_id": section["section_id"],
            "section_title": section["section_title"],
            "parent_section": section["parent_section"],
        }
        for match in section["matches"]:
            if match["impact_level"] == "high":
                findings.append({**section_meta, **match})
    return findings


def build_agent():
    """Build the ReAct agent: Claude Sonnet + the 2 F4 lookup tools + create_task."""
    model = ChatAnthropic(model=PRIMARY_MODEL, temperature=0)
    return create_react_agent(
        model,
        tools=[get_regulation_deadline, get_policy_section_text, create_task],
        prompt=SYSTEM_PROMPT,
    )


def _extract_create_task_args(messages: list) -> dict:
    """
    Find the agent's create_task tool call in the message history and return
    its (already Pydantic-validated) args dict.

    v2 (Day 33): the agent's draft is no longer free-form JSON text -- it's
    the arguments of a create_task tool call, validated against
    CreateTaskArgs (src/f4_tasks/tools.py) before this code ever sees it.
    Raises ValueError if the agent never called create_task.
    """
    for message in messages:
        for tool_call in getattr(message, "tool_calls", None) or []:
            if tool_call["name"] == "create_task":
                return tool_call["args"]
    raise ValueError("Agent did not call create_task")


def generate_task_for_finding(agent, finding: dict, today: date) -> dict:
    """
    Run the agent on one HIGH finding and return the drafted task dict
    (title, description, owner, due_date) plus the source_* traceability
    fields needed to build a Task row.
    """
    user_message = (
        f"Today's date is {today.isoformat()}.\n\n"
        f"F3 finding (JSON):\n{json.dumps(finding, indent=2)}"
    )

    # Day 37 (KM #241 LangSmith): collect_runs() captures every run of this
    # agent.invoke() call (LangGraph/LangChain are auto-traced when
    # LANGCHAIN_TRACING_V2=true) -- one per graph step/tool call, plus the
    # root "LangGraph" run. The root run (parent_run_id is None) is the one
    # that represents this whole agent invocation in the LangSmith UI. If
    # tracing isn't configured, cb.traced_runs is empty and trace_id stays
    # None -- agent behaviour is unaffected.
    with collect_runs() as cb:
        result = agent.invoke({"messages": [{"role": "user", "content": user_message}]})

    trace_id = None
    for run in cb.traced_runs:
        if run.parent_run_id is None:
            trace_id = str(run.id)
            break
    drafted = _extract_create_task_args(result["messages"])

    return {
        "source_policy_name": finding["policy_name"],
        "source_section_id": finding["section_id"],
        "source_regulation_doc_id": finding["regulation_doc_id"],
        "source_regulation_title": finding["regulation_title"],
        "source_impact_level": finding["impact_level"],
        "title": drafted["title"],
        "description": drafted["description"],
        "owner": drafted["owner"],
        "due_date": drafted["due_date"],
        "_langsmith_trace_id": trace_id,
    }


def run(limit: int = 5) -> list[dict]:
    """
    Generate tasks for the first `limit` HIGH findings, persist Task +
    AuditLog rows, and write data/f4_tasks/tasks.json.
    """
    create_db_and_tables()

    findings = load_high_findings()[:limit]
    agent = build_agent()
    today = date.today()

    tasks = []
    with get_session() as session:
        for finding in findings:
            task_dict = generate_task_for_finding(agent, finding, today)
            trace_id = task_dict.pop("_langsmith_trace_id", None)
            tasks.append(task_dict)

            task_row = Task(**task_dict)
            session.add(task_row)

            session.add(
                AuditLog(
                    action=AuditAction.TASK_CREATE,
                    actor="system:f4",
                    doc_id=finding["regulation_doc_id"],
                    langsmith_trace_id=trace_id,
                    payload_json=json.dumps({
                        "model": PRIMARY_MODEL,
                        "prompt_version": PROMPT_VERSION,
                        "source_policy_name": finding["policy_name"],
                        "source_section_id": finding["section_id"],
                        "source_regulation_doc_id": finding["regulation_doc_id"],
                        "task_id": task_row.id,
                        "default_sla_days": DEFAULT_SLA_DAYS,
                    }),
                )
            )

        session.commit()

    TASKS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    TASKS_OUTPUT_PATH.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    return tasks


if __name__ == "__main__":
    generated = run(limit=5)
    print(f"Generated {len(generated)} tasks -> {TASKS_OUTPUT_PATH}")
    for t in generated:
        print(f"  - {t['title']}  (due {t['due_date']}, owner={t['owner']})")
