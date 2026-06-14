"""Tests for src/f4_tasks/tools.py — no LLM calls, real fixture/DB data."""

import json
from contextlib import contextmanager

import pytest
from pydantic import ValidationError
from sqlmodel import Session, SQLModel, create_engine

from src.database import get_session
from src.f4_tasks import tools as tools_module
from src.f4_tasks.tools import (
    AssignOwnerArgs,
    CreateTaskArgs,
    SetDueDateArgs,
    _lookup_policy_section_text,
    _lookup_regulation_deadline,
    assign_owner,
    create_task,
    link_regulation,
    set_due_date,
)
from src.models import AuditAction, AuditLog, RegulatoryDocument, Task


def test_lookup_policy_section_text_finds_known_section():
    result = _lookup_policy_section_text("Fair-Lending-ECOA-Policy", "1.1")

    assert result["found"] is True
    assert result["section_title"] == "Purpose"
    assert result["parent_section"] == "SECTION 1: PURPOSE AND SCOPE"
    assert result["text"]


def test_lookup_policy_section_text_unknown_policy_not_found():
    result = _lookup_policy_section_text("Does-Not-Exist-Policy", "1.1")

    assert result == {"found": False, "section_title": None, "parent_section": None, "text": None}


def test_lookup_policy_section_text_unknown_section_not_found():
    result = _lookup_policy_section_text("Fair-Lending-ECOA-Policy", "99.9")

    assert result == {"found": False, "section_title": None, "parent_section": None, "text": None}


def test_lookup_regulation_deadline_known_document():
    """Equal Credit Opportunity Act (Regulation B) — has both dates set."""
    result = _lookup_regulation_deadline("c5ba5ac6-a2ac-4522-a4b4-23c19d492dd3")

    assert result["found"] is True
    assert result["effective_date"] == "2026-07-21"
    assert result["compliance_deadline"] == "2026-07-21"


def test_lookup_regulation_deadline_unknown_document_not_found():
    result = _lookup_regulation_deadline("00000000-0000-0000-0000-000000000000")

    assert result == {"found": False, "effective_date": None, "compliance_deadline": None}


def test_lookup_regulation_deadline_document_without_summary(monkeypatch):
    """A doc with summary_json=None returns found=False (no NER data yet)."""

    class FakeDoc:
        summary_json = None

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, model, doc_id):
            return FakeDoc()

    import src.f4_tasks.tools as tools_module

    monkeypatch.setattr(tools_module, "get_session", lambda: FakeSession())

    result = _lookup_regulation_deadline("some-id")

    assert result == {"found": False, "effective_date": None, "compliance_deadline": None}


# ── create_task schema validation (Day 33) ──────────────────────────────────

VALID_CREATE_TASK_ARGS = {
    "title": "Fair-Lending-ECOA-Policy Section 1.1 - Equal Credit Opportunity Act (Regulation B)",
    "description": "Some evidence text. Review needed.",
    "owner": "Sarah",
    "due_date": "2026-07-21",
}


def test_create_task_accepts_valid_args():
    result = json.loads(create_task.invoke(VALID_CREATE_TASK_ARGS))

    assert result == VALID_CREATE_TASK_ARGS


def test_create_task_rejects_invalid_owner():
    bad_args = {**VALID_CREATE_TASK_ARGS, "owner": "Bob"}

    with pytest.raises(ValidationError):
        CreateTaskArgs(**bad_args)


def test_create_task_rejects_invalid_due_date():
    bad_args = {**VALID_CREATE_TASK_ARGS, "due_date": "not-a-date"}

    with pytest.raises(ValidationError):
        CreateTaskArgs(**bad_args)


# ── DB-backed task-management tools (Day 33) ────────────────────────────────

EXISTING_TASK = dict(
    source_policy_name="Fair-Lending-ECOA-Policy",
    source_section_id="1.1",
    source_regulation_doc_id="c5ba5ac6-a2ac-4522-a4b4-23c19d492dd3",
    source_regulation_title="Equal Credit Opportunity Act (Regulation B)",
    source_impact_level="high",
    title="Fair-Lending-ECOA-Policy Section 1.1 - Equal Credit Opportunity Act (Regulation B)",
    description="Some evidence text. Review needed.",
    owner="Sarah",
    due_date="2026-07-21",
)


@pytest.fixture
def in_memory_engine(monkeypatch):
    """Fresh in-memory SQLite DB with one Task row, same pattern as tests/test_f4_hitl.py."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    @contextmanager
    def mock_get_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(tools_module, "get_session", mock_get_session)

    with Session(engine) as session:
        task = Task(**EXISTING_TASK)
        session.add(task)
        session.commit()
        task_id = task.id

    return engine, task_id


def test_assign_owner_updates_task_and_logs_override(in_memory_engine):
    engine, task_id = in_memory_engine

    result = json.loads(assign_owner.invoke({"task_id": task_id, "owner": "Mike"}))

    assert result == {"found": True, "task_id": task_id, "owner": "Mike"}
    with Session(engine) as session:
        task = session.get(Task, task_id)
        assert task.owner == "Mike"
        logs = session.query(AuditLog).all()
        assert any(log.action == AuditAction.OVERRIDE for log in logs)


def test_assign_owner_rejects_invalid_owner():
    with pytest.raises(ValidationError):
        AssignOwnerArgs(task_id="some-id", owner="Bob")


def test_assign_owner_unknown_task_not_found(in_memory_engine):
    result = json.loads(assign_owner.invoke({"task_id": "does-not-exist", "owner": "Mike"}))

    assert result == {"found": False}


def test_set_due_date_updates_task_and_logs_override(in_memory_engine):
    engine, task_id = in_memory_engine

    result = json.loads(set_due_date.invoke({"task_id": task_id, "due_date": "2026-08-01"}))

    assert result == {"found": True, "task_id": task_id, "due_date": "2026-08-01"}
    with Session(engine) as session:
        task = session.get(Task, task_id)
        assert task.due_date == "2026-08-01"
        logs = session.query(AuditLog).all()
        assert any(log.action == AuditAction.OVERRIDE for log in logs)


def test_set_due_date_rejects_invalid_date():
    with pytest.raises(ValidationError):
        SetDueDateArgs(task_id="some-id", due_date="not-a-date")


def test_link_regulation_appends_and_logs_override(in_memory_engine):
    engine, task_id = in_memory_engine

    result = json.loads(link_regulation.invoke({
        "task_id": task_id,
        "regulation_doc_id": "another-doc-id",
        "regulation_title": "Truth in Lending Act (Regulation Z)",
    }))

    assert result["found"] is True
    assert result["linked_regulations"] == [
        {"regulation_doc_id": "another-doc-id", "regulation_title": "Truth in Lending Act (Regulation Z)"}
    ]
    with Session(engine) as session:
        task = session.get(Task, task_id)
        assert json.loads(task.linked_regulations_json) == [
            {"regulation_doc_id": "another-doc-id", "regulation_title": "Truth in Lending Act (Regulation Z)"}
        ]
        logs = session.query(AuditLog).all()
        assert any(log.action == AuditAction.OVERRIDE for log in logs)


def test_link_regulation_unknown_task_not_found(in_memory_engine):
    result = json.loads(link_regulation.invoke({
        "task_id": "does-not-exist",
        "regulation_doc_id": "another-doc-id",
        "regulation_title": "Truth in Lending Act (Regulation Z)",
    }))

    assert result == {"found": False}
