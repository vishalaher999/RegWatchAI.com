"""
Tests for src/f4_tasks/hitl_agent.py — no LLM calls (fake draft_fn injected).

Uses an in-memory SQLite DB, same pattern as tests/test_f1_dedup.py.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.f4_tasks import hitl_agent as hitl_module
from src.models import AuditAction, AuditLog, Task

FAKE_FINDING = {
    "policy_name": "Fair-Lending-ECOA-Policy",
    "section_id": "1.1",
    "section_title": "Purpose",
    "parent_section": "SECTION 1: PURPOSE AND SCOPE",
    "regulation_doc_id": "c5ba5ac6-a2ac-4522-a4b4-23c19d492dd3",
    "regulation_title": "Equal Credit Opportunity Act (Regulation B)",
    "impact_level": "high",
    "matched_chunk_text": "some evidence text",
}

FAKE_DRAFTED_TASK = {
    "source_policy_name": "Fair-Lending-ECOA-Policy",
    "source_section_id": "1.1",
    "source_regulation_doc_id": "c5ba5ac6-a2ac-4522-a4b4-23c19d492dd3",
    "source_regulation_title": "Equal Credit Opportunity Act (Regulation B)",
    "source_impact_level": "high",
    "title": "Fair-Lending-ECOA-Policy Section 1.1 - Equal Credit Opportunity Act (Regulation B)",
    "description": "Some evidence text. Review needed.",
    "owner": "Sarah",
    "due_date": "2026-07-21",
}


def fake_draft_fn(finding, today):
    return dict(FAKE_DRAFTED_TASK)


@pytest.fixture
def in_memory_engine(monkeypatch):
    """Create a fresh in-memory SQLite DB for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    from contextlib import contextmanager

    @contextmanager
    def mock_get_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(hitl_module, "get_session", mock_get_session)
    monkeypatch.setattr(hitl_module, "create_db_and_tables", lambda: None)
    monkeypatch.setattr(hitl_module, "load_high_findings", lambda: [FAKE_FINDING])
    return engine


def test_run_with_approval_pauses_without_db_writes(in_memory_engine):
    pending, graph = hitl_module.run_with_approval(limit=1, graph=hitl_module.build_graph(fake_draft_fn))

    assert len(pending) == 1
    assert pending[0]["drafted_task"] == FAKE_DRAFTED_TASK
    assert pending[0]["finding"] == FAKE_FINDING

    with Session(in_memory_engine) as session:
        assert session.query(Task).count() == 0
        assert session.query(AuditLog).count() == 0


def test_resolve_approval_creates_task_and_audit_log(in_memory_engine):
    graph = hitl_module.build_graph(fake_draft_fn)
    pending, graph = hitl_module.run_with_approval(limit=1, graph=graph)

    result = hitl_module.resolve_approval(graph, pending[0]["thread_id"], approved=True)

    assert result["status"] == "created"

    with Session(in_memory_engine) as session:
        tasks = session.query(Task).all()
        assert len(tasks) == 1
        assert tasks[0].id == result["task_id"]
        assert tasks[0].title == FAKE_DRAFTED_TASK["title"]
        assert tasks[0].status.value == "open"

        logs = session.query(AuditLog).all()
        assert len(logs) == 1
        assert logs[0].action == AuditAction.TASK_CREATE
        assert logs[0].actor == "system:f4"


def test_resolve_approval_reject_creates_no_task_but_logs_override(in_memory_engine):
    graph = hitl_module.build_graph(fake_draft_fn)
    pending, graph = hitl_module.run_with_approval(limit=1, graph=graph)

    result = hitl_module.resolve_approval(graph, pending[0]["thread_id"], approved=False)

    assert result["status"] == "rejected"

    with Session(in_memory_engine) as session:
        assert session.query(Task).count() == 0

        logs = session.query(AuditLog).all()
        assert len(logs) == 1
        assert logs[0].action == AuditAction.OVERRIDE
        assert logs[0].actor == "human:sarah"


def test_resolve_approval_applies_edits_on_approve(in_memory_engine):
    graph = hitl_module.build_graph(fake_draft_fn)
    pending, graph = hitl_module.run_with_approval(limit=1, graph=graph)

    result = hitl_module.resolve_approval(
        graph, pending[0]["thread_id"], approved=True, edits={"due_date": "2026-08-01"}
    )

    assert result["status"] == "created"

    with Session(in_memory_engine) as session:
        task = session.query(Task).one()
        assert task.due_date == "2026-08-01"
