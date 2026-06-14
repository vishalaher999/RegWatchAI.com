"""
Tests for src/f3_impact/classifier.py log_map_decisions (Day 36, KM #242
Compliance logging) -- in-memory SQLite, same pattern as test_f4_audit.py.
"""

import json
from contextlib import contextmanager

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from src.f3_impact import classifier as classifier_module
from src.f3_impact.classifier import (
    HIGH_THRESHOLD,
    LOW_THRESHOLD,
    MEDIUM_THRESHOLD,
    classify_matches,
    log_map_decisions,
)
from src.models import AuditAction, AuditLog


SECTIONS = [
    {
        "policy_name": "Fair-Lending-ECOA-Policy",
        "section_id": "2.1",
        "section_title": "Prohibited Bases Under ECOA/Regulation B",
        "parent_section": "SECTION 2: PROHIBITED BASES FOR DISCRIMINATION",
        "matches": [
            {
                "regulation_doc_id": "docA",
                "regulation_title": "Equal Credit Opportunity Act (Regulation B)",
                "dense_score": 0.60,
                "score": 0.03,
            },
            {
                "regulation_doc_id": "docB",
                "regulation_title": "Agencies issue host state loan-to-deposit ratios",
                "dense_score": 0.30,
                "score": 0.02,
            },
        ],
    }
]


@pytest.fixture
def in_memory_engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    @contextmanager
    def mock_get_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(classifier_module, "get_session", mock_get_session)
    return engine


def test_log_map_decisions_writes_one_entry_per_match(in_memory_engine):
    results = classify_matches(SECTIONS)

    count = log_map_decisions(results)
    assert count == 2

    with Session(in_memory_engine) as session:
        logs = session.exec(select(AuditLog).where(AuditLog.action == AuditAction.MAP)).all()

    assert len(logs) == 2

    by_doc = {log.doc_id: log for log in logs}

    high_payload = json.loads(by_doc["docA"].payload_json)
    assert high_payload["policy_name"] == "Fair-Lending-ECOA-Policy"
    assert high_payload["section_id"] == "2.1"
    assert high_payload["impact_level"] == "high"
    assert high_payload["named_regulation_match"] is True
    assert high_payload["high_threshold"] == HIGH_THRESHOLD
    assert high_payload["medium_threshold"] == MEDIUM_THRESHOLD
    assert high_payload["low_threshold"] == LOW_THRESHOLD

    na_payload = json.loads(by_doc["docB"].payload_json)
    assert na_payload["impact_level"] == "not_applicable"
    assert na_payload["named_regulation_match"] is False


def test_log_map_decisions_handles_section_with_no_matches(in_memory_engine):
    results = classify_matches([
        {
            "policy_name": "BSA-AML-Policy",
            "section_id": "1.1",
            "section_title": "Purpose",
            "parent_section": "SECTION 1",
            "matches": [],
        }
    ])

    count = log_map_decisions(results)
    assert count == 0

    with Session(in_memory_engine) as session:
        logs = session.exec(select(AuditLog).where(AuditLog.action == AuditAction.MAP)).all()
    assert logs == []
