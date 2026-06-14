"""
Tests for F1 full-text extraction and title similarity dedup.
All tests are fast (no network calls).
"""

import pytest
from src.f1_ingest.fulltext import (
    _clean_text,
    _extract_text_from_html,
    title_similarity,
    find_near_duplicates,
    SIMILARITY_THRESHOLD,
)
from src.models import RegulatoryDocument, SourceAgency, DocType


# ── Text cleaning ─────────────────────────────────────────────────────────────

def test_clean_text_collapses_whitespace():
    raw = "This   is\t\na   test   string."
    assert _clean_text(raw) == "This is a test string."


def test_clean_text_strips_edges():
    assert _clean_text("  hello world  ") == "hello world"


# ── HTML extraction ───────────────────────────────────────────────────────────

def test_extract_strips_script_tags():
    html = "<html><body><script>alert('x')</script><p>Real content here.</p></body></html>"
    text = _extract_text_from_html(html)
    assert "alert" not in text
    assert "Real content here" in text


def test_extract_strips_nav():
    html = "<html><body><nav>Home | About | Contact</nav><main><p>Rule text.</p></main></html>"
    text = _extract_text_from_html(html)
    assert "Home | About | Contact" not in text
    assert "Rule text" in text


def test_extract_prefers_main_container():
    html = """
    <html><body>
      <div class="sidebar">Sidebar noise</div>
      <main><p>The regulation states the following requirements.</p></main>
    </body></html>
    """
    text = _extract_text_from_html(html)
    assert "regulation states" in text


def test_extract_falls_back_to_body():
    html = "<html><body><p>Content without semantic tags.</p></body></html>"
    text = _extract_text_from_html(html)
    assert "Content without semantic tags" in text


def test_extract_empty_html_returns_empty():
    assert _extract_text_from_html("") == ""


def test_extract_strips_style_tags():
    html = "<html><body><style>.foo { color: red; }</style><p>Actual text.</p></body></html>"
    text = _extract_text_from_html(html)
    assert "color" not in text
    assert "Actual text" in text


# ── Title similarity ──────────────────────────────────────────────────────────

def test_identical_titles_score_one():
    assert title_similarity("Final Rule on Capital", "Final Rule on Capital") == pytest.approx(1.0)


def test_completely_different_titles_score_low():
    score = title_similarity("Final Rule on Capital Requirements", "Annual Budget Report")
    assert score < 0.5


def test_near_duplicate_titles_score_above_threshold():
    a = "Final Rule on Capital Requirements for Large Banks"
    b = "Final Rule on Capital Requirements for Large Banks (Correction)"
    assert title_similarity(a, b) >= SIMILARITY_THRESHOLD


def test_similarity_is_case_insensitive():
    assert title_similarity("FINAL RULE", "final rule") == pytest.approx(1.0)


# ── Near-duplicate detection ──────────────────────────────────────────────────

def _make_doc(title: str, agency: SourceAgency = SourceAgency.FED) -> RegulatoryDocument:
    from src.f1_ingest.dedup import compute_hash
    return RegulatoryDocument(
        source_agency=agency,
        doc_type=DocType.FINAL_RULE,
        title=title,
        url=f"https://example.com/{hash(title)}",
        content_hash=compute_hash(title, f"https://example.com/{hash(title)}"),
    )


def test_find_near_duplicates_detects_similar_titles():
    docs = [
        _make_doc("Final Rule on BSA Compliance Requirements"),
        _make_doc("Final Rule on BSA Compliance Requirements (Amended)"),
        _make_doc("Guidance on Third-Party Risk Management"),
    ]
    dupes = find_near_duplicates(docs)
    assert len(dupes) == 1
    assert dupes[0][2] >= SIMILARITY_THRESHOLD


def test_find_near_duplicates_ignores_different_agencies():
    docs = [
        _make_doc("Final Rule on Capital", SourceAgency.FED),
        _make_doc("Final Rule on Capital", SourceAgency.OCC),  # same title, different agency
    ]
    # Different agencies — not considered duplicates
    dupes = find_near_duplicates(docs)
    assert len(dupes) == 0


def test_find_near_duplicates_empty_list():
    assert find_near_duplicates([]) == []


def test_find_near_duplicates_no_duplicates():
    docs = [
        _make_doc("Final Rule on Capital Requirements"),
        _make_doc("Guidance on Interest Rate Risk"),
        _make_doc("Enforcement Action Against Community Bank"),
    ]
    assert find_near_duplicates(docs) == []
