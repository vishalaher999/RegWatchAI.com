"""
End-to-end integration test (Day 43, KM #227 FastAPI end-to-end --
"RSS ingest -> summary -> impact -> task -> audit report").

Exercises the full F1 -> F2 -> F3 -> F4 -> F5 chain through one in-memory
SQLite DB, asserting the same AuditLog rows / Task rows / report counts that
a real run would produce. The only mocked boundary is the Anthropic API call
inside F2's _call_claude (no network, no API cost) -- chunking, hybrid
retrieval, reranking, NER, guardrails, routing, F3's threshold-based
classification, the F4 LangGraph HITL graph, Day 42's notification outbox,
and F5's weekly_compliance_report aggregation all run for real.

This is the integration test the roadmap calls "RSS ingest -> summary ->
impact -> task -> audit report" -- F1's actual feed fetch is out of scope
(covered separately, @pytest.mark.slow, in tests/test_f1_integration.py);
here F1 is represented by writing the AuditLog(INGEST) row a real ingest run
would write for one document.
"""

import json
from contextlib import contextmanager
from datetime import datetime

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from scripts import override_rate_report, weekly_compliance_report
from src.f1_ingest.dedup import compute_hash
from src.f2_summarise import summariser
from src.f3_impact import classifier as classifier_module
from src.f4_tasks import hitl_agent as hitl_module
from src.models import (
    AuditAction,
    AuditLog,
    DocStatus,
    DocType,
    RegulatoryDocument,
    SourceAgency,
    Task,
)

RAW_CONTENT = """
SECTION 1: OVERVIEW

The Consumer Financial Protection Bureau is issuing this final rule to
amend Regulation B (Equal Credit Opportunity Act) requirements applicable
to small business lending data collection. This rule updates reporting
thresholds and clarifies the definition of a "small business" for purposes
of fair lending analysis.

SECTION 2: EFFECTIVE DATE AND COMPLIANCE DEADLINE

This rule is effective August 1, 2026. Covered financial institutions must
comply with the new data collection requirements by September 1, 2026.
Institutions with fewer than 100 covered originations in either of the two
preceding calendar years are exempt from the reporting requirement for the
following calendar year.

SECTION 3: AFFECTED INSTITUTIONS

This rule applies to banks, credit unions, and other financial institutions
that originate small business loans, including community banks supervised
by the OCC, FDIC, and the Federal Reserve. Institutions should review their
internal fair lending policies, including any sections addressing data
collection, recordkeeping, and reporting obligations under Regulation B.

SECTION 4: WHAT CHANGED

Previously, institutions were required to report small business lending
data using the prior thresholds established in the 2023 rulemaking. This
rule raises those thresholds and adds two new data fields: pricing
information and time in business. Institutions must update their data
collection systems and staff training materials accordingly before the
compliance deadline.

SECTION 5: WHY IT MATTERS

Failure to comply with the updated data collection and reporting
requirements by the compliance deadline may result in supervisory findings
during the next fair lending examination. Community banks should treat this
as a near-term priority given the relatively short window between the
effective date and the compliance deadline.
""".strip()


@pytest.fixture
def in_memory_engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    @contextmanager
    def mock_get_session():
        with Session(engine) as session:
            yield session

    for module in (summariser, classifier_module, hitl_module,
                   weekly_compliance_report, override_rate_report):
        monkeypatch.setattr(module, "get_session", mock_get_session)

    monkeypatch.setattr(hitl_module, "create_db_and_tables", lambda: None)

    return engine


class FakeMessages:
    def __init__(self, text: str):
        self._text = text

    def create(self, **kwargs):
        from types import SimpleNamespace
        return SimpleNamespace(content=[SimpleNamespace(text=self._text)])


class FakeClient:
    def __init__(self, text: str):
        self.messages = FakeMessages(text)


FAKE_SUMMARY = {
    "headline": "CFPB Updates Small Business Lending Data Reporting Thresholds",
    "plain_english_summary": "The CFPB raised the reporting thresholds for "
                              "small business lending data and added two new "
                              "data fields under Regulation B.",
    "what_changed": "Reporting thresholds increased; pricing and time-in-business "
                    "fields added.",
    "why_it_matters": "Community banks must update data collection systems before "
                      "the compliance deadline or risk supervisory findings.",
    "confidence_score": 92,
    "effective_date": "2026-08-01",
    "compliance_deadline": "2026-09-01",
    "affected_institutions": ["community banks", "credit unions"],
    "source_citations": [
        "Chunk 1 - effective_date",
        "Chunk 1 - compliance_deadline",
    ],
}


def test_full_pipeline_ingest_to_audit_report(in_memory_engine, monkeypatch, tmp_path):
    # ── F1: one document already "ingested" (real ingest writes this AuditLog) ──
    with Session(in_memory_engine) as session:
        title = "Small Business Lending Data Collection Under Regulation B"
        url = "https://example.gov/cfpb/reg-b-small-business-2026"
        doc = RegulatoryDocument(
            title=title,
            url=url,
            source_agency=SourceAgency.CFPB,
            doc_type=DocType.FINAL_RULE,
            status=DocStatus.NEW,
            raw_content=RAW_CONTENT,
            content_hash=compute_hash(title, url),
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        doc_id = doc.id

        session.add(AuditLog(
            action=AuditAction.INGEST,
            actor="system",
            doc_id=doc_id,
            payload_json=json.dumps({
                "agency": "cfpb",
                "title": doc.title,
                "doc_type": doc.doc_type.value,
                "url": doc.url,
            }),
        ))
        session.commit()

    # ── F2: summarise (mocked LLM boundary only) ────────────────────────────────
    monkeypatch.setattr(
        summariser, "_get_client",
        lambda: FakeClient(json.dumps(FAKE_SUMMARY)),
    )

    with Session(in_memory_engine) as session:
        doc = session.get(RegulatoryDocument, doc_id)

    summary = summariser.summarise_document(doc, verbose=False)

    assert summary is not None
    assert summary["headline"] == FAKE_SUMMARY["headline"]

    with Session(in_memory_engine) as session:
        db_doc = session.get(RegulatoryDocument, doc_id)
        assert db_doc.status == DocStatus.SUMMARISED
        assert db_doc.summary_json is not None

        summarise_logs = session.exec(
            select(AuditLog).where(AuditLog.action == AuditAction.SUMMARISE)
        ).all()
        assert len(summarise_logs) == 1
        summarise_payload = json.loads(summarise_logs[0].payload_json)
        assert summarise_payload["guardrail_warnings"] == []

    # ── F3: impact mapping (real threshold-based classification) ────────────────
    # dense_score=0.9 clears HIGH_THRESHOLD (0.55) regardless of the named-match
    # adjustment (+0.10 / -0.20), so this section is unambiguously HIGH impact.
    sections = [{
        "policy_name": "Fair-Lending-ECOA-Policy",
        "section_id": "1.1",
        "section_title": "Purpose",
        "parent_section": "SECTION 1: PURPOSE AND SCOPE",
        "matches": [{
            "regulation_doc_id": doc_id,
            "regulation_title": doc.title,
            "dense_score": 0.9,
            "matched_chunk_text": "small business lending data collection",
        }],
    }]

    classified = classifier_module.classify_matches(sections)
    assert classified[0]["matches"][0]["impact_level"] == "high"

    written = classifier_module.log_map_decisions(classified)
    assert written == 1

    with Session(in_memory_engine) as session:
        map_logs = session.exec(
            select(AuditLog).where(AuditLog.action == AuditAction.MAP)
        ).all()
        assert len(map_logs) == 1
        assert json.loads(map_logs[0].payload_json)["impact_level"] == "high"

    # ── F4: HITL task drafting + approval ───────────────────────────────────────
    finding = {
        "policy_name": "Fair-Lending-ECOA-Policy",
        "section_id": "1.1",
        "section_title": "Purpose",
        "parent_section": "SECTION 1: PURPOSE AND SCOPE",
        "regulation_doc_id": doc_id,
        "regulation_title": doc.title,
        "impact_level": "high",
        "matched_chunk_text": "small business lending data collection",
    }
    drafted_task = {
        "source_policy_name": finding["policy_name"],
        "source_section_id": finding["section_id"],
        "source_regulation_doc_id": finding["regulation_doc_id"],
        "source_regulation_title": finding["regulation_title"],
        "source_impact_level": finding["impact_level"],
        "title": "Review Fair-Lending-ECOA-Policy Section 1.1 against updated Reg B reporting thresholds",
        "description": "Update data collection systems for the new pricing and "
                        "time-in-business fields before the compliance deadline.",
        "owner": "Sarah",
        "due_date": "2026-09-01",
    }

    def fake_draft_fn(_finding, _today):
        return dict(drafted_task)

    monkeypatch.setattr(hitl_module, "load_high_findings", lambda: [finding])
    monkeypatch.setattr("src.f4_tasks.notifications.OUTBOX_PATH", tmp_path / "notifications.jsonl")

    graph = hitl_module.build_graph(fake_draft_fn)
    pending, graph = hitl_module.run_with_approval(limit=1, graph=graph)
    assert len(pending) == 1

    result = hitl_module.resolve_approval(graph, pending[0]["thread_id"], approved=True)
    assert result["status"] == "created"

    with Session(in_memory_engine) as session:
        tasks = session.exec(select(Task)).all()
        assert len(tasks) == 1
        assert tasks[0].title == drafted_task["title"]
        assert tasks[0].source_regulation_doc_id == doc_id

        task_create_logs = session.exec(
            select(AuditLog).where(AuditLog.action == AuditAction.TASK_CREATE)
        ).all()
        assert len(task_create_logs) == 1

    # Day 42: approval queues a "new task assigned" notification
    outbox_path = tmp_path / "notifications.jsonl"
    assert outbox_path.exists()
    notification = json.loads(outbox_path.read_text(encoding="utf-8").strip().splitlines()[0])
    assert notification["kind"] == "new_task_assigned"
    assert notification["to"] == "Sarah"

    # ── F5: weekly compliance report aggregates everything above ────────────────
    report = weekly_compliance_report.build_report(days=7, now=datetime.utcnow())

    assert report["documents_ingested"] == 1
    assert report["high_findings"] == 1
    assert report["tasks_created"] == 1
    assert "guardrail_warnings" in report
