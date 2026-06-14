"""
Override rate report (Day 37, KM #241 LangSmith / observability).

Computes "% of tasks human-edited" from AuditLog:
  - total tasks created (AuditAction.TASK_CREATE rows with a task_id)
  - tasks that have >=1 AuditAction.OVERRIDE row editing a field
    (owner / due_date / linked_regulations_json -- src/f4_tasks/tools.py)
  - override rate = edited tasks / created tasks
  - rejected drafts: OVERRIDE rows from HITL rejection (hitl_agent.py),
    which have a "rejected_task" payload but no task_id/field

v1 does NOT report a "% summaries human-edited" number -- F2 summaries
have no edit/override mechanism in the current schema (AuditAction.OVERRIDE
is only ever written against Task rows). See docs/Override-Rate-Dashboard-v1.md.

Run: python -m scripts.override_rate_report
"""

import json
import sys
from collections import Counter

from sqlmodel import select

from src.database import get_session
from src.models import AuditAction, AuditLog


def compute_override_rate() -> dict:
    with get_session() as session:
        task_create_logs = session.exec(
            select(AuditLog).where(AuditLog.action == AuditAction.TASK_CREATE)
        ).all()
        override_logs = session.exec(
            select(AuditLog).where(AuditLog.action == AuditAction.OVERRIDE)
        ).all()

    created_task_ids = set()
    for log in task_create_logs:
        payload = json.loads(log.payload_json) if log.payload_json else {}
        task_id = payload.get("task_id")
        if task_id:
            created_task_ids.add(task_id)

    edited_task_ids = set()
    field_counts = Counter()
    rejected_drafts = 0

    for log in override_logs:
        payload = json.loads(log.payload_json) if log.payload_json else {}
        task_id = payload.get("task_id")
        field = payload.get("field")
        if task_id and field:
            edited_task_ids.add(task_id)
            field_counts[field] += 1
        elif "rejected_task" in payload:
            rejected_drafts += 1

    total_tasks = len(created_task_ids)
    edited_tasks = len(edited_task_ids & created_task_ids)
    rate = (edited_tasks / total_tasks * 100) if total_tasks else 0.0

    return {
        "total_tasks_created": total_tasks,
        "tasks_edited": edited_tasks,
        "override_rate_pct": round(rate, 1),
        "edits_by_field": dict(field_counts),
        "rejected_drafts": rejected_drafts,
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    stats = compute_override_rate()

    print("Override Rate Report")
    print("=" * 40)
    print(f"Tasks created:          {stats['total_tasks_created']}")
    print(f"Tasks human-edited:     {stats['tasks_edited']}")
    print(f"Override rate:          {stats['override_rate_pct']}%")
    print(f"Rejected drafts (HITL): {stats['rejected_drafts']}")
    print()
    print("Edits by field:")
    if stats["edits_by_field"]:
        for field, count in stats["edits_by_field"].items():
            print(f"  {field}: {count}")
    else:
        print("  (none)")
    print()
    print("Note: '% summaries human-edited' is not tracked in v1 -- F2")
    print("summaries have no edit/override mechanism. See")
    print("docs/Override-Rate-Dashboard-v1.md for the planned v2 approach.")


if __name__ == "__main__":
    main()
