"""
F4 MVP demo (Day 35, Week 5 review/exit).

Demonstrates the full chain: an F3 HIGH-impact finding (regulation already
ingested by F1, summarised by F2, mapped by F3) -> F4 drafts a Task via the
ReAct agent + create_task tool (Day 33) -> the HITL gate (Day 32) approves
it -> Day 34's audit trail shows the complete history for the resulting
Task.

This script auto-approves every draft (`resolve_approval(..., approved=True)`)
-- it's a demo of the chain working end-to-end, not a substitute for
Sarah's real review via scripts/review_pending_tasks.py.

Run: python -m scripts.f4_mvp_demo [N]   (N defaults to 1; real Anthropic API calls)
"""

import sys

from src.f4_tasks.audit import format_trail, get_task_audit_trail
from src.f4_tasks.hitl_agent import resolve_approval, run_with_approval


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    pending, graph = run_with_approval(limit=limit)
    print(f"\n{len(pending)} F3 HIGH finding(s) -> F4 draft(s).\n")

    for item in pending:
        finding = item["finding"]
        task = item["drafted_task"]

        print("=" * 70)
        print("F3 finding (policy <-> regulation, impact=HIGH):")
        print(f"  Policy:     {finding['policy_name']} Section {finding['section_id']}")
        print(f"  Regulation: {finding['regulation_title']}")
        print()
        print("F4 draft (create_task):")
        print(f"  Title:       {task['title']}")
        print(f"  Owner:       {task['owner']}")
        print(f"  Due date:    {task['due_date']}")
        print(f"  Description: {task['description']}")
        print()

        result = resolve_approval(graph, item["thread_id"], approved=True)
        print(f"HITL decision: approved -> {result}")

        if result["status"] == "created":
            trail = get_task_audit_trail(result["task_id"])
            print()
            print(format_trail(result["task_id"], trail))

        print("=" * 70)
        print()


if __name__ == "__main__":
    main()
