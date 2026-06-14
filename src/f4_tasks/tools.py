"""
Tools for F4's ReAct task-drafting agent.

Each tool wraps a plain lookup function (`_lookup_*`) that returns a dict.
The plain functions are unit-testable without any LLM or LangGraph involved
(see tests/test_f4_tools.py). The @tool-decorated wrappers are what the
agent actually calls -- they serialise the dict to JSON text, which is the
format LangGraph tool results are returned to the model in.
"""

import json
from datetime import date
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, field_validator

from src.database import get_session
from src.f3_impact.citations import POLICIES_DIR
from src.f3_impact.extractor import extract_policy_file
from src.models import AuditAction, AuditLog, RegulatoryDocument, Task


def _lookup_regulation_deadline(regulation_doc_id: str) -> dict:
    """
    Look up F2's extracted deadline fields for a regulation document.

    F2's NER step (src/f2_summarise/ner.py) writes effective_date and
    compliance_deadline into RegulatoryDocument.summary_json. Returns
    found=False if the document doesn't exist or has no summary yet.
    """
    with get_session() as session:
        doc = session.get(RegulatoryDocument, regulation_doc_id)
        if doc is None or doc.summary_json is None:
            return {
                "found": False,
                "effective_date": None,
                "compliance_deadline": None,
            }

        summary = json.loads(doc.summary_json)
        return {
            "found": True,
            "effective_date": summary.get("effective_date"),
            "compliance_deadline": summary.get("compliance_deadline"),
        }


def _lookup_policy_section_text(policy_name: str, section_id: str) -> dict:
    """
    Look up the full text of a policy section from its fixture file.

    Reads fixtures/policies/<policy_name>.txt via F3's extractor. Returns
    found=False if the policy file or section_id doesn't exist.
    """
    policy_path = POLICIES_DIR / f"{policy_name}.txt"
    if not policy_path.exists():
        return {"found": False, "section_title": None, "parent_section": None, "text": None}

    for section in extract_policy_file(policy_path):
        if section.section_id == section_id:
            return {
                "found": True,
                "section_title": section.section_title,
                "parent_section": section.parent_section,
                "text": section.text,
            }

    return {"found": False, "section_title": None, "parent_section": None, "text": None}


@tool
def get_regulation_deadline(regulation_doc_id: str) -> str:
    """
    Look up the compliance_deadline and effective_date for a regulation
    document, extracted by F2's NER step. Returns a JSON string with keys
    found, effective_date, compliance_deadline. If found is false, or both
    dates are null, no deadline information is available for this regulation.
    """
    return json.dumps(_lookup_regulation_deadline(regulation_doc_id))


@tool
def get_policy_section_text(policy_name: str, section_id: str) -> str:
    """
    Look up the full text of a bank policy section by policy_name and
    section_id. Returns a JSON string with keys found, section_title,
    parent_section, text.
    """
    return json.dumps(_lookup_policy_section_text(policy_name, section_id))


# ── create_task (Day 33, KM #178) ──────────────────────────────────────────
#
# Pydantic validates owner/due_date AT THE TOOL CALL boundary. If the model
# calls create_task with owner="Bob" or due_date="not a date", Pydantic
# raises ValidationError before our function body ever runs; LangGraph's
# ToolNode turns that into a ToolMessage error that's fed back to the model,
# so the model retries with a corrected value -- self-correcting, instead of
# only being caught by evals/f4_eval.py after the fact (v1's failure mode).

class CreateTaskArgs(BaseModel):
    title: str
    description: str
    owner: Literal["Sarah", "Mike"]
    due_date: str  # YYYY-MM-DD

    @field_validator("due_date")
    @classmethod
    def _due_date_is_iso(cls, v: str) -> str:
        date.fromisoformat(v)
        return v


@tool("create_task", args_schema=CreateTaskArgs)
def create_task(title: str, description: str, owner: str, due_date: str) -> str:
    """
    Record the drafted compliance task. This is the agent's FINAL action --
    call it exactly once, after both lookup tools, with the title,
    description, owner, and due_date for the task being drafted.
    """
    return json.dumps({
        "title": title,
        "description": description,
        "owner": owner,
        "due_date": due_date,
    })


# ── Task-management tools (Day 33) ──────────────────────────────────────────
#
# These operate on Task rows that already exist (created via Day 32's
# resolve_approval). Each is a human-initiated edit, not an agent draft --
# every change writes an AuditLog(OVERRIDE) row recording the before/after
# values, per the SR 11-7 "every AI decision and override is logged" rule.

class AssignOwnerArgs(BaseModel):
    task_id: str
    owner: Literal["Sarah", "Mike"]


@tool("assign_owner", args_schema=AssignOwnerArgs)
def assign_owner(task_id: str, owner: str) -> str:
    """
    Reassign an existing Task to a different owner ("Sarah" or "Mike").
    Writes an AuditLog(OVERRIDE) row recording the before/after owner.
    Returns a JSON string with key found (False if task_id doesn't exist).
    """
    with get_session() as session:
        task = session.get(Task, task_id)
        if task is None:
            return json.dumps({"found": False})

        before = task.owner
        task.owner = owner
        session.add(task)
        session.add(AuditLog(
            action=AuditAction.OVERRIDE,
            actor="human:sarah",
            payload_json=json.dumps({
                "task_id": task_id,
                "field": "owner",
                "before": before,
                "after": owner,
            }),
        ))
        session.commit()
        return json.dumps({"found": True, "task_id": task_id, "owner": owner})


class SetDueDateArgs(BaseModel):
    task_id: str
    due_date: str  # YYYY-MM-DD

    @field_validator("due_date")
    @classmethod
    def _due_date_is_iso(cls, v: str) -> str:
        date.fromisoformat(v)
        return v


@tool("set_due_date", args_schema=SetDueDateArgs)
def set_due_date(task_id: str, due_date: str) -> str:
    """
    Change an existing Task's due_date (YYYY-MM-DD). Writes an
    AuditLog(OVERRIDE) row recording the before/after due_date. Returns a
    JSON string with key found (False if task_id doesn't exist).
    """
    with get_session() as session:
        task = session.get(Task, task_id)
        if task is None:
            return json.dumps({"found": False})

        before = task.due_date
        task.due_date = due_date
        session.add(task)
        session.add(AuditLog(
            action=AuditAction.OVERRIDE,
            actor="human:sarah",
            payload_json=json.dumps({
                "task_id": task_id,
                "field": "due_date",
                "before": before,
                "after": due_date,
            }),
        ))
        session.commit()
        return json.dumps({"found": True, "task_id": task_id, "due_date": due_date})


class LinkRegulationArgs(BaseModel):
    task_id: str
    regulation_doc_id: str
    regulation_title: str


@tool("link_regulation", args_schema=LinkRegulationArgs)
def link_regulation(task_id: str, regulation_doc_id: str, regulation_title: str) -> str:
    """
    Add a regulation to an existing Task's linked_regulations_json list (for
    regulations relevant to the task beyond the one that originally produced
    it). Writes an AuditLog(OVERRIDE) row recording the addition. Returns a
    JSON string with key found (False if task_id doesn't exist).
    """
    with get_session() as session:
        task = session.get(Task, task_id)
        if task is None:
            return json.dumps({"found": False})

        linked = json.loads(task.linked_regulations_json) if task.linked_regulations_json else []
        linked.append({
            "regulation_doc_id": regulation_doc_id,
            "regulation_title": regulation_title,
        })
        task.linked_regulations_json = json.dumps(linked)
        session.add(task)
        session.add(AuditLog(
            action=AuditAction.OVERRIDE,
            actor="human:sarah",
            payload_json=json.dumps({
                "task_id": task_id,
                "field": "linked_regulations_json",
                "added": {
                    "regulation_doc_id": regulation_doc_id,
                    "regulation_title": regulation_title,
                },
            }),
        ))
        session.commit()
        return json.dumps({"found": True, "task_id": task_id, "linked_regulations": linked})
