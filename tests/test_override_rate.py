"""
Tests for scripts/override_rate_report.py (Day 37, KM #241 LangSmith /
Override rate dashboard) -- in-memory SQLite, same pattern as
tests/test_f4_audit.py.
"""

import json
from contextlib import contextmanager

import pytest
from sqlmodel import Session, SQLModel, create_engine

from scripts import override_rate_report
from src.models import AuditAction, AuditLog


@pytest.fixture
def in_memory_engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    @contextmanager
    def mock_get_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(override_rate_report, "get_session", mock_get_session)
    return engine


def test_no_data_returns_zero_rate(in_memory_engine):
    stats = override_rate_report.compute_override_rate()

    assert stats["total_tasks_created"] == 0
    assert stats["tasks_edited"] == 0
    assert stats["override_rate_pct"] == 0.0
    assert stats["edits_by_field"] == {}
    assert stats["rejected_drafts"] == 0


def test_computes_rate_and_field_breakdown(in_memory_engine):
    engine = in_memory_engine

    with Session(engine) as session:
        # Two tasks created.
        session.add(AuditLog(
            action=AuditAction.TASK_CREATE,
            actor="system:f4",
            payload_json=json.dumps({"task_id": "task-1", "approved_by": "human:sarah"}),
        ))
        session.add(AuditLog(
            action=AuditAction.TASK_CREATE,
            actor="system:f4",
            payload_json=json.dumps({"task_id": "task-2", "approved_by": "human:sarah"}),
        ))
        # task-1 is edited twice (owner, then due_date) -- still counts once.
        session.add(AuditLog(
            action=AuditAction.OVERRIDE,
            actor="human:sarah",
            payload_json=json.dumps({"task_id": "task-1", "field": "owner", "before": "Sarah", "after": "Mike"}),
        ))
        session.add(AuditLog(
            action=AuditAction.OVERRIDE,
            actor="human:sarah",
            payload_json=json.dumps({"task_id": "task-1", "field": "due_date", "before": "2026-07-21", "after": "2026-08-01"}),
        ))
        # A rejected HITL draft -- no task_id/field, has rejected_task.
        session.add(AuditLog(
            action=AuditAction.OVERRIDE,
            actor="human:sarah",
            payload_json=json.dumps({"rejected_task": {"title": "Some draft"}}),
        ))
        session.commit()

    stats = override_rate_report.compute_override_rate()

    assert stats["total_tasks_created"] == 2
    assert stats["tasks_edited"] == 1
    assert stats["override_rate_pct"] == 50.0
    assert stats["edits_by_field"] == {"owner": 1, "due_date": 1}
    assert stats["rejected_drafts"] == 1
