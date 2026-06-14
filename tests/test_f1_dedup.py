"""
Tests for the F1 deduplication logic.
Uses an in-memory SQLite database — no file created, no cleanup needed.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.f1_ingest.dedup import compute_hash, is_duplicate
from src.models import RegulatoryDocument, SourceAgency, DocType


@pytest.fixture
def in_memory_engine(monkeypatch):
    """Create a fresh in-memory SQLite DB for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    # Patch get_session to use our test engine
    import src.f1_ingest.dedup as dedup_module
    from contextlib import contextmanager

    @contextmanager
    def mock_get_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(dedup_module, "get_session", mock_get_session)
    return engine


def test_compute_hash_is_deterministic():
    h1 = compute_hash("Final Rule on Capital", "https://example.com/rule1")
    h2 = compute_hash("Final Rule on Capital", "https://example.com/rule1")
    assert h1 == h2


def test_compute_hash_differs_for_different_inputs():
    h1 = compute_hash("Rule A", "https://example.com/a")
    h2 = compute_hash("Rule B", "https://example.com/b")
    assert h1 != h2


def test_is_duplicate_returns_false_for_new_doc(in_memory_engine):
    hash_val = compute_hash("New Rule", "https://example.com/new")
    assert is_duplicate(hash_val) is False


def test_is_duplicate_returns_true_after_insert(in_memory_engine):
    hash_val = compute_hash("Existing Rule", "https://example.com/existing")
    doc = RegulatoryDocument(
        source_agency=SourceAgency.FED,
        doc_type=DocType.FINAL_RULE,
        title="Existing Rule",
        url="https://example.com/existing",
        content_hash=hash_val,
    )
    with Session(in_memory_engine) as session:
        session.add(doc)
        session.commit()

    assert is_duplicate(hash_val) is True
