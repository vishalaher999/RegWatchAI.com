"""
Task audit trail (Day 34, KM #198 Audit trail).

Day 33 made every edit to a Task individually auditable (AuditLog(OVERRIDE)
per assign_owner/set_due_date/link_regulation call, plus the original
AuditLog(TASK_CREATE)). Nothing assembles those rows into a single
chronological story for a given Task -- get_task_audit_trail() does that.

Day 36 (KM #242 Compliance logging) closed the two gaps documented here on
Day 34 (docs/F4-Audit-Report-v1.md Section 7, gaps #1-2):
  - F1 now writes one AuditLog(INGEST) per document (src/f1_ingest/ingest.py
    log_document_ingest), doc_id-scoped, so an ingest event can be traced to
    a specific RegulatoryDocument.
  - F3 now writes one AuditLog(MAP) per (policy section, regulation) match
    (src/f3_impact/classifier.py log_map_decisions), doc_id-scoped to the
    regulation with policy_name/section_id in the payload.

A Task's trail now covers all five AuditActions: INGEST + SUMMARISE + MAP
(doc-scoped to source_regulation_doc_id, MAP additionally filtered to this
task's policy_name/section_id) and TASK_CREATE / OVERRIDE (task_id-scoped
via payload_json).
"""

import json
from datetime import datetime

from sqlmodel import select

from src.database import get_session
from src.models import AuditAction, AuditLog, Task


def _trace_suffix(log: AuditLog) -> str:
    """
    Append ' | trace=<id>' when this AuditLog row has a LangSmith run ID
    (Day 37, KM #241 LangSmith). Empty string if tracing wasn't configured
    for this run -- the "decision trace view" is additive, not required.
    """
    if log.langsmith_trace_id:
        return f" | trace={log.langsmith_trace_id}"
    return ""


def _summarize_entry(log: AuditLog, payload: dict) -> str:
    """Human-readable one-line summary of an AuditLog row for the trail."""
    if log.action == AuditAction.SUMMARISE:
        if "error" in payload:
            return f"F2 summarisation FAILED (model={payload.get('model_tried')}): {payload['error']}"
        return (
            f"Regulation summarised by F2 (model={payload.get('model')}, "
            f"prompt_version={payload.get('prompt_version')}, "
            f"confidence={payload.get('confidence_score')}, "
            f"review_flag={payload.get('review_flag')})"
            + _trace_suffix(log)
        )

    if log.action == AuditAction.TASK_CREATE:
        return (
            f"Task created by F4 (model={payload.get('model')}, "
            f"prompt_version={payload.get('prompt_version')}, "
            f"approved_by={payload.get('approved_by', 'system:f4')}, "
            f"edits_applied={payload.get('edits_applied') or {}})"
            + _trace_suffix(log)
        )

    if log.action == AuditAction.INGEST:
        return (
            f"Document ingested by F1 (agency={payload.get('agency')}, "
            f"doc_type={payload.get('doc_type')}, title={payload.get('title')!r})"
        )

    if log.action == AuditAction.MAP:
        return (
            f"Policy section mapped by F3 (policy={payload.get('policy_name')} "
            f"§{payload.get('section_id')}, dense_score={payload.get('dense_score')}, "
            f"named_regulation_match={payload.get('named_regulation_match')}, "
            f"impact_level={payload.get('impact_level')})"
        )

    if log.action == AuditAction.OVERRIDE:
        if "field" in payload:
            if payload["field"] == "linked_regulations_json":
                return f"Override by {log.actor}: linked regulation {payload.get('added')}"
            return (
                f"Override by {log.actor}: {payload['field']} changed "
                f"from {payload.get('before')!r} to {payload.get('after')!r}"
            )
        return f"Override by {log.actor}: {payload}"

    return f"{log.action.value} by {log.actor}"


def get_task_audit_trail(task_id: str) -> list[dict]:
    """
    Return the chronological audit trail for a Task as a list of
    {timestamp, action, actor, summary} dicts, oldest first.

    Combines:
      - F1 INGEST + F2 SUMMARISE entries for the Task's
        source_regulation_doc_id (doc_id-linked).
      - F3 MAP entries for source_regulation_doc_id, further filtered to
        this task's source_policy_name/source_section_id (a regulation can
        be mapped against many policy sections, each with its own MAP entry).
      - F4 TASK_CREATE / OVERRIDE entries whose payload_json["task_id"]
        matches this task (Day 32 approval, Day 33 management-tool edits).

    Returns [] if no Task with this id exists.
    """
    with get_session() as session:
        task = session.get(Task, task_id)
        if task is None:
            return []

        entries = []

        regulation_logs = session.exec(
            select(AuditLog).where(
                AuditLog.doc_id == task.source_regulation_doc_id,
                AuditLog.action.in_([AuditAction.INGEST, AuditAction.SUMMARISE]),
            )
        ).all()
        for log in regulation_logs:
            payload = json.loads(log.payload_json) if log.payload_json else {}
            entries.append({
                "timestamp": log.timestamp,
                "action": log.action.value,
                "actor": log.actor,
                "summary": _summarize_entry(log, payload),
            })

        map_logs = session.exec(
            select(AuditLog).where(
                AuditLog.doc_id == task.source_regulation_doc_id,
                AuditLog.action == AuditAction.MAP,
            )
        ).all()
        for log in map_logs:
            payload = json.loads(log.payload_json) if log.payload_json else {}
            if (
                payload.get("policy_name") != task.source_policy_name
                or payload.get("section_id") != task.source_section_id
            ):
                continue
            entries.append({
                "timestamp": log.timestamp,
                "action": log.action.value,
                "actor": log.actor,
                "summary": _summarize_entry(log, payload),
            })

        task_logs = session.exec(
            select(AuditLog).where(
                AuditLog.action.in_([AuditAction.TASK_CREATE, AuditAction.OVERRIDE])
            )
        ).all()
        for log in task_logs:
            payload = json.loads(log.payload_json) if log.payload_json else {}
            if payload.get("task_id") != task_id:
                continue
            entries.append({
                "timestamp": log.timestamp,
                "action": log.action.value,
                "actor": log.actor,
                "summary": _summarize_entry(log, payload),
            })

    entries.sort(key=lambda e: e["timestamp"])
    return entries


def format_trail(task_id: str, entries: list[dict]) -> str:
    """Render a trail as plain text for the CLI / future report export."""
    if not entries:
        return f"No audit trail found for task {task_id}."

    lines = [f"Audit trail for task {task_id}:", ""]
    for e in entries:
        ts: datetime = e["timestamp"]
        lines.append(f"  {ts.isoformat()}  [{e['action']}]  {e['summary']}")
    return "\n".join(lines)
