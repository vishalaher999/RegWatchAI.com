"""
Cross-encoder reranker for F2 — Day 17.

KM concept: #162 Reranking

Sits between hybrid retrieval and Claude. Takes the top-N candidates
from hybrid search and reranks them to find the best-K to send to Claude.

Pipeline after Day 17:
  470 chunks
    → BM25 top-50 candidates        (fast, free, exact term match)
    → Dense embedding top-15        (semantic similarity, moderate cost)
    → Cross-encoder rerank → top-8  (precise relevance, slow but only 15 inputs)
    → Claude                        (summarisation)

Why a reranker after hybrid search?
  Bi-encoders (used in Days 15-16) encode query and chunk SEPARATELY.
  The model never sees both texts together — it scores them independently.
  This is fast but approximate.

  Cross-encoders encode query+chunk TOGETHER. The model's attention layers
  read every word of the query while reading every word of the chunk.
  It models interactions ("effective date" in query ↔ "takes effect on" in chunk).
  Much more accurate but O(n) in candidates — must pre-filter to a small set.

  Solution: hybrid gives us top-15 candidates fast; cross-encoder picks
  the best 8 from those 15 precisely. Best of both worlds.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  - Trained on MS MARCO passage ranking dataset (140M query-passage pairs)
  - Small and fast (6 transformer layers)
  - Outputs a relevance score (higher = more relevant)
  - Downloaded once, runs locally (no API cost)
"""

import time
from dataclasses import dataclass
from typing import Optional

from src.f2_summarise.chunker import Chunk

# Reranking configuration
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_TOP_K = 8          # Final chunks passed to Claude after reranking
RERANK_CANDIDATE_K = 15   # Candidates fed into reranker from hybrid search

# Compliance-focused query for reranking
# The cross-encoder reads this alongside each chunk to score relevance
RERANK_QUERY = (
    "What is the effective date, compliance deadline, and which financial institutions "
    "(community banks, credit unions, national banks) are required to comply? "
    "What specifically changed from previous requirements? What must compliance officers do?"
)


@dataclass
class RerankedChunk:
    """A chunk with its cross-encoder relevance score attached."""
    chunk: Chunk
    rerank_score: float
    original_rank: int   # Position before reranking (from hybrid retrieval)


class CrossEncoderReranker:
    """
    Wrapper around a sentence-transformers CrossEncoder model.
    Lazy-loads on first use.
    """

    def __init__(self, model_name: str = RERANKER_MODEL):
        self.model_name = model_name
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import CrossEncoder
        print(f"  [loading reranker] {self.model_name}...")
        t0 = time.time()
        self._model = CrossEncoder(self.model_name)
        print(f"  [loaded reranker] {self.model_name} in {time.time()-t0:.1f}s")

    def rerank(
        self,
        query: str,
        chunks: list[Chunk],
        top_k: int = RERANK_TOP_K,
    ) -> list[RerankedChunk]:
        """
        Score each (query, chunk) pair and return top_k by relevance.

        Args:
            query:   The compliance question being answered.
            chunks:  Candidate chunks from hybrid retrieval (typically 15).
            top_k:   How many to return after reranking.

        Returns:
            Top-k RerankedChunk objects sorted by relevance descending,
            then re-sorted by document position for coherent reading order.
        """
        if not chunks:
            return []

        self._load()

        # Build (query, passage) pairs for the cross-encoder
        pairs = [(query, chunk.text) for chunk in chunks]

        t0 = time.time()
        scores = self._model.predict(pairs)
        elapsed = time.time() - t0

        # Pair each chunk with its score and original position
        scored = [
            RerankedChunk(chunk=chunk, rerank_score=float(score), original_rank=i)
            for i, (chunk, score) in enumerate(zip(chunks, scores))
        ]

        # Sort by relevance score (descending)
        scored.sort(key=lambda r: r.rerank_score, reverse=True)

        # Take top-k
        top = scored[:top_k]

        # Re-sort by document position for coherent reading order
        top.sort(key=lambda r: r.chunk.index)

        return top


# ── Singleton reranker ────────────────────────────────────────────────────────
# One instance shared across all summarisation calls to avoid repeated model loading.
_reranker: Optional[CrossEncoderReranker] = None


def get_reranker() -> CrossEncoderReranker:
    """Return the shared reranker instance (loads model on first call)."""
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker


def rerank_chunks(
    chunks: list[Chunk],
    query: str = RERANK_QUERY,
    top_k: int = RERANK_TOP_K,
) -> list[Chunk]:
    """
    Convenience function: rerank a list of chunks and return plain Chunk objects.
    Used by the summariser to drop-in replace the retrieval output.
    """
    reranker = get_reranker()
    reranked = reranker.rerank(query, chunks, top_k=top_k)
    return [r.chunk for r in reranked]
