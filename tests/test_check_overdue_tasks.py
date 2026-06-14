"""
Tests for scripts/check_overdue_tasks.py (Day 42, KM "Review" -- email
notification system) -- in-memory SQLite, same pattern as
tests/test_override_rate.py.
"""

import json
from contextlib import contextmanager
from datetime import date

import pytest
from sqlmodel import Session, SQLModel, create_engine

from scripts import check_overdue_tasks
from src.models import Task, TaskStatus

EXISTING_TASK = dict(
    source_policy_name="Fair-Lending-ECOA-Policy",
    source_section_id="1.1",
    source_regulation_doc_id="c5ba5ac6-a2ac-4522-a4b4-23c19d492dd3",
    source_regulation_title="Equal Credit Opportunity Act (Regulation B)",
    source_impact_level="high",
    title="Review Section 1.1 against Regulation B",
    description="Some evidence text. Review needed.",
    owner="Sarah",
)


@pytest.fixture
def in_memory_engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    @contextmanager
    def mock_get_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(check_overdue_tasks, "get_session", mock_get_session)
    return engine


def test_find_overdue_tasks_returns_only_past_due_open_tasks(in_memory_engine):
    with Session(in_memory_engine) as session:
        session.add(Task(**EXISTING_TASK, due_date="2020-01-01", status=TaskStatus.OPEN))
        session.add(Task(**{**EXISTING_TASK, "title": "Future task"}, due_date="2099-01-01", status=TaskStatus.OPEN))
        session.add(Task(**{**EXISTING_TASK, "title": "Completed but overdue"}, due_date="2020-01-01", status=TaskStatus.COMPLETED))
        session.commit()

    overdue = check_overdue_tasks.find_overdue_tasks(today=date(2026, 6, 14))

    titles = {t.title for t in overdue}
    assert titles == {"Review Section 1.1 against Regulation B"}


def test_main_queues_notification_for_each_overdue_task(in_memory_engine, tmp_path, monkeypatch):
    import src.f4_tasks.notifications as notifications_module

    outbox_path = tmp_path / "notifications.jsonl"
    monkeypatch.setattr(notifications_module, "OUTBOX_PATH", outbox_path)

    with Session(in_memory_engine) as session:
        session.add(Task(**EXISTING_TASK, due_date="2020-01-01", status=TaskStatus.OPEN))
        session.commit()

    monkeypatch.setattr(check_overdue_tasks, "find_overdue_tasks", lambda today=None: session_tasks(in_memory_engine))

    check_overdue_tasks.main()

    lines = outbox_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["kind"] == "task_overdue"
    assert record["to"] == "Sarah"


def session_tasks(engine):
    from sqlmodel import select
    with Session(engine) as session:
        return session.exec(select(Task)).all()
