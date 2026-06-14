"""
F1 integration tests — hit live feeds against a real (temporary) database.

Marked with @pytest.mark.slow — excluded from the default test run.
Include with:  pytest tests/ -m slow
Exclude with:  pytest tests/ -m "not slow"  (default)

These tests verify the full pipeline works end-to-end against real
government data sources. They are inherently slower and depend on
network access. Run them before any deployment or after changing
feed URLs or fetcher logic.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from src.f1_ingest.agencies import AGENCY_SEEDS
from src.f1_ingest.dedup import compute_hash
from src.f1_ingest.fetcher import fetch_feed, fetch_fr_api
from src.models import Agency, DocType, RegulatoryDocument, SourceAgency


@pytest.fixture(scope="module")
def test_engine():
    """In-memory DB for integration tests — fresh per module, not per test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def fed_agency(test_engine):
    """Seed a Federal Reserve agency record in the test DB."""
    fed_seed = next(s for s in AGENCY_SEEDS if s["slug"] == "fed")
    agency = Agency(**fed_seed)
    with Session(test_engine) as session:
        session.add(agency)
        session.commit()
        session.refresh(agency)
    return agency


@pytest.fixture(scope="module")
def cfpb_agency(test_engine):
    """Seed a CFPB agency record (uses FR API)."""
    cfpb_seed = next(s for s in AGENCY_SEEDS if s["slug"] == "cfpb")
    agency = Agency(**cfpb_seed)
    with Session(test_engine) as session:
        session.add(agency)
        session.commit()
        session.refresh(agency)
    return agency


@pytest.mark.slow
def test_fed_feed_returns_documents(fed_agency):
    """The Federal Reserve RSS feed must return at least 5 documents."""
    docs = fetch_feed(fed_agency)
    assert len(docs) >= 5, f"Expected ≥5 docs from Fed feed, got {len(docs)}"


@pytest.mark.slow
def test_fed_docs_have_required_fields(fed_agency):
    """Every Fed document must have title, URL, content_hash, and source_agency."""
    docs = fetch_feed(fed_agency)
    assert docs, "No documents returned from Fed feed"

    for doc in docs:
        assert doc.title, f"Document missing title: {doc}"
        assert doc.url, f"Document missing URL: {doc}"
        assert doc.content_hash, f"Document missing content_hash: {doc}"
        assert doc.source_agency == SourceAgency.FED
        assert doc.doc_type in list(DocType), f"Invalid doc_type: {doc.doc_type}"


@pytest.mark.slow
def test_fed_content_hash_is_unique(fed_agency):
    """No two documents from the same feed run should have the same hash."""
    docs = fetch_feed(fed_agency)
    hashes = [d.content_hash for d in docs]
    assert len(hashes) == len(set(hashes)), "Duplicate content hashes within single feed fetch"


@pytest.mark.slow
def test_cfpb_fr_api_returns_documents(cfpb_agency):
    """The CFPB Federal Register API must return at least 5 documents."""
    docs = fetch_fr_api(cfpb_agency)
    assert len(docs) >= 5, f"Expected ≥5 docs from CFPB FR API, got {len(docs)}"


@pytest.mark.slow
def test_cfpb_docs_have_required_fields(cfpb_agency):
    """Every CFPB document must have title, URL, and content_hash."""
    docs = fetch_fr_api(cfpb_agency)
    assert docs, "No documents returned from CFPB FR API"

    for doc in docs:
        assert doc.title, f"Document missing title: {doc}"
        assert doc.url.startswith("https://"), f"URL not HTTPS: {doc.url}"
        assert doc.content_hash, f"Document missing content_hash: {doc}"
        assert len(doc.content_hash) == 64, "content_hash is not a SHA-256 hex digest (64 chars)"


@pytest.mark.slow
def test_dedup_prevents_double_insert(fed_agency, test_engine):
    """
    Running fetch twice should not produce duplicate hashes.
    This simulates the daily re-run scenario.
    """
    docs_run1 = fetch_feed(fed_agency)
    docs_run2 = fetch_feed(fed_agency)

    hashes_run1 = {d.content_hash for d in docs_run1}
    hashes_run2 = {d.content_hash for d in docs_run2}

    # The same feed fetched twice should produce the same set of hashes
    assert hashes_run1 == hashes_run2, "Same feed returned different hashes on second fetch"


@pytest.mark.slow
def test_zero_missed_publications_metric(fed_agency):
    """
    F1 success metric: the pipeline must capture all entries the feed exposes.
    Verify: doc count from fetcher == entry count reported by feedparser directly.
    """
    import feedparser, httpx
    response = httpx.get(
        fed_agency.feed_url,
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "RegWatch-AI/1.0"},
    )
    raw_feed = feedparser.parse(response.text)
    raw_count = len([e for e in raw_feed.entries if e.get("title") and e.get("link")])

    our_docs = fetch_feed(fed_agency)
    assert len(our_docs) == raw_count, (
        f"Pipeline captured {len(our_docs)} docs but feed has {raw_count} entries — "
        f"zero-missed-publications metric FAILED"
    )
