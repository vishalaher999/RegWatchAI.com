"""
F4 HITL approval gate (Day 32, KM #190-191 LangGraph HITL).

Day 31's agent.run() drafted a Task and immediately wrote it to the DB as
status=open -- nothing stopped an unreviewed task from going live. Day 32
wraps the Day 31 ReAct agent in a small parent graph that PAUSES via
LangGraph's interrupt() before any DB write, and only proceeds once a human
resumes the graph with a Command(resume=...) decision.

This is Stage 2 of docs/Progressive-Autonomy-Roadmap-v1.md: tasks for HIGH
findings are auto-drafted, but every one still requires Sarah's approval --
enforced in the graph's control flow, not just a UI button.

Graph:
    START -> draft -> await_approval -> finalize -> END

  draft:          runs Day 31's generate_task_for_finding() (or a injected
                   draft_fn for testing) -- no DB writes.
  await_approval: interrupt(drafted_task) -- pauses here. Resuming requires
                   Command(resume={"approved": bool, "edits": dict | None}).
  finalize:       approved=True  -> writes Task(status=open) + AuditLog
                                     (TASK_CREATE), applying `edits` first.
                   approved=False -> writes AuditLog(OVERRIDE) recording the
                                     rejected draft. No Task row is created.

v1 limitation: checkpointer is InMemorySaver -- pending approvals are lost
if the process restarts. A future day could swap to SqliteSaver (same DB).
"""

import json
import uuid
from datetime import date
from typing import Optional, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from src.database import create_db_and_tables, get_session
from src.f4_tasks.agent import build_agent, generate_task_for_finding, load_high_findings
from src.f4_tasks.notifications import render_new_task_notification, write_to_outbox
from src.f4_tasks.prompts import PRIMARY_MODEL, PROMPT_VERSION
from src.models import AuditAction, AuditLog, Task


class HITLState(TypedDict):
    finding: dict
    drafted_task: Optional[dict]
    decision: Optional[dict]
    result: Optional[dict]


def build_graph(draft_fn=None):
    """
    Build the HITL graph.

    draft_fn(finding: dict, today: date) -> dict, returning the same shape
    as agent.generate_task_for_finding(). Defaults to a real ReAct agent
    (real Anthropic API calls). Tests inject a fake draft_fn to avoid LLM
    calls entirely.
    """
    if draft_fn is None:
        agent = build_agent()

        def draft_fn(finding: dict, today: date) -> dict:
            return generate_task_for_finding(agent, finding, today)

    def draft(state: HITLState) -> dict:
        return {"drafted_task": draft_fn(state["finding"], date.today())}

    def await_approval(state: HITLState) -> dict:
        decision = interrupt(state["drafted_task"])
        return {"decision": decision}

    def finalize(state: HITLState) -> dict:
        finding = state["finding"]
        decision = state["decision"]
        task_dict = dict(state["drafted_task"])
        trace_id = task_dict.pop("_langsmith_trace_id", None)
        edits = decision.get("edits") or {}
        task_dict.update(edits)

        with get_session() as session:
            if decision.get("approved"):
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
                            "edits_applied": edits,
                            "approved_by": "human:sarah",
                        }),
                    )
                )
                session.commit()

                # Day 42: queue a "new task assigned" notification (generation
                # + outbox only -- no actual send, see notifications.py docstring)
                write_to_outbox(
                    render_new_task_notification(task_row),
                    task_id=task_row.id,
                    kind="new_task_assigned",
                )

                return {"result": {"status": "created", "task_id": task_row.id}}

            session.add(
                AuditLog(
                    action=AuditAction.OVERRIDE,
                    actor="human:sarah",
                    doc_id=finding["regulation_doc_id"],
                    payload_json=json.dumps({
                        "model": PRIMARY_MODEL,
                        "prompt_version": PROMPT_VERSION,
                        "source_policy_name": finding["policy_name"],
                        "source_section_id": finding["section_id"],
                        "source_regulation_doc_id": finding["regulation_doc_id"],
                        "rejected_task": task_dict,
                    }),
                )
            )
            session.commit()
            return {"result": {"status": "rejected"}}

    graph = StateGraph(HITLState)
    graph.add_node("draft", draft)
    graph.add_node("await_approval", await_approval)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "draft")
    graph.add_edge("draft", "await_approval")
    graph.add_edge("await_approval", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=InMemorySaver())


def run_with_approval(limit: int = 5, graph=None) -> tuple[list[dict], object]:
    """
    Draft tasks for the first `limit` HIGH findings and pause each one at
    await_approval. Returns (pending, graph), where pending is a list of:
      {"thread_id": str, "finding": dict, "drafted_task": dict}

    The returned `graph` MUST be passed to resolve_approval() for these
    threads -- InMemorySaver state lives on this compiled graph instance.

    No Task or AuditLog rows are written by this call -- only
    resolve_approval() writes to the DB.
    """
    create_db_and_tables()

    if graph is None:
        graph = build_graph()

    pending = []
    for finding in load_high_findings()[:limit]:
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        result = graph.invoke(
            {"finding": finding, "drafted_task": None, "decision": None, "result": None},
            config=config,
        )
        drafted_task = result["__interrupt__"][0].value
        pending.append({"thread_id": thread_id, "finding": finding, "drafted_task": drafted_task})

    return pending, graph


def resolve_approval(
    graph, thread_id: str, approved: bool, edits: Optional[dict] = None
) -> dict:
    """
    Resume a paused thread with a human decision.

    approved=True  -> writes Task(status=open) + AuditLog(TASK_CREATE),
                       applying `edits` to the drafted task first.
    approved=False -> writes AuditLog(OVERRIDE) only. No Task row created.

    Returns the "result" dict written by the finalize node.
    """
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(Command(resume={"approved": approved, "edits": edits}), config=config)
    return result["result"]
