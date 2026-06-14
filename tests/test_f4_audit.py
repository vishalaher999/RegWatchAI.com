"""
Tests for src/f4_tasks/audit.py — in-memory SQLite, same pattern as
tests/test_f4_hitl.py and tests/test_f4_tools.py.
"""

import json
from contextlib import contextmanager

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.f4_tasks import audit as audit_module
from src.models import AuditAction, AuditLog, Task

REGULATION_DOC_ID = "c5ba5ac6-a2ac-4522-a4b4-23c19d492dd3"

EXISTING_TASK = dict(
    source_policy_name="Fair-Lending-ECOA-Policy",
    source_section_id="1.1",
    source_regulation_doc_id=REGULATION_DOC_ID,
    source_regulation_title="Equal Credit Opportunity Act (Regulation B)",
    source_impact_level="high",
    title="Fair-Lending-ECOA-Policy Section 1.1 - Equal Credit Opportunity Act (Regulation B)",
    description="Some evidence text. Review needed.",
    owner="Sarah",
    due_date="2026-07-21",
)


@pytest.fixture
def in_memory_engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    @contextmanager
    def mock_get_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(audit_module, "get_session", mock_get_session)
    return engine


def test_unknown_task_returns_empty_list(in_memory_engine):
    assert audit_module.get_task_audit_trail("does-not-exist") == []


def test_trail_includes_summarise_and_task_create(in_memory_engine):
    engine = in_memory_engine

    with Session(engine) as session:
        task = Task(**EXISTING_TASK)
        session.add(task)
        session.commit()
        task_id = task.id

        session.add(AuditLog(
            action=AuditAction.SUMMARISE,
            actor="system:f2",
            doc_id=REGULATION_DOC_ID,
            payload_json=json.dumps({
                "model": "claude-sonnet-4-20250514",
                "prompt_version": "v3",
                "confidence_score": 0.91,
                "review_flag": False,
            }),
        ))
        session.add(AuditLog(
            action=AuditAction.TASK_CREATE,
            actor="system:f4",
            doc_id=REGULATION_DOC_ID,
            payload_json=json.dumps({
                "model": "claude-sonnet-4-20250514",
                "prompt_version": "v2",
                "task_id": task_id,
                "approved_by": "human:sarah",
                "edits_applied": {},
            }),
        ))
        session.commit()

    trail = audit_module.get_task_audit_trail(task_id)

    assert [e["action"] for e in trail] == ["summarise", "task_create"]
    assert "Regulation summarised by F2" in trail[0]["summary"]
    assert "Task created by F4" in trail[1]["summary"]
    assert "approved_by=human:sarah" in trail[1]["summary"]


def test_trail_shows_langsmith_trace_id_when_present(in_memory_engine):
    """Day 37 (KM #241 LangSmith): SUMMARISE/TASK_CREATE rows with a
    langsmith_trace_id show 'trace=<id>' in the summary; rows without one
    (tracing not configured) show nothing extra."""
    engine = in_memory_engine

    with Session(engine) as session:
        task = Task(**EXISTING_TASK)
        session.add(task)
        session.commit()
        task_id = task.id

        session.add(AuditLog(
            action=AuditAction.SUMMARISE,
            actor="system:f2",
            doc_id=REGULATION_DOC_ID,
            langsmith_trace_id="trace-abc-123",
            payload_json=json.dumps({
                "model": "claude-sonnet-4-20250514",
                "prompt_version": "v3",
                "confidence_score": 0.91,
                "review_flag": False,
            }),
        ))
        session.add(AuditLog(
            action=AuditAction.TASK_CREATE,
            actor="system:f4",
            doc_id=REGULATION_DOC_ID,
            payload_json=json.dumps({
                "model": "claude-sonnet-4-20250514",
                "prompt_version": "v2",
                "task_id": task_id,
                "approved_by": "human:sarah",
                "edits_applied": {},
            }),
        ))
        session.commit()

    trail = audit_module.get_task_audit_trail(task_id)

    assert "trace=trace-abc-123" in trail[0]["summary"]
    assert "trace=" not in trail[1]["summary"]


def test_trail_includes_ingest_and_map_entries(in_memory_engine):
    engine = in_memory_engine

    with Session(engine) as session:
        task = Task(**EXISTING_TASK)
        session.add(task)
        session.commit()
        task_id = task.id

        session.add(AuditLog(
            action=AuditAction.INGEST,
            actor="system",
            doc_id=REGULATION_DOC_ID,
            payload_json=json.dumps({
                "agency": "fed",
                "title": "Equal Credit Opportunity Act (Regulation B)",
                "doc_type": "final_rule",
                "url": "https://example.com/reg-b",
            }),
        ))
        session.add(AuditLog(
            action=AuditAction.MAP,
            actor="system",
            doc_id=REGULATION_DOC_ID,
            payload_json=json.dumps({
                "policy_name": "Fair-Lending-ECOA-Policy",
                "section_id": "1.1",
                "regulation_title": "Equal Credit Opportunity Act (Regulation B)",
                "dense_score": 0.60,
                "named_regulation_match": True,
                "impact_level": "high",
                "high_threshold": 0.55,
                "medium_threshold": 0.45,
                "low_threshold": 0.35,
            }),
        ))
        # MAP entry for a DIFFERENT policy section against the same
        # regulation -- must not appear in this task's trail.
        session.add(AuditLog(
            action=AuditAction.MAP,
            actor="system",
            doc_id=REGULATION_DOC_ID,
            payload_json=json.dumps({
                "policy_name": "Fair-Lending-ECOA-Policy",
                "section_id": "1.2",
                "regulation_title": "Equal Credit Opportunity Act (Regulation B)",
                "dense_score": 0.40,
                "named_regulation_match": False,
                "impact_level": "not_applicable",
                "high_threshold": 0.55,
                "medium_threshold": 0.45,
                "low_threshold": 0.35,
            }),
        ))
        session.commit()

    trail = audit_module.get_task_audit_trail(task_id)

    assert [e["action"] for e in trail] == ["ingest", "map"]
    assert "Document ingested by F1" in trail[0]["summary"]
    assert "Policy section mapped by F3" in trail[1]["summary"]
    assert "impact_level=high" in trail[1]["summary"]


def test_trail_includes_overrides_for_this_task_only(in_memory_engine):
    engine = in_memory_engine

    with Session(engine) as session:
        task = Task(**EXISTING_TASK)
        other_task = Task(**EXISTING_TASK)
        session.add(task)
        session.add(other_task)
        session.commit()
        task_id = task.id
        other_task_id = other_task.id

        session.add(AuditLog(
            action=AuditAction.OVERRIDE,
            actor="human:sarah",
            payload_json=json.dumps({
                "task_id": task_id,
                "field": "owner",
                "before": "Sarah",
                "after": "Mike",
            }),
        ))
        session.add(AuditLog(
            action=AuditAction.OVERRIDE,
            actor="human:sarah",
            payload_json=json.dumps({
                "task_id": other_task_id,
                "field": "due_date",
                "before": "2026-07-21",
                "after": "2026-08-01",
            }),
        ))
        session.commit()

    trail = audit_module.get_task_audit_trail(task_id)

    assert len(trail) == 1
    assert trail[0]["action"] == "override"
    assert "owner changed from 'Sarah' to 'Mike'" in trail[0]["summary"]


def test_trail_sorted_chronologically(in_memory_engine):
    engine = in_memory_engine

    with Session(engine) as session:
        task = Task(**EXISTING_TASK)
        session.add(task)
        session.commit()
        task_id = task.id

        # Insert OVERRIDE first, then TASK_CREATE -- trail must still
        # order by timestamp, not insertion order.
        session.add(AuditLog(
            action=AuditAction.OVERRIDE,
            actor="human:sarah",
            payload_json=json.dumps({
                "task_id": task_id,
                "field": "due_date",
                "before": "2026-07-21",
                "after": "2026-08-01",
            }),
        ))
        session.commit()

        session.add(AuditLog(
            action=AuditAction.TASK_CREATE,
            actor="system:f4",
            doc_id=REGULATION_DOC_ID,
            payload_json=json.dumps({
                "model": "claude-sonnet-4-20250514",
                "prompt_version": "v2",
                "task_id": task_id,
                "approved_by": "human:sarah",
            }),
        ))
        session.commit()

    trail = audit_module.get_task_audit_trail(task_id)

    timestamps = [e["timestamp"] for e in trail]
    assert timestamps == sorted(timestamps)


def test_format_trail_empty(in_memory_engine):
    assert audit_module.format_trail("missing-id", []) == "No audit trail found for task missing-id."


def test_format_trail_non_empty(in_memory_engine):
    engine = in_memory_engine

    with Session(engine) as session:
        task = Task(**EXISTING_TASK)
        session.add(task)
        session.commit()
        task_id = task.id

        session.add(AuditLog(
            action=AuditAction.TASK_CREATE,
            actor="system:f4",
            doc_id=REGULATION_DOC_ID,
            payload_json=json.dumps({
                "model": "claude-sonnet-4-20250514",
                "prompt_version": "v2",
                "task_id": task_id,
                "approved_by": "human:sarah",
            }),
        ))
        session.commit()

    trail = audit_module.get_task_audit_trail(task_id)
    text = audit_module.format_trail(task_id, trail)

    assert f"Audit trail for task {task_id}" in text
    assert "[task_create]" in text
