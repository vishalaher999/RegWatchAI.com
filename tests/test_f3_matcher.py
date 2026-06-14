"""
Tests for src/f3_impact/matcher.py.

Uses the same fake embedding model pattern as test_f3_vectorstore.py so
these tests don't download sentence-transformers.
"""

from dataclasses import dataclass

import numpy as np
import pytest

from src.f3_impact import matcher as matcher_module
from src.f3_impact.matcher import HybridMatcher, _rrf_combine
from src.f3_impact.vectorstore import VectorIndex


@dataclass
class _FakeResult:
    vector: np.ndarray


class _FakeEmbeddingModel:
    """Maps known text strings to hand-picked normalized 3D vectors."""

    VECTORS = {
        "currency transaction report cash ten thousand dollars": np.array([1.0, 0.0, 0.0]),
        "ctr threshold reduced to five thousand": np.array([0.95, 0.05, 0.0]),
        "mortgage closing disclosure timing": np.array([0.0, 1.0, 0.0]),
        "reserve requirement ratio change": np.array([0.0, 0.0, 1.0]),
        # Day 30 multi-query: the extra query issued for a named regulation
        "currency transaction report cash ten thousand dollars\nBank Secrecy Act": np.array([0.9, 0.0, 0.1]),
    }

    def _vec(self, text: str) -> np.ndarray:
        v = self.VECTORS[text]
        return v / np.linalg.norm(v)

    def embed(self, text: str) -> _FakeResult:
        return _FakeResult(vector=self._vec(text))

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[_FakeResult]:
        return [_FakeResult(vector=self._vec(t)) for t in texts]


@pytest.fixture
def regulation_index() -> VectorIndex:
    idx = VectorIndex(name="regulation_chunks")
    idx._model = _FakeEmbeddingModel()
    idx.upsert_batch(
        ids=["docA::chunk0", "docB::chunk0", "docC::chunk0"],
        texts=[
            "ctr threshold reduced to five thousand",
            "mortgage closing disclosure timing",
            "reserve requirement ratio change",
        ],
        metadatas=[
            {
                "doc_id": "docA",
                "title": "FinCEN Advisory: CTR threshold update",
                "source_agency": "fincen",
                "chunk_index": 0,
                "section_header": "SECTION 1",
                "text": "ctr threshold reduced to five thousand",
            },
            {
                "doc_id": "docB",
                "title": "CFPB Rule: TRID timing",
                "source_agency": "cfpb",
                "chunk_index": 0,
                "section_header": "SECTION 1",
                "text": "mortgage closing disclosure timing",
            },
            {
                "doc_id": "docC",
                "title": "FRB Notice: Reserve requirements",
                "source_agency": "fed",
                "chunk_index": 0,
                "section_header": "SECTION 1",
                "text": "reserve requirement ratio change",
            },
        ],
    )
    return idx


def test_rrf_combine_ranks_items_present_in_both_lists_highest():
    dense_ranked = ["a", "b", "c"]
    bm25_ranked = ["b", "a", "c"]

    results = _rrf_combine(dense_ranked, bm25_ranked)
    ranked_ids = [r[0] for r in results]

    # "a" and "b" both appear near the top of both lists -> should rank above "c"
    assert ranked_ids[:2] == sorted(["a", "b"]) or set(ranked_ids[:2]) == {"a", "b"}
    assert ranked_ids[-1] == "c"


def test_rrf_combine_handles_items_missing_from_one_list():
    dense_ranked = ["a", "b", "c", "d", "e"]
    bm25_ranked = ["b", "x", "y"]  # "a" missing from BM25 results entirely

    results = _rrf_combine(dense_ranked, bm25_ranked)
    scores = dict(results)

    # "b" appears near the top of both lists -> higher score than "a" (dense-only, rank 1)
    assert scores["b"] > scores["a"]


def test_match_section_returns_best_matching_regulation(regulation_index: VectorIndex):
    matcher = HybridMatcher(regulation_index)

    matches = matcher.match_section("currency transaction report cash ten thousand dollars")

    assert len(matches) > 0
    assert matches[0]["regulation_doc_id"] == "docA"
    assert matches[0]["source_agency"] == "fincen"


def test_match_section_respects_matches_per_section_limit(regulation_index: VectorIndex):
    matcher = HybridMatcher(regulation_index)

    matches = matcher.match_section("currency transaction report cash ten thousand dollars")

    # Only 3 docs exist total, well under MATCHES_PER_SECTION
    assert len(matches) <= 5
    doc_ids = [m["regulation_doc_id"] for m in matches]
    assert len(doc_ids) == len(set(doc_ids))  # no duplicate documents


def test_merge_chunk_matches_keeps_best_score_per_chunk():
    # Same chunk ("a") scores higher in the second query's results -> merged
    # result should keep the higher rrf_score AND the higher dense_score,
    # even though they come from different queries.
    list1 = [("a", 0.5, 0.6), ("b", 0.4, 0.3)]
    list2 = [("a", 0.7, 0.9), ("c", 0.2, 0.1)]

    merged = HybridMatcher._merge_chunk_matches([list1, list2])
    merged_map = {chunk_id: (rrf, dense) for chunk_id, rrf, dense in merged}

    assert merged_map["a"] == (0.7, 0.9)
    assert merged_map["b"] == (0.4, 0.3)
    assert merged_map["c"] == (0.2, 0.1)
    # Result is re-sorted by rrf_score descending
    assert [c[0] for c in merged] == ["a", "b", "c"]


def test_match_section_multi_query_falls_back_to_single_query_with_no_named_regulations(
    regulation_index: VectorIndex, monkeypatch
):
    monkeypatch.setattr(matcher_module, "get_named_regulations", lambda policy_name: set())

    matcher = HybridMatcher(regulation_index)
    query = "currency transaction report cash ten thousand dollars"

    single = matcher.match_section(query)
    multi = matcher.match_section_multi_query(query, "Some-Policy")

    assert multi == single


def test_match_section_multi_query_issues_extra_query_per_named_regulation(
    regulation_index: VectorIndex, monkeypatch
):
    monkeypatch.setattr(matcher_module, "get_named_regulations", lambda policy_name: {"Bank Secrecy Act"})

    matcher = HybridMatcher(regulation_index)
    query = "currency transaction report cash ten thousand dollars"

    matches = matcher.match_section_multi_query(query, "BSA-AML-Policy")

    # Still returns valid, deduplicated, capped results
    assert len(matches) <= 5
    doc_ids = [m["regulation_doc_id"] for m in matches]
    assert len(doc_ids) == len(set(doc_ids))
    # The CTR-related document remains the top match across both queries
    assert matches[0]["regulation_doc_id"] == "docA"
