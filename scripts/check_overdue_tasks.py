"""
Day 42 (KM "Review" -- "email notification system live").

Scans Task rows for ones where due_date < today and status != completed,
and queues a "task overdue" notification (docs/Notification-UX-v1.md
section 2) for each into the outbox (logs/notifications.jsonl) -- generation
+ queueing only, no actual send (see src/f4_tasks/notifications.py).

v1 limitation: re-running this script re-queues a notification for every
still-overdue task every time -- no "already notified" dedup. A future
version would track last-notified date per task before adding a real send
path, where duplicate emails would actually matter.

Run: python -m scripts.check_overdue_tasks
"""
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlmodel import select

from src.database import get_session
from src.f4_tasks.notifications import render_overdue_notification, write_to_outbox
from src.models import Task, TaskStatus


def find_overdue_tasks(today: date | None = None) -> list[Task]:
    today = today or date.today()
    with get_session() as session:
        tasks = session.exec(select(Task)).all()
    return [
        t for t in tasks
        if t.status != TaskStatus.COMPLETED and t.due_date < today.isoformat()
    ]


def main() -> None:
    overdue = find_overdue_tasks()
    for task in overdue:
        write_to_outbox(
            render_overdue_notification(task),
            task_id=task.id,
            kind="task_overdue",
        )
    print(f"Queued {len(overdue)} overdue-task notification(s).")
    for task in overdue:
        print(f"  - [{task.id}] {task.title} (due {task.due_date}, owner {task.owner})")


if __name__ == "__main__":
    main()
