"""
Day 38 (KM #263 Citations + #269 Guardrails) tests for _apply_guardrails.

_apply_guardrails is a post-hoc safety check on Claude's structured output,
independent of confidence_score and the router. Each test below is one
failure mode from the eval-first plan:
  1. A date field with no field-level citation (closes the gap from
     docs/RCA-Hallucinated-Deadline-v1.md).
  2. A properly-cited date field -- no false positive.
  3. High confidence with empty source_citations.
  4. A citation referencing a chunk outside the retrieved range.
  5. A clean summary (cited dates, in-range citations, high confidence)
     produces zero warnings.
"""

from src.f2_summarise.prompts import CONFIDENCE_THRESHOLD
from src.f2_summarise.summariser import _apply_guardrails


def test_date_field_without_citation_warns():
    summary = {
        "compliance_deadline": "2027-01-01",
        "confidence_score": 70,
        "source_citations": ["Chunk 2 (institution types: banks)"],
    }
    warnings = _apply_guardrails(summary, num_chunks=5)
    assert any("compliance_deadline" in w for w in warnings)


def test_date_field_with_matching_citation_passes():
    summary = {
        "compliance_deadline": "2027-01-01",
        "confidence_score": 70,
        "source_citations": ["Chunk 3 (compliance_deadline: Jan 1 2027)"],
    }
    warnings = _apply_guardrails(summary, num_chunks=5)
    assert warnings == []


def test_high_confidence_with_no_citations_warns():
    summary = {
        "effective_date": None,
        "compliance_deadline": None,
        "confidence_score": CONFIDENCE_THRESHOLD,
        "source_citations": [],
    }
    warnings = _apply_guardrails(summary, num_chunks=5)
    assert any("confidence_score" in w for w in warnings)


def test_citation_referencing_out_of_range_chunk_warns():
    summary = {
        "confidence_score": 70,
        "source_citations": ["Chunk 9 (effective_date: some date)"],
    }
    warnings = _apply_guardrails(summary, num_chunks=5)
    assert any("Chunk 9" in w for w in warnings)


def test_clean_summary_produces_no_warnings():
    summary = {
        "effective_date": "2026-07-21",
        "compliance_deadline": "2027-01-01",
        "confidence_score": 88,
        "source_citations": [
            "Chunk 1 (effective_date: July 21 2026)",
            "Chunk 3 (compliance_deadline: Jan 1 2027)",
        ],
    }
    warnings = _apply_guardrails(summary, num_chunks=5)
    assert warnings == []
