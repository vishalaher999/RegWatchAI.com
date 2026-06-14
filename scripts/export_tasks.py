"""
Day 42 (KM "Review" -- "management task export").

Exports all F4 Task rows to a CSV file for Mike/Sarah to open in Excel --
a flat snapshot of the task board, independent of the API/dashboard.

v1 limitation: CSV only. A PDF export would need `reportlab`, which is not
currently installed (commented out in requirements.txt) -- flagged as a v2
add rather than installed speculatively.

Run: python -m scripts.export_tasks [output_path]
"""
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlmodel import select

from src.database import get_session
from src.models import Task

DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "exports" / "tasks.csv"

FIELDNAMES = [
    "id", "created_at", "status", "title", "description", "owner", "due_date",
    "source_policy_name", "source_section_id", "source_regulation_doc_id",
    "source_regulation_title", "source_impact_level", "linked_regulations_json",
]


def export_tasks(output_path: Path = DEFAULT_OUTPUT_PATH) -> int:
    with get_session() as session:
        tasks = session.exec(select(Task)).all()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for task in tasks:
            writer.writerow({
                "id": task.id,
                "created_at": task.created_at.isoformat(),
                "status": task.status.value,
                "title": task.title,
                "description": task.description,
                "owner": task.owner,
                "due_date": task.due_date,
                "source_policy_name": task.source_policy_name,
                "source_section_id": task.source_section_id,
                "source_regulation_doc_id": task.source_regulation_doc_id,
                "source_regulation_title": task.source_regulation_title,
                "source_impact_level": task.source_impact_level,
                "linked_regulations_json": task.linked_regulations_json or "",
            })
    return len(tasks)


def main() -> None:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT_PATH
    count = export_tasks(output_path)
    print(f"Exported {count} task(s) to {output_path}")


if __name__ == "__main__":
    main()
