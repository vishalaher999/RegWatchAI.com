"""
Similarity matcher v1 for F3 — Policy Impact Mapping.

KM concept: #159-160 Hybrid search

For each policy section, finds the regulation chunks most likely to be
relevant, using the same hybrid approach F2 validated on Day 16:
  - Dense (mpnet embeddings via VectorIndex.query) — semantic similarity
  - BM25 (keyword/citation matching) — catches exact terms dense search
    can miss ("Regulation B", "12 CFR 1002.6")
  - RRF (Reciprocal Rank Fusion) — combines both ranked lists

Chunk-level matches are then collapsed to one row per (policy section,
regulation document) — Sarah cares about "which regulation", not "which
chunk of that regulation".

Output (matches.json) feeds:
  - Day 25: impact classifier (High/Med/Low/N/A) scores each match
  - Day 26: eval set labels the top-5 matches per section for precision@5
"""

import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from src.f3_impact.citations import get_named_regulations
from src.f3_impact.vectorstore import VectorIndex

INDEX_DIR = Path(__file__).resolve().parents[2] / "data" / "f3_indexes"

RRF_K = 60              # Same constant F2 validated on Day 16
DENSE_TOP_K = 20        # Dense candidates per policy section
BM25_TOP_K = 20         # BM25 candidates per policy section
CHUNK_TOP_K = 15        # Chunk-level matches kept after RRF
MATCHES_PER_SECTION = 5  # Final regulation matches per policy section


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokenization for BM25."""
    return re.findall(r"\w+", text.lower())


def _rrf_combine(
    dense_ranked: list[str],
    bm25_ranked: list[str],
    k: int = RRF_K,
) -> list[tuple[str, float]]:
    """
    Combine two ranked lists of ids using Reciprocal Rank Fusion.

    RRF_score(id) = 1/(k + rank_dense) + 1/(k + rank_bm25)
    An id missing from one list gets a rank of len(list)+1 in that list
    (worst-case penalty, not zero — avoids over-rewarding single-method hits).
    """
    dense_pos = {item_id: rank + 1 for rank, item_id in enumerate(dense_ranked)}
    bm25_pos = {item_id: rank + 1 for rank, item_id in enumerate(bm25_ranked)}

    all_ids = set(dense_pos) | set(bm25_pos)
    n_dense = len(dense_ranked)
    n_bm25 = len(bm25_ranked)

    rrf_scores: dict[str, float] = {}
    for item_id in all_ids:
        d_rank = dense_pos.get(item_id, n_dense + 1)
        b_rank = bm25_pos.get(item_id, n_bm25 + 1)
        rrf_scores[item_id] = 1.0 / (k + d_rank) + 1.0 / (k + b_rank)

    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)


class HybridMatcher:
    """
    Hybrid (dense + BM25) matcher over a regulation chunk VectorIndex.

    Builds a BM25 index once over all chunks in `regulation_index`, then
    matches arbitrary query texts (policy section text) against it.
    """

    def __init__(self, regulation_index: VectorIndex):
        self.regulation_index = regulation_index
        self._bm25 = BM25Okapi([_tokenize(m["text"]) for m in regulation_index.metadata])

    def match_chunks(self, query_text: str) -> list[tuple[str, float]]:
        """Return top CHUNK_TOP_K (chunk_id, rrf_score, dense_score) tuples for query_text."""
        dense_results = self.regulation_index.query(query_text, top_k=DENSE_TOP_K)
        dense_ranked = [r["id"] for r in dense_results]
        dense_score_map = {r["id"]: r["score"] for r in dense_results}

        bm25_scores = self._bm25.get_scores(_tokenize(query_text))
        bm25_order = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)
        bm25_ranked = [self.regulation_index.ids[i] for i in bm25_order[:BM25_TOP_K]]

        rrf_ranked = _rrf_combine(dense_ranked, bm25_ranked)
        return [
            (chunk_id, rrf_score, dense_score_map.get(chunk_id, 0.0))
            for chunk_id, rrf_score in rrf_ranked[:CHUNK_TOP_K]
        ]

    def match_section(self, query_text: str) -> list[dict]:
        """
        Return up to MATCHES_PER_SECTION regulation-level matches for query_text.

        Collapses chunk-level RRF results to one entry per regulation
        document (max RRF score, best chunk kept as evidence). Each result
        also carries `dense_score` (cosine similarity) — used by Day 25's
        classifier, which has more dynamic range than the RRF score.
        """
        return self._collapse_to_docs(self.match_chunks(query_text))

    def match_section_multi_query(self, query_text: str, policy_name: str) -> list[dict]:
        """
        Multi-query variant of match_section — Day 30, KM #164.

        A single embedding of a policy section's full text averages together
        every regulation it touches, diluting sections that reference
        multiple regulatory frameworks ("...per BSA and Regulation B
        requirements"). For each regulation the policy itself names
        (citations.py), this runs an ADDITIONAL query — query_text plus that
        regulation's name — so each cited regulation gets its own dedicated
        retrieval pass. Results across all queries are merged by best score
        per chunk before collapsing to per-document matches.

        Policies that cite no recognizable regulations (citations.py finds
        nothing) fall back to exactly one query — identical to
        match_section().
        """
        queries = [query_text]
        for reg_name in sorted(get_named_regulations(policy_name)):
            queries.append(f"{query_text}\n{reg_name}")

        all_chunk_matches = [self.match_chunks(q) for q in queries]
        merged = self._merge_chunk_matches(all_chunk_matches)
        return self._collapse_to_docs(merged)

    @staticmethod
    def _merge_chunk_matches(
        chunk_match_lists: list[list[tuple[str, float, float]]],
    ) -> list[tuple[str, float, float]]:
        """
        Merge multiple match_chunks() result lists into one, keeping the best
        (max) RRF score and dense_score seen for each chunk across all
        queries. Re-sorted and truncated to CHUNK_TOP_K.
        """
        best: dict[str, tuple[float, float]] = {}
        for chunk_matches in chunk_match_lists:
            for chunk_id, rrf_score, dense_score in chunk_matches:
                prev = best.get(chunk_id)
                if prev is None or rrf_score > prev[0]:
                    best[chunk_id] = (rrf_score, max(dense_score, prev[1] if prev else 0.0))
                elif dense_score > prev[1]:
                    best[chunk_id] = (prev[0], dense_score)

        merged = [(chunk_id, rrf_score, dense_score) for chunk_id, (rrf_score, dense_score) in best.items()]
        merged.sort(key=lambda x: x[1], reverse=True)
        return merged[:CHUNK_TOP_K]

    def _collapse_to_docs(self, chunk_matches: list[tuple[str, float, float]]) -> list[dict]:
        """Collapse chunk-level (chunk_id, rrf_score, dense_score) matches to one entry per regulation document."""
        id_to_metadata = dict(zip(self.regulation_index.ids, self.regulation_index.metadata))

        by_doc: dict[str, dict] = {}
        for chunk_id, score, dense_score in chunk_matches:
            meta = id_to_metadata[chunk_id]
            doc_id = meta["doc_id"]
            if doc_id not in by_doc or score > by_doc[doc_id]["score"]:
                by_doc[doc_id] = {
                    "regulation_doc_id": doc_id,
                    "regulation_title": meta["title"],
                    "source_agency": meta["source_agency"],
                    "score": score,
                    "dense_score": dense_score,
                    "matched_chunk_text": meta["text"],
                    "matched_chunk_section_header": meta["section_header"],
                }

        ranked_docs = sorted(by_doc.values(), key=lambda d: d["score"], reverse=True)
        return ranked_docs[:MATCHES_PER_SECTION]


def build_matches() -> list[dict]:
    """
    For every policy section, find its top regulation matches.

    Returns a list of dicts (one per policy section):
        {policy_name, section_id, section_title, parent_section, matches: [...]}
    """
    policy_index = VectorIndex.load(INDEX_DIR, "policy_sections")
    regulation_index = VectorIndex.load(INDEX_DIR, "regulation_chunks")

    matcher = HybridMatcher(regulation_index)

    results = []
    for meta in policy_index.metadata:
        query_text = f"{meta['section_title']}\n{meta['text']}"
        results.append(
            {
                "policy_name": meta["policy_name"],
                "section_id": meta["section_id"],
                "section_title": meta["section_title"],
                "parent_section": meta["parent_section"],
                "matches": matcher.match_section_multi_query(query_text, meta["policy_name"]),
            }
        )
    return results


def main() -> None:
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    results = build_matches()

    out_path = INDEX_DIR / "matches.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    total_matches = sum(len(r["matches"]) for r in results)
    print(f"{len(results)} policy sections processed, {total_matches} regulation matches found")
    print(f"Saved to {out_path}")

    print("\nSample (first 3 sections with at least one match):")
    shown = 0
    for r in results:
        if not r["matches"]:
            continue
        print(f"\n{r['policy_name']} §{r['section_id']} - {r['section_title']}")
        for m in r["matches"][:2]:
            print(f"  {m['score']:.4f}  [{m['source_agency']}] {m['regulation_title'][:70]}")
        shown += 1
        if shown >= 3:
            break


if __name__ == "__main__":
    main()
