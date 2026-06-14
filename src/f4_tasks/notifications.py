"""
Day 42 (KM "Review" -- "email notification system live").

Implements the two draft templates from docs/Notification-UX-v1.md as
renderable notifications, plus an "outbox" -- a JSONL file that notifications
are appended to instead of being sent.

Standing project constraint: RegWatch AI / Claude does not send emails on the
user's behalf. This module is the generation + queueing half of a
notification system; wiring the outbox to a real transactional-email provider
is a separate, future, human decision (see docs/Notification-UX-v1.md).
"""
import json
from datetime import date
from pathlib import Path

from src.models import Task

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTBOX_PATH = PROJECT_ROOT / "logs" / "notifications.jsonl"


def render_new_task_notification(task: Task) -> dict:
    """"New task assigned" template from docs/Notification-UX-v1.md section 1."""
    body = f"""Hi {task.owner},

A new compliance task has been created from RegWatch AI's regulatory
monitoring.

Task: {task.title}
Due: {task.due_date}

{task.description}

Source: {task.source_policy_name} Section {task.source_section_id}
Regulation: {task.source_regulation_title}
Impact level: {task.source_impact_level}

View and manage this task in the Task Board.

— RegWatch AI"""
    return {
        "to": task.owner,
        "subject": f"[RegWatch AI] New compliance task: {task.title}",
        "body": body,
    }


def render_overdue_notification(task: Task) -> dict:
    """"Task overdue" template from docs/Notification-UX-v1.md section 2."""
    linked = task.linked_regulations_json or "(none)"
    body = f"""Hi {task.owner},

The following compliance task is now overdue.

Task: {task.title}
Was due: {task.due_date}
Current status: {task.status.value}

{task.description}

Regulation: {task.source_regulation_title}
Linked regulations: {linked}

Please update its status or due date in the Task Board, or use
set_due_date / assign_owner if it needs to be reassigned or rescheduled.

— RegWatch AI"""
    return {
        "to": task.owner,
        "subject": f"[RegWatch AI] Overdue: {task.title}",
        "body": body,
    }


def write_to_outbox(notification: dict, task_id: str, kind: str) -> None:
    """Append a rendered notification to logs/notifications.jsonl.

    Each line is a self-contained record -- not sent anywhere. A future
    integration would tail/consume this file and call a real email provider.
    """
    OUTBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "queued_at": date.today().isoformat(),
        "kind": kind,
        "task_id": task_id,
        **notification,
    }
    with open(OUTBOX_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
