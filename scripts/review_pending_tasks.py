"""
CLI for Sarah to review F4's drafted tasks (Day 32, HITL approval gate).

Drafts tasks for the first N HIGH findings (default 5), pauses each one at
the HITL graph's await_approval node (src/f4_tasks/hitl_agent.py), then
walks through them one at a time: shows the draft, asks
approve / edit due_date / reject, and resumes the graph with that decision.

Run: python -m scripts.review_pending_tasks [N]
"""

import sys

from src.f4_tasks.hitl_agent import resolve_approval, run_with_approval


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    pending, graph = run_with_approval(limit=limit)
    print(f"\n{len(pending)} drafted task(s) awaiting review.\n")

    for item in pending:
        task = item["drafted_task"]
        print("=" * 65)
        print(f"Title:       {task['title']}")
        print(f"Owner:       {task['owner']}")
        print(f"Due date:    {task['due_date']}")
        print(f"Description: {task['description']}")
        print("=" * 65)

        choice = input("Approve (y) / Edit due date (e) / Reject (n)? ").strip().lower()

        if choice == "e":
            new_due_date = input(f"New due date [{task['due_date']}]: ").strip()
            edits = {"due_date": new_due_date} if new_due_date else None
            result = resolve_approval(graph, item["thread_id"], approved=True, edits=edits)
        elif choice == "y":
            result = resolve_approval(graph, item["thread_id"], approved=True)
        else:
            result = resolve_approval(graph, item["thread_id"], approved=False)

        print(f"-> {result}\n")


if __name__ == "__main__":
    main()
