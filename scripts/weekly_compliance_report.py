"""
Weekly compliance report (Day 38, KM #263/#269 -- "compliance report
template / weekly PDF export").

Queries AuditLog for the last 7 days and renders a Markdown summary:
  - documents ingested (AuditAction.INGEST)
  - summaries produced, broken down by routing decision (AuditAction.SUMMARISE,
    payload["routing_decision"] from src/f2_summarise/router.py)
  - guardrail warnings raised (Day 38, payload["guardrail_warnings"])
  - HIGH-impact findings (AuditAction.MAP, payload["impact_level"] == "high")
  - tasks created (AuditAction.TASK_CREATE)
  - override rate (reuses compute_override_rate from Day 37)

v1 produces Markdown only. PDF rendering (e.g. via pandoc) is a v2
follow-up -- see docs/Compliance-Report-Template-v1.md.

Run: python -m scripts.weekly_compliance_report
"""

import json
import sys
from collections import Counter
from datetime import datetime, timedelta

from sqlmodel import select

from src.database import get_session
from src.models import AuditAction, AuditLog
from scripts.override_rate_report import compute_override_rate


def build_report(days: int = 7, now: datetime | None = None) -> dict:
    now = now or datetime.utcnow()
    since = now - timedelta(days=days)

    with get_session() as session:
        logs = session.exec(
            select(AuditLog).where(AuditLog.timestamp >= since)
        ).all()

    documents_ingested = 0
    routing_counts = Counter()
    guardrail_warning_count = 0
    high_findings = 0
    tasks_created = 0

    for log in logs:
        payload = json.loads(log.payload_json) if log.payload_json else {}

        if log.action == AuditAction.INGEST:
            documents_ingested += 1
        elif log.action == AuditAction.SUMMARISE:
            decision = payload.get("routing_decision", "unknown")
            routing_counts[decision] += 1
            if payload.get("guardrail_warnings"):
                guardrail_warning_count += 1
        elif log.action == AuditAction.MAP:
            if payload.get("impact_level") == "high":
                high_findings += 1
        elif log.action == AuditAction.TASK_CREATE:
            tasks_created += 1

    override_stats = compute_override_rate()

    return {
        "period_start": since.isoformat(timespec="seconds"),
        "period_end": now.isoformat(timespec="seconds"),
        "documents_ingested": documents_ingested,
        "summaries_by_routing": dict(routing_counts),
        "guardrail_warnings": guardrail_warning_count,
        "high_findings": high_findings,
        "tasks_created": tasks_created,
        "override_rate_pct": override_stats["override_rate_pct"],
        "tasks_human_edited": override_stats["tasks_edited"],
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Weekly Compliance Report",
        "",
        f"**Period:** {report['period_start']} to {report['period_end']} (UTC)",
        "",
        "## Feed Activity",
        "",
        f"- Documents ingested: {report['documents_ingested']}",
        "",
        "## Summaries (F2)",
        "",
    ]

    if report["summaries_by_routing"]:
        for decision, count in report["summaries_by_routing"].items():
            lines.append(f"- {decision}: {count}")
    else:
        lines.append("- (none)")

    lines += [
        f"- Guardrail warnings raised: {report['guardrail_warnings']}",
        "",
        "## Impact Findings (F3)",
        "",
        f"- HIGH-impact findings: {report['high_findings']}",
        "",
        "## Tasks (F4)",
        "",
        f"- Tasks created: {report['tasks_created']}",
        f"- Tasks human-edited: {report['tasks_human_edited']}",
        f"- Override rate: {report['override_rate_pct']}%",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    report = build_report()
    print(render_markdown(report))


if __name__ == "__main__":
    main()
