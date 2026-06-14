"""
Tests for scripts/export_tasks.py (Day 42, KM "Review" -- management task
export) -- in-memory SQLite, same pattern as tests/test_override_rate.py.
"""

import csv
from contextlib import contextmanager

import pytest
from sqlmodel import Session, SQLModel, create_engine

from scripts import export_tasks
from src.models import Task

EXISTING_TASK = dict(
    source_policy_name="Fair-Lending-ECOA-Policy",
    source_section_id="1.1",
    source_regulation_doc_id="c5ba5ac6-a2ac-4522-a4b4-23c19d492dd3",
    source_regulation_title="Equal Credit Opportunity Act (Regulation B)",
    source_impact_level="high",
    title="Review Section 1.1 against Regulation B",
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

    monkeypatch.setattr(export_tasks, "get_session", mock_get_session)
    return engine


def test_export_tasks_writes_csv_with_header_and_rows(in_memory_engine, tmp_path):
    with Session(in_memory_engine) as session:
        session.add(Task(**EXISTING_TASK))
        session.add(Task(**{**EXISTING_TASK, "title": "Second task", "owner": "Mike"}))
        session.commit()

    output_path = tmp_path / "tasks.csv"
    count = export_tasks.export_tasks(output_path)

    assert count == 2
    with open(output_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    titles = {row["title"] for row in rows}
    assert titles == {"Review Section 1.1 against Regulation B", "Second task"}
    assert rows[0]["source_regulation_title"] == "Equal Credit Opportunity Act (Regulation B)"


def test_export_tasks_with_no_tasks_writes_header_only(in_memory_engine, tmp_path):
    output_path = tmp_path / "tasks.csv"
    count = export_tasks.export_tasks(output_path)

    assert count == 0
    with open(output_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows == []
