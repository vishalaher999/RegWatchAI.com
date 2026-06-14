"""
Tests for src/f3_impact/vectorstore.py.

Uses a fake embedding model (no sentence-transformers download) so these
tests stay fast. The fake model maps each text to a hand-picked 3D vector
so similarity rankings are predictable.
"""

from dataclasses import dataclass

import numpy as np
import pytest

from src.f3_impact.vectorstore import VectorIndex


@dataclass
class _FakeResult:
    vector: np.ndarray


class _FakeEmbeddingModel:
    """Maps known text strings to hand-picked normalized 3D vectors."""

    VECTORS = {
        "apple": np.array([1.0, 0.0, 0.0]),
        "fruit": np.array([0.9, 0.1, 0.0]),
        "banana": np.array([0.8, 0.2, 0.0]),
        "car": np.array([0.0, 0.0, 1.0]),
        "vehicle": np.array([0.0, 0.1, 0.9]),
    }

    def _vec(self, text: str) -> np.ndarray:
        v = self.VECTORS[text]
        return v / np.linalg.norm(v)

    def embed(self, text: str) -> _FakeResult:
        return _FakeResult(vector=self._vec(text))

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[_FakeResult]:
        return [_FakeResult(vector=self._vec(t)) for t in texts]


@pytest.fixture
def index() -> VectorIndex:
    idx = VectorIndex(name="test_index")
    idx._model = _FakeEmbeddingModel()
    return idx


def test_upsert_and_query_ranks_by_similarity(index: VectorIndex):
    index.upsert_batch(
        ids=["a", "b", "c"],
        texts=["apple", "banana", "car"],
        metadatas=[{"label": "apple"}, {"label": "banana"}, {"label": "car"}],
    )

    results = index.query("fruit", top_k=2)

    assert len(results) == 2
    # "apple" and "banana" are closer to "fruit" than "car" is
    result_ids = [r["id"] for r in results]
    assert "c" not in result_ids
    assert results[0]["score"] >= results[1]["score"]


def test_upsert_mismatched_lengths_raises(index: VectorIndex):
    with pytest.raises(ValueError):
        index.upsert_batch(ids=["a"], texts=["apple", "banana"], metadatas=[{}])


def test_query_on_empty_index_returns_empty_list(index: VectorIndex):
    assert index.query("apple") == []


def test_len_reflects_item_count(index: VectorIndex):
    assert len(index) == 0
    index.upsert_batch(ids=["a"], texts=["apple"], metadatas=[{"label": "apple"}])
    assert len(index) == 1


def test_save_and_load_round_trip(index: VectorIndex, tmp_path):
    index.upsert_batch(
        ids=["a", "b"],
        texts=["apple", "car"],
        metadatas=[{"label": "apple"}, {"label": "car"}],
    )
    index.save(tmp_path)

    loaded = VectorIndex.load(tmp_path, "test_index")

    assert loaded.name == "test_index"
    assert loaded.ids == ["a", "b"]
    assert loaded.metadata == [{"label": "apple"}, {"label": "car"}]
    assert loaded.vectors is not None
    assert loaded.vectors.shape == (2, 3)

    # Loaded index can query without re-running embed_batch (vectors persisted)
    loaded._model = _FakeEmbeddingModel()
    results = loaded.query("vehicle", top_k=1)
    assert results[0]["id"] == "b"
