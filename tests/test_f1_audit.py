"""
Tests for src/f1_ingest/ingest.py log_document_ingest (Day 36, KM #242
Compliance logging) -- in-memory SQLite, same pattern as test_f1_dedup.py.
"""

import json
from contextlib import contextmanager

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from src.f1_ingest.ingest import log_document_ingest
from src.models import AuditAction, AuditLog, DocType, RegulatoryDocument, SourceAgency


@pytest.fixture
def in_memory_engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine


def test_log_document_ingest_writes_doc_scoped_entry(in_memory_engine):
    doc = RegulatoryDocument(
        source_agency=SourceAgency.FED,
        doc_type=DocType.FINAL_RULE,
        title="Final Rule on Capital",
        url="https://example.com/rule1",
        content_hash="abc123",
    )

    with Session(in_memory_engine) as session:
        session.add(doc)
        log_document_ingest(session, doc, "fed")
        session.commit()
        doc_id = doc.id

    with Session(in_memory_engine) as session:
        logs = session.exec(select(AuditLog).where(AuditLog.action == AuditAction.INGEST)).all()

    assert len(logs) == 1
    log = logs[0]
    assert log.doc_id == doc_id
    assert log.actor == "system"

    payload = json.loads(log.payload_json)
    assert payload["agency"] == "fed"
    assert payload["title"] == "Final Rule on Capital"
    assert payload["doc_type"] == "final_rule"
    assert payload["url"] == "https://example.com/rule1"
