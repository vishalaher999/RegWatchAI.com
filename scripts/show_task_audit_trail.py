"""
CLI to print the audit trail for a Task (Day 34, KM #198 Audit trail).

Run: python -m scripts.show_task_audit_trail <task_id>
"""

import sys

from src.f4_tasks.audit import format_trail, get_task_audit_trail


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) != 2:
        print("Usage: python -m scripts.show_task_audit_trail <task_id>")
        raise SystemExit(1)

    task_id = sys.argv[1]
    entries = get_task_audit_trail(task_id)
    print(format_trail(task_id, entries))


if __name__ == "__main__":
    main()
