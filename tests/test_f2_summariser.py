"""
Tests for F2 summarisation components.
All tests are fast (no API calls, no DB).
"""

import json
import pytest
from src.f2_summarise.chunker import chunk_document, chunk_stats, CHUNK_SIZE, OVERLAP
from src.f2_summarise.retriever import retrieve_top_chunks, _score_chunk, format_chunks_for_prompt
from src.f2_summarise.prompts import build_user_message, SYSTEM_PROMPT, CONFIDENCE_THRESHOLD
from src.f2_summarise.summariser import _parse_summary_json, _validate_summary


# ── Chunker tests ──────────────────────────────────────────────────────────────

def test_chunk_empty_text():
    assert chunk_document("") == []
    assert chunk_document("   ") == []


def test_chunk_short_text():
    # MIN_CHUNK_SIZE = 100 — text below this threshold is filtered out
    # Use text above the threshold for a meaningful single-chunk test
    text = "This is a regulatory notice about final rule changes. " * 3  # ~160 chars
    chunks = chunk_document(text)
    assert len(chunks) == 1
    assert chunks[0].index == 0


def test_chunk_below_min_size_returns_empty():
    # Text shorter than MIN_CHUNK_SIZE (100 chars) produces no chunks
    text = "Short notice."  # 13 chars
    chunks = chunk_document(text)
    assert chunks == []


def test_chunk_produces_overlap():
    # Create text longer than one chunk
    text = "A" * (CHUNK_SIZE + 200)
    chunks = chunk_document(text)
    assert len(chunks) >= 2
    # The end of chunk 0 should overlap with the start of chunk 1
    end_of_first = chunks[0].text[-(OVERLAP):]
    start_of_second = chunks[1].text[:OVERLAP]
    assert end_of_first == start_of_second


def test_chunk_covers_full_document():
    text = "The regulation states the following. " * 100
    chunks = chunk_document(text)
    # Every character should appear in at least one chunk
    # (verify by checking first and last char of original)
    all_text = " ".join(c.text for c in chunks)
    assert text[:50].strip() in all_text
    assert text[-50:].strip() in all_text


def test_chunk_stats():
    text = "Word " * 500
    chunks = chunk_document(text)
    stats = chunk_stats(chunks)
    assert stats["count"] == len(chunks)
    assert stats["avg_chars"] > 0
    assert stats["min_chars"] <= stats["avg_chars"] <= stats["max_chars"]


def test_chunk_indices_are_sequential():
    text = "Regulatory text. " * 200
    chunks = chunk_document(text)
    indices = [c.index for c in chunks]
    assert indices == list(range(len(chunks)))


# ── Retriever tests ────────────────────────────────────────────────────────────

def make_test_chunks(texts: list[str]):
    from src.f2_summarise.chunker import Chunk
    return [Chunk(index=i, text=t, start_char=i*100, end_char=(i+1)*100)
            for i, t in enumerate(texts)]


def test_retrieve_empty_chunks():
    assert retrieve_top_chunks([]) == []


def test_retrieve_scores_compliance_content_higher():
    from src.f2_summarise.chunker import Chunk
    high_relevance = Chunk(0, "The final rule shall take effect January 1, 2027. Banks must comply by this deadline.", 0, 80)
    low_relevance = Chunk(1, "The agency was founded in 1934 and has published many documents.", 80, 160)

    score_high = _score_chunk(high_relevance)
    score_low = _score_chunk(low_relevance)
    assert score_high > score_low


def test_retrieve_returns_sorted_by_position():
    texts = [f"Chunk {i}: {'regulation ' * 20}" for i in range(10)]
    chunks = make_test_chunks(texts)
    result = retrieve_top_chunks(chunks, top_k=5)
    indices = [c.index for c in result]
    assert indices == sorted(indices)


def test_retrieve_always_includes_first_chunk():
    # First chunk (document header) should always be included
    texts = ["Header chunk with title"] + [f"Chunk {i}: compliance deadline effective date institution" for i in range(10)]
    chunks = make_test_chunks(texts)
    result = retrieve_top_chunks(chunks, top_k=3)
    assert any(c.index == 0 for c in result)


def test_format_chunks_for_prompt():
    chunks = make_test_chunks(["First chunk text", "Second chunk text"])
    formatted = format_chunks_for_prompt(chunks)
    assert "[Chunk 1]" in formatted
    assert "[Chunk 2]" in formatted
    assert "First chunk text" in formatted
    assert "Second chunk text" in formatted


# ── Prompt tests ───────────────────────────────────────────────────────────────

def test_system_prompt_contains_key_instructions():
    assert "null" in SYSTEM_PROMPT.lower()
    assert "plain english" in SYSTEM_PROMPT.lower()
    assert "confidence" in SYSTEM_PROMPT.lower()


def test_build_user_message_contains_all_parts():
    msg = build_user_message(
        title="Test Rule",
        agency="cfpb",
        url="https://example.com",
        chunks_text="[Chunk 1]\nThe rule takes effect January 1, 2027.",
    )
    assert "Test Rule" in msg
    assert "cfpb" in msg
    assert "https://example.com" in msg
    assert "January 1, 2027" in msg
    assert "headline" in msg  # schema field names present


def test_confidence_threshold_is_80():
    assert CONFIDENCE_THRESHOLD == 80


# ── JSON parser tests ──────────────────────────────────────────────────────────

def test_parse_valid_json():
    raw = '{"headline": "Test", "confidence_score": 85}'
    result = _parse_summary_json(raw)
    assert result["headline"] == "Test"
    assert result["confidence_score"] == 85


def test_parse_json_with_markdown_fences():
    raw = '```json\n{"headline": "Test", "confidence_score": 90}\n```'
    result = _parse_summary_json(raw)
    assert result["headline"] == "Test"


def test_parse_json_with_preamble():
    raw = 'Here is the summary:\n{"headline": "Test", "confidence_score": 75}'
    result = _parse_summary_json(raw)
    assert result["headline"] == "Test"


def test_parse_invalid_json_raises():
    with pytest.raises(Exception):
        _parse_summary_json("This is not JSON at all")


# ── Validator tests ────────────────────────────────────────────────────────────

def test_validate_complete_summary():
    summary = {
        "headline": "CFPB issues final rule",
        "plain_english_summary": "The rule changes lending requirements.",
        "what_changed": "New data collection requirements added.",
        "why_it_matters": "Community banks must update their systems.",
        "effective_date": "2027-01-01",
        "compliance_deadline": None,
        "affected_institution_types": ["community banks"],
        "confidence_score": 88,
        "source_citations": ["Chunk 2"],
    }
    warnings = _validate_summary(summary)
    assert warnings == []


def test_validate_missing_required_field():
    summary = {
        "headline": "Test",
        # missing plain_english_summary
        "what_changed": "Something changed",
        "why_it_matters": "It matters",
        "confidence_score": 85,
    }
    warnings = _validate_summary(summary)
    assert any("plain_english_summary" in w for w in warnings)


def test_validate_confidence_out_of_range():
    summary = {
        "headline": "Test",
        "plain_english_summary": "Summary",
        "what_changed": "Changed",
        "why_it_matters": "Matters",
        "confidence_score": 150,  # invalid
    }
    warnings = _validate_summary(summary)
    assert any("confidence_score" in w for w in warnings)
