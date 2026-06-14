"""
Embedding model wrapper for F2 — Day 15.

KM concept: #156 Embeddings

Wraps sentence-transformers models with a consistent interface.
Used by:
  - benchmark_embeddings.py (Day 15) — finding the best model
  - retriever.py (Day 16) — replacing keyword scoring with dense retrieval
  - hybrid search (Day 16) — combined with BM25

Why sentence-transformers over OpenAI embeddings?
  - Zero cost — runs locally, no API calls, no rate limits
  - Zero latency penalty for batch embedding (process all chunks at once)
  - No data leaves your machine — important for compliance document content
  - Three models benchmarked to find best for regulatory text

Models being benchmarked:
  1. all-MiniLM-L6-v2   — fastest, smallest (22M params), good general-purpose
  2. all-mpnet-base-v2  — best quality in sentence-transformers family (110M params)
  3. bge-small-en-v1.5  — BAAI model, optimised specifically for retrieval tasks

How embeddings work:
  text → neural network → list of N floats (the "vector" or "embedding")
  Similar meaning → similar vectors → low cosine distance
  "Banks must comply by January 2027" ≈ "Institutions required to implement by Q1 2027"
  even though they share zero keywords.
"""

import time
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class EmbeddingResult:
    """One embedded text item."""
    text: str
    vector: np.ndarray      # shape: (embedding_dim,)
    model_name: str
    embed_time_ms: float    # milliseconds to embed this text


class EmbeddingModel:
    """
    Wrapper around a sentence-transformers model.
    Lazy-loads the model on first use to avoid startup cost.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None          # Loaded on first embed() call
        self._dim: Optional[int] = None

    def _load(self) -> None:
        """Load the model weights. Called once on first embed()."""
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer
        print(f"  [loading] {self.model_name}...")
        t0 = time.time()
        self._model = SentenceTransformer(self.model_name)
        self._dim = self._model.get_sentence_embedding_dimension()
        print(f"  [loaded]  {self.model_name} ({self._dim}d) in {time.time()-t0:.1f}s")

    def embed(self, text: str) -> EmbeddingResult:
        """Embed a single text string."""
        self._load()
        t0 = time.time()
        vector = self._model.encode(text, normalize_embeddings=True)
        elapsed_ms = (time.time() - t0) * 1000
        return EmbeddingResult(
            text=text,
            vector=vector,
            model_name=self.model_name,
            embed_time_ms=elapsed_ms,
        )

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[EmbeddingResult]:
        """
        Embed a list of texts efficiently using batch processing.
        Batch processing is much faster than one-at-a-time for many texts.
        """
        self._load()
        t0 = time.time()
        vectors = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        total_ms = (time.time() - t0) * 1000
        per_ms = total_ms / len(texts) if texts else 0

        return [
            EmbeddingResult(
                text=text,
                vector=vector,
                model_name=self.model_name,
                embed_time_ms=per_ms,
            )
            for text, vector in zip(texts, vectors)
        ]

    @property
    def dim(self) -> int:
        self._load()
        return self._dim


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity between two normalized vectors.
    Range: -1 (opposite) to 1 (identical). For normalized vectors: dot product.
    We normalize in embed(), so this is just a dot product.
    """
    return float(np.dot(a, b))


def rank_chunks_by_similarity(
    query_vector: np.ndarray,
    chunk_vectors: list[np.ndarray],
    top_k: int = 6,
) -> list[tuple[int, float]]:
    """
    Return top-k (chunk_index, similarity_score) pairs, sorted by similarity descending.
    Replaces keyword scoring in the retriever when using dense embeddings.
    """
    scores = [(i, cosine_similarity(query_vector, cv)) for i, cv in enumerate(chunk_vectors)]
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]


# ── Model registry ─────────────────────────────────────────────────────────────

BENCHMARK_MODELS = {
    "minilm": "all-MiniLM-L6-v2",
    "mpnet":  "all-mpnet-base-v2",
    "bge":    "BAAI/bge-small-en-v1.5",
}

# Default model (set after benchmark — updated Day 16)
# Day 15 benchmark winner: all-mpnet-base-v2 scored 0.690 composite P@3
# vs bge-small 0.638 and all-MiniLM 0.599.
# Key win: effective_date P@3 = 0.845 (best for compliance deadline retrieval).
DEFAULT_EMBEDDING_MODEL = "all-mpnet-base-v2"


def get_model(name: str = DEFAULT_EMBEDDING_MODEL) -> EmbeddingModel:
    """Return an EmbeddingModel instance for the given model name."""
    return EmbeddingModel(name)
