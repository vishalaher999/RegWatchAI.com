"""
Tests for scripts/cost_dashboard.py (Day 44, KM #239 -- cost ($/query)
dashboard) -- in-memory SQLite, same pattern as tests/test_override_rate.py.
"""

import json
from contextlib import contextmanager

import pytest
from sqlmodel import Session, SQLModel, create_engine

from scripts import cost_dashboard
from src.models import AuditAction, AuditLog


@pytest.fixture
def in_memory_engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    @contextmanager
    def mock_get_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(cost_dashboard, "get_session", mock_get_session)
    return engine


def _summarise_log(model, input_tokens, output_tokens):
    return AuditLog(
        action=AuditAction.SUMMARISE,
        actor="system:f2",
        payload_json=json.dumps({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }),
    )


def test_compute_cost_report_sums_tokens_and_cost_by_model(in_memory_engine):
    with Session(in_memory_engine) as session:
        session.add(_summarise_log("claude-sonnet-4-20250514", 10_000, 1_000))
        session.add(_summarise_log("claude-sonnet-4-20250514", 5_000, 500))
        session.add(_summarise_log("claude-haiku-4-5-20251001", 2_000, 200))
        session.commit()

    report = cost_dashboard.compute_cost_report()

    assert report["total_summarise_logs"] == 3
    assert report["queries_with_token_data"] == 3
    assert report["total_input_tokens"] == 17_000
    assert report["total_output_tokens"] == 1_700

    sonnet = report["by_model"]["claude-sonnet-4-20250514"]
    assert sonnet["queries"] == 2
    assert sonnet["input_tokens"] == 15_000
    assert sonnet["output_tokens"] == 1_500
    # 15,000/1e6 * $3 + 1,500/1e6 * $15 = 0.045 + 0.0225 = 0.0675
    assert sonnet["cost_usd"] == pytest.approx(0.0675, abs=1e-4)

    haiku = report["by_model"]["claude-haiku-4-5-20251001"]
    # 2,000/1e6 * $1 + 200/1e6 * $5 = 0.002 + 0.001 = 0.003
    assert haiku["cost_usd"] == pytest.approx(0.003, abs=1e-4)

    assert report["total_cost_usd"] == pytest.approx(0.0705, abs=1e-4)
    assert report["cost_per_query_usd"] == pytest.approx(0.0705 / 3, abs=1e-4)


def test_compute_cost_report_skips_rows_without_token_data(in_memory_engine):
    with Session(in_memory_engine) as session:
        # Pre-Day-44 row: no input_tokens/output_tokens keys at all.
        session.add(AuditLog(
            action=AuditAction.SUMMARISE,
            actor="system:f2",
            payload_json=json.dumps({"model": "claude-sonnet-4-20250514"}),
        ))
        session.commit()

    report = cost_dashboard.compute_cost_report()

    assert report["total_summarise_logs"] == 1
    assert report["queries_with_token_data"] == 0
    assert report["total_cost_usd"] == 0.0
    assert report["cost_per_query_usd"] == 0.0
    assert report["by_model"] == {}


def test_compute_cost_report_with_no_logs_returns_zeroes(in_memory_engine):
    report = cost_dashboard.compute_cost_report()

    assert report["total_summarise_logs"] == 0
    assert report["queries_with_token_data"] == 0
    assert report["total_cost_usd"] == 0.0
    assert report["cost_per_query_usd"] == 0.0
