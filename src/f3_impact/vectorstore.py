"""
Local vector store for F3 — Policy Impact Mapping.

KM concept: #157 Dense retrieval

Provides a small `VectorIndex` class with the same shape as a Pinecone
index (`upsert`, `query`, persisted collection of vectors + metadata) but
backed by numpy + JSON on local disk. No API key, no network call, no cost.

Why local instead of real Pinecone:
  CLAUDE.md lists Pinecone as the target stack, but no PINECONE_API_KEY is
  configured in .env. F2 already established the precedent (embeddings.py):
  local sentence-transformers embeddings are zero-cost, zero-latency for
  batch jobs, and keep compliance document content off third-party servers
  during development.

  The interface here (`upsert`, `query`, `save`, `load`) mirrors what a
  Pinecone-backed index would expose. Swapping to real Pinecone later means
  rewriting this one file, not the code that calls it — same pattern as
  DATABASE_URL for SQLite -> Postgres.

Dual-index usage (Day 23):
  - One VectorIndex for policy sections (from src/f3_impact/extractor.py)
  - One VectorIndex for regulation chunks (from src/f2_summarise/chunker.py)
  Kept separate so Day 24's matcher can search "regulations similar to
  this policy section" without policy-to-policy matches polluting results.
"""

import json
from pathlib import Path

import numpy as np

from src.f2_summarise.embeddings import get_model, DEFAULT_EMBEDDING_MODEL


class VectorIndex:
    """
    A named collection of (id, vector, metadata) items with cosine-similarity
    search. Vectors are normalized on insert, so cosine similarity = dot product.
    """

    def __init__(self, name: str, model_name: str = DEFAULT_EMBEDDING_MODEL):
        self.name = name
        self.model_name = model_name
        self._model = get_model(model_name)
        self.ids: list[str] = []
        self.metadata: list[dict] = []
        self.vectors: np.ndarray | None = None  # shape: (n_items, dim)

    def upsert_batch(self, ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
        """Embed a batch of texts and add them to the index."""
        if not (len(ids) == len(texts) == len(metadatas)):
            raise ValueError("ids, texts, and metadatas must be the same length")

        results = self._model.embed_batch(texts)
        new_vectors = np.stack([r.vector for r in results])

        if self.vectors is None:
            self.vectors = new_vectors
        else:
            self.vectors = np.vstack([self.vectors, new_vectors])

        self.ids.extend(ids)
        self.metadata.extend(metadatas)

    def query(self, text: str, top_k: int = 5) -> list[dict]:
        """
        Return the top_k most similar items to `text`, sorted by score descending.
        Each result: {"id": ..., "score": float, "metadata": {...}}
        """
        if self.vectors is None or len(self.ids) == 0:
            return []

        query_vector = self._model.embed(text).vector
        scores = self.vectors @ query_vector  # cosine similarity (vectors are normalized)

        top_k = min(top_k, len(self.ids))
        top_indices = np.argsort(scores)[::-1][:top_k]

        return [
            {"id": self.ids[i], "score": float(scores[i]), "metadata": self.metadata[i]}
            for i in top_indices
        ]

    def __len__(self) -> int:
        return len(self.ids)

    def save(self, directory: str | Path) -> None:
        """Persist this index to `directory/<name>.npz` and `<name>.json`."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        if self.vectors is not None:
            np.savez_compressed(directory / f"{self.name}.npz", vectors=self.vectors)

        with open(directory / f"{self.name}.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "name": self.name,
                    "model_name": self.model_name,
                    "ids": self.ids,
                    "metadata": self.metadata,
                },
                f,
                indent=2,
            )

    @classmethod
    def load(cls, directory: str | Path, name: str) -> "VectorIndex":
        """Load a previously saved index from `directory/<name>.npz` and `<name>.json`."""
        directory = Path(directory)

        with open(directory / f"{name}.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        index = cls(name=data["name"], model_name=data["model_name"])
        index.ids = data["ids"]
        index.metadata = data["metadata"]

        npz_path = directory / f"{name}.npz"
        if npz_path.exists():
            index.vectors = np.load(npz_path)["vectors"]

        return index
