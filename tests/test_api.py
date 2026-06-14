"""
Day 40 (KM #227 FastAPI) tests for api/main.py.

These hit the real dev DB + data/f3_indexes/*.json (read-only, same as
dashboard/app.py) rather than a fixture DB -- the goal is to verify the
FastAPI layer correctly shapes/filters whatever the current dev data is,
not to test F1-F5 logic itself (already covered elsewhere).
"""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_documents_returns_list():
    resp = client.get("/f1/documents")
    assert resp.status_code == 200
    docs = resp.json()
    assert isinstance(docs, list)
    assert len(docs) > 0
    assert "source_agency" in docs[0]


def test_get_document_by_id():
    docs = client.get("/f1/documents").json()
    doc_id = docs[0]["id"]
    resp = client.get(f"/f1/documents/{doc_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == doc_id


def test_get_document_404():
    resp = client.get("/f1/documents/does-not-exist")
    assert resp.status_code == 404


def test_review_queue_only_flagged():
    resp = client.get("/f2/review-queue")
    assert resp.status_code == 200
    for doc in resp.json():
        assert doc["review_flag"] is True


def test_summaries_have_summary_json():
    resp = client.get("/f2/summaries")
    assert resp.status_code == 200
    for doc in resp.json():
        assert doc["summary_json"] is not None


def test_impact_results_filter_by_level():
    resp = client.get("/f3/impact-results?impact_level=high")
    assert resp.status_code == 200
    for section in resp.json():
        for match in section["matches"]:
            assert match["impact_level"] == "high"


def test_policy_sections_returns_metadata():
    resp = client.get("/f3/policy-sections")
    assert resp.status_code == 200
    sections = resp.json()
    assert len(sections) == 72
    assert "policy_name" in sections[0]


def test_list_tasks_returns_list():
    resp = client.get("/f4/tasks")
    assert resp.status_code == 200
    tasks = resp.json()
    assert isinstance(tasks, list)
    for task in tasks:
        assert "source_impact_level" in task


def test_audit_log_invalid_action_400():
    resp = client.get("/f5/audit-log?action=not_a_real_action")
    assert resp.status_code == 400


def test_audit_log_filter_by_action():
    resp = client.get("/f5/audit-log?action=summarise&limit=3")
    assert resp.status_code == 200
    for row in resp.json():
        assert row["action"] == "summarise"


def test_compliance_report_shape():
    resp = client.get("/f5/compliance-report")
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "documents_ingested", "summaries_by_routing", "guardrail_warnings",
        "high_findings", "tasks_created", "override_rate_pct",
    ):
        assert key in body
