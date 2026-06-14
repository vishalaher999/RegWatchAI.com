"""Tests for src/f4_tasks/notifications.py (Day 42)."""

import json

from src.f4_tasks.notifications import (
    render_new_task_notification,
    render_overdue_notification,
    write_to_outbox,
)
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
    due_date="2026-07-21",
)


def test_render_new_task_notification_includes_key_fields():
    task = Task(**EXISTING_TASK)

    notification = render_new_task_notification(task)

    assert notification["to"] == "Sarah"
    assert "New compliance task: Review Section 1.1 against Regulation B" in notification["subject"]
    assert task.title in notification["body"]
    assert task.due_date in notification["body"]
    assert task.source_policy_name in notification["body"]
    assert task.source_regulation_title in notification["body"]
    assert task.source_impact_level in notification["body"]


def test_render_overdue_notification_includes_status_and_linked_regulations():
    task = Task(**EXISTING_TASK, status=TaskStatus.IN_PROGRESS,
                 linked_regulations_json='[{"regulation_doc_id": "abc", "regulation_title": "Some Other Rule"}]')

    notification = render_overdue_notification(task)

    assert notification["to"] == "Sarah"
    assert "Overdue: Review Section 1.1 against Regulation B" in notification["subject"]
    assert "in_progress" in notification["body"]
    assert "Some Other Rule" in notification["body"]


def test_render_overdue_notification_handles_no_linked_regulations():
    task = Task(**EXISTING_TASK)

    notification = render_overdue_notification(task)

    assert "(none)" in notification["body"]


def test_write_to_outbox_appends_jsonl(tmp_path, monkeypatch):
    import src.f4_tasks.notifications as notifications_module

    outbox_path = tmp_path / "notifications.jsonl"
    monkeypatch.setattr(notifications_module, "OUTBOX_PATH", outbox_path)

    task = Task(**EXISTING_TASK)
    notification = render_new_task_notification(task)

    write_to_outbox(notification, task_id=task.id, kind="new_task_assigned")
    write_to_outbox(render_overdue_notification(task), task_id=task.id, kind="task_overdue")

    lines = outbox_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    record_0 = json.loads(lines[0])
    assert record_0["kind"] == "new_task_assigned"
    assert record_0["task_id"] == task.id
    assert record_0["to"] == "Sarah"

    record_1 = json.loads(lines[1])
    assert record_1["kind"] == "task_overdue"
