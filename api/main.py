"""
RegWatch AI — FastAPI layer (Day 40, KM #227 FastAPI / #229 Docker).

Read-only endpoints over the same DB + data/f3_indexes/*.json that
dashboard/app.py and the scripts/ CLI tools already read. No new write
paths -- this is a presentation layer, not a new source of truth.

Run locally:
    uvicorn api.main:app --reload

Endpoints (see docstrings below for filters):
    GET /health
    GET /f1/documents
    GET /f1/documents/{doc_id}
    GET /f2/review-queue
    GET /f2/summaries
    GET /f3/impact-results
    GET /f3/policy-sections
    GET /f4/tasks
    GET /f5/audit-log
    GET /f5/compliance-report
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from sqlmodel import select

from src.database import get_session
from src.models import AuditAction, AuditLog, RegulatoryDocument, Task
from scripts.weekly_compliance_report import build_report

PROJECT_ROOT = Path(__file__).resolve().parents[1]
F3_INDEX_DIR = PROJECT_ROOT / "data" / "f3_indexes"

app = FastAPI(
    title="RegWatch AI API",
    description="Compliance intelligence platform for US community banks — F1-F5 read API.",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ── F1 — Feed ────────────────────────────────────────────────────────────────

def _doc_to_dict(doc: RegulatoryDocument) -> dict:
    return {
        "id": doc.id,
        "title": doc.title,
        "url": doc.url,
        "source_agency": doc.source_agency.value,
        "doc_type": doc.doc_type.value,
        "published_date": doc.published_date,
        "fetched_at": doc.fetched_at,
        "status": doc.status.value,
        "review_flag": doc.review_flag,
        "is_anomaly": doc.is_anomaly,
        "summary_json": json.loads(doc.summary_json) if doc.summary_json else None,
    }


@app.get("/f1/documents")
def list_documents(
    agency: Optional[str] = Query(None, description="Filter by source_agency, e.g. 'cfpb'"),
    doc_type: Optional[str] = Query(None, description="Filter by doc_type, e.g. 'final_rule'"),
    anomaly: Optional[bool] = Query(None, description="If true, only anomalous documents"),
) -> list[dict]:
    """List ingested regulatory documents (F1), optionally filtered."""
    with get_session() as session:
        docs = session.exec(select(RegulatoryDocument)).all()

    result = [_doc_to_dict(d) for d in docs]
    if agency:
        result = [d for d in result if d["source_agency"] == agency]
    if doc_type:
        result = [d for d in result if d["doc_type"] == doc_type]
    if anomaly is not None:
        result = [d for d in result if d["is_anomaly"] == anomaly]
    return result


@app.get("/f1/documents/{doc_id}")
def get_document(doc_id: str) -> dict:
    """Fetch a single regulatory document by id, including its F2 summary if present."""
    with get_session() as session:
        doc = session.get(RegulatoryDocument, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_to_dict(doc)


# ── F2 — Summarisation ──────────────────────────────────────────────────────

@app.get("/f2/review-queue")
def review_queue() -> list[dict]:
    """Summarised documents flagged for human review (review_flag=True)."""
    with get_session() as session:
        docs = session.exec(
            select(RegulatoryDocument).where(RegulatoryDocument.review_flag == True)  # noqa: E712
        ).all()
    return [_doc_to_dict(d) for d in docs]


@app.get("/f2/summaries")
def summaries() -> list[dict]:
    """Documents with an F2 summary attached, regardless of review status."""
    with get_session() as session:
        docs = session.exec(
            select(RegulatoryDocument).where(RegulatoryDocument.summary_json.is_not(None))
        ).all()
    return [_doc_to_dict(d) for d in docs]


# ── F3 — Policy impact mapping ──────────────────────────────────────────────

@app.get("/f3/impact-results")
def impact_results(
    impact_level: Optional[str] = Query(
        None, description="Filter matches to only this impact_level (e.g. 'high')"
    ),
) -> list[dict]:
    """Per-policy-section regulation matches with impact_level (output of classifier.py)."""
    path = F3_INDEX_DIR / "impact_results.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="impact_results.json not found -- run python -m src.f3_impact.classifier first",
        )
    sections = json.loads(path.read_text(encoding="utf-8"))

    if impact_level:
        sections = [
            {**section, "matches": [m for m in section["matches"] if m["impact_level"] == impact_level]}
            for section in sections
        ]
        sections = [s for s in sections if s["matches"]]

    return sections


@app.get("/f3/policy-sections")
def policy_sections() -> list[dict]:
    """Indexed policy sections (metadata only -- vectors are not exposed)."""
    path = F3_INDEX_DIR / "policy_sections.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="policy_sections.json not found -- run python -m src.f3_impact.build_indexes first",
        )
    index = json.loads(path.read_text(encoding="utf-8"))
    return index["metadata"]


# ── F4 — Task generation ────────────────────────────────────────────────────

@app.get("/f4/tasks")
def list_tasks(status: Optional[str] = Query(None, description="Filter by task status")) -> list[dict]:
    """Drafted compliance tasks (F4)."""
    with get_session() as session:
        tasks = session.exec(select(Task)).all()

    result = [
        {
            "id": t.id,
            "created_at": t.created_at,
            "title": t.title,
            "description": t.description,
            "owner": t.owner,
            "due_date": t.due_date,
            "status": t.status.value,
            "source_policy_name": t.source_policy_name,
            "source_section_id": t.source_section_id,
            "source_regulation_title": t.source_regulation_title,
            "source_impact_level": t.source_impact_level,
            "linked_regulations": json.loads(t.linked_regulations_json) if t.linked_regulations_json else [],
        }
        for t in tasks
    ]
    if status:
        result = [t for t in result if t["status"] == status]
    return result


# ── F5 — Audit trail + reporting ────────────────────────────────────────────

@app.get("/f5/audit-log")
def audit_log(
    action: Optional[str] = Query(None, description="Filter by AuditAction, e.g. 'summarise'"),
    doc_id: Optional[str] = Query(None, description="Filter by RegulatoryDocument id"),
    limit: int = Query(100, ge=1, le=1000, description="Max rows to return, newest first"),
) -> list[dict]:
    """Raw AuditLog rows -- the SR 11-7 audit trail."""
    if action is not None and action not in {a.value for a in AuditAction}:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    with get_session() as session:
        query = select(AuditLog)
        if action:
            query = query.where(AuditLog.action == AuditAction(action))
        if doc_id:
            query = query.where(AuditLog.doc_id == doc_id)
        logs = session.exec(query).all()

    logs = sorted(logs, key=lambda l: l.timestamp, reverse=True)[:limit]
    return [
        {
            "id": l.id,
            "timestamp": l.timestamp,
            "action": l.action.value,
            "actor": l.actor,
            "doc_id": l.doc_id,
            "langsmith_trace_id": l.langsmith_trace_id,
            "payload": json.loads(l.payload_json) if l.payload_json else None,
        }
        for l in logs
    ]


@app.get("/f5/compliance-report")
def compliance_report(days: int = Query(7, ge=1, le=90, description="Trailing window in days")) -> dict:
    """Weekly compliance report (Day 38) as JSON instead of Markdown."""
    return build_report(days=days)
