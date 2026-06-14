"""
Chunk retriever for F2.

Day 8:  Keyword frequency scoring (TF-IDF-inspired, no embeddings).
Day 15: Dense embedding retrieval benchmarked — all-mpnet-base-v2 wins.
Day 16: Hybrid search = dense (mpnet) + BM25 sparse, combined with RRF.

How each retriever works:
  Dense (embeddings): encode query and chunks as vectors, rank by cosine similarity.
    Finds semantically similar content even with different wording.
    Best for: "When does this take effect?" → finds date sections regardless of phrasing.

  Sparse (BM25): TF-IDF-like keyword matching with term frequency normalisation.
    Best for: exact regulatory citations ("12 CFR Part 1002", "Regulation B § 1002.6").

  Hybrid (RRF): Reciprocal Rank Fusion combines both ranked lists.
    RRF_score = 1/(k + rank_dense) + 1/(k + rank_bm25)
    Chunks ranked high by BOTH get the biggest boost.
    k=60 is the empirically validated constant from the original RRF paper.

Why not embeddings on Day 8?
  Embeddings require either a local model (GPU/RAM overhead) or an
  embedding API call (cost + latency per chunk). For a 400K doc with
  400 chunks, that's 400 API calls just to retrieve. Keyword scoring
  costs nothing and works in microseconds. Day 15 benchmarks whether
  embeddings are worth the cost — for now, keywords are the baseline.
"""

import re
from src.f2_summarise.chunker import Chunk

TOP_K_DEFAULT = 6  # Chunks passed to Claude per summary call

# Keywords that signal compliance-relevant content.
# Grouped by what summary field they help populate.
FIELD_KEYWORDS: dict[str, list[str]] = {
    "dates": [
        "effective date", "effective", "compliance date", "compliance deadline",
        "deadline", "by", "no later than", "takes effect", "enacted",
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
        "2024", "2025", "2026", "2027", "2028",
    ],
    "what_changed": [
        "amend", "amendment", "revise", "revision", "update", "change",
        "modify", "modification", "repeal", "remove", "add", "new requirement",
        "final rule", "proposed rule", "rulemaking", "regulation",
        "replace", "supersede", "new",
    ],
    "institution_types": [
        "community bank", "credit union", "bank", "institution",
        "financial institution", "lender", "servicer", "national bank",
        "state bank", "thrift", "holding company", "fdic", "ncua",
        "federal reserve", "occ", "cfpb", "fincen", "federally insured",
        "assets", "billion", "million",
    ],
    "compliance_action": [
        "must", "shall", "required", "requirement", "comply", "compliance",
        "obligation", "prohibit", "prohibited", "violation", "penalty",
        "civil money penalty", "enforcement", "examiner", "examination",
        "implement", "implementation", "procedure", "policy",
    ],
    "why_it_matters": [
        "risk", "consumer", "protection", "safety", "soundness",
        "capital", "liquidity", "disclosure", "notice", "report",
        "bsa", "aml", "anti-money laundering", "fair lending",
        "truth in lending", "trid", "hmda", "cra", "dodd-frank",
    ],
}

# Flatten all keywords into one list for quick scoring
ALL_KEYWORDS = [kw for kws in FIELD_KEYWORDS.values() for kw in kws]


def _score_chunk(chunk: Chunk) -> float:
    """
    Score a chunk by counting compliance keyword matches.
    Case-insensitive. Partial matches count (e.g. 'amend' matches 'amending').
    Returns a float score — higher = more relevant.
    """
    text_lower = chunk.text.lower()
    score = 0.0

    for keyword in ALL_KEYWORDS:
        # Count occurrences — repeated keywords signal high relevance
        count = text_lower.count(keyword)
        if count > 0:
            # Weight by keyword length — longer phrases are more specific
            weight = len(keyword.split()) * 0.5
            score += count * (1.0 + weight)

    # Bonus: chunks with numbers and year-like patterns likely contain dates
    year_matches = re.findall(r'\b(202[4-9]|203[0-9])\b', chunk.text)
    score += len(year_matches) * 2.0

    # Bonus: chunks with section references likely contain structured content
    section_matches = re.findall(r'§\s*\d+|\bsection\s+\d+|\bpart\s+\d+', text_lower)
    score += len(section_matches) * 1.5

    return score


def retrieve_top_chunks(chunks: list[Chunk], top_k: int = TOP_K_DEFAULT) -> list[Chunk]:
    """
    Score all chunks and return the top-k most relevant ones.

    For HierarchicalChunk objects, apply priority boosts:
      - is_date_section=True    → +50 score (always retrieve date sections)
      - is_institution_section  → +30 score (always retrieve institution sections)
      - is_table=True           → +20 score (tables are usually information-dense)

    This ensures compliance-critical sections are retrieved even when
    their prose content uses different terminology than our keyword list.

    The returned chunks are sorted by their original document position
    (not by score) so Claude receives them in reading order.
    """
    if not chunks:
        return []

    from src.f2_summarise.chunker import HierarchicalChunk

    def score_with_priority(chunk: Chunk) -> float:
        base = _score_chunk(chunk)
        if isinstance(chunk, HierarchicalChunk):
            if chunk.is_date_section:
                base += 50.0   # Always retrieve date sections
            if chunk.is_institution_section:
                base += 30.0   # Always retrieve institution sections
            if chunk.is_table:
                base += 20.0   # Tables are information-dense
        return base

    scored = [(chunk, score_with_priority(chunk)) for chunk in chunks]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Select top-k by score
    top = [chunk for chunk, score in scored[:top_k]]

    # Always include first chunk (doc header) and last chunk (often has dates)
    if chunks[0] not in top:
        top.append(chunks[0])
    if len(chunks) > 1 and chunks[-1] not in top:
        top.append(chunks[-1])

    # Sort selected chunks by document position for coherent reading order
    top.sort(key=lambda c: c.index)

    return top


# ── Hybrid retrieval (Day 16) ──────────────────────────────────────────────────

RRF_K = 60           # RRF smoothing constant (standard value from original paper)
HYBRID_TOP_K = 8     # Final chunks passed to Claude (without reranker)
BM25_PREFILTER_K = 50  # BM25 pre-filter before dense embedding (Day 17 optimisation)
DENSE_CANDIDATE_K = 15  # Dense embedding candidate set → fed to cross-encoder reranker

# Compliance-specific queries for dense retrieval
# These represent the summariser's implicit information needs
COMPLIANCE_QUERIES = [
    "What is the effective date and when does this rule take effect?",
    "What compliance deadline must institutions meet?",
    "Which financial institutions are subject to this rule?",
    "What changed from the previous requirement?",
    "What are the compliance obligations and required actions?",
]


def _bm25_rank(chunks: list[Chunk]) -> list[tuple[int, float]]:
    """
    Rank chunks using BM25. Returns (chunk_index, score) sorted descending.

    BM25 tokenises each chunk and scores them against a combined query
    of all compliance-relevant terms. Good at finding exact regulatory citations.
    """
    from rank_bm25 import BM25Okapi

    # Simple whitespace tokenisation + lowercase
    tokenised = [c.text.lower().split() for c in chunks]
    if not any(tokenised):
        return [(i, 0.0) for i in range(len(chunks))]

    bm25 = BM25Okapi(tokenised)

    # Query = union of all compliance query terms
    query_tokens = " ".join(COMPLIANCE_QUERIES).lower().split()
    scores = bm25.get_scores(query_tokens)

    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return ranked


def _dense_rank(
    chunks: list[Chunk],
    model_name: str | None = None,
) -> list[tuple[int, float]]:
    """
    Rank chunks using dense embeddings. Returns (chunk_index, similarity) sorted descending.

    Encodes all compliance queries as a single averaged query vector,
    then ranks chunks by cosine similarity.
    """
    try:
        from src.f2_summarise.embeddings import EmbeddingModel, DEFAULT_EMBEDDING_MODEL, cosine_similarity
        model = EmbeddingModel(model_name or DEFAULT_EMBEDDING_MODEL)

        chunk_texts = [c.text for c in chunks]
        chunk_embeddings = model.embed_batch(chunk_texts)
        chunk_vectors = [e.vector for e in chunk_embeddings]

        # Average of all compliance queries = the "ideal" regulatory chunk
        query_embeddings = model.embed_batch(COMPLIANCE_QUERIES)
        import numpy as np
        avg_query_vector = np.mean([e.vector for e in query_embeddings], axis=0)

        scored = [(i, cosine_similarity(avg_query_vector, cv))
                  for i, cv in enumerate(chunk_vectors)]
        ranked = sorted(scored, key=lambda x: x[1], reverse=True)
        return ranked

    except Exception:
        # Fallback: keyword scoring if embeddings unavailable
        scored = [(i, _score_chunk(c)) for i, c in enumerate(chunks)]
        return sorted(scored, key=lambda x: x[1], reverse=True)


def _rrf_combine(
    dense_ranked: list[tuple[int, float]],
    bm25_ranked: list[tuple[int, float]],
    k: int = RRF_K,
) -> list[tuple[int, float]]:
    """
    Reciprocal Rank Fusion: combine two ranked lists into one.

    RRF_score(chunk) = 1/(k + rank_dense) + 1/(k + rank_bm25)

    where rank is 1-based position in each ranked list.

    Chunks ranked highly by BOTH methods get the biggest combined score.
    Chunks ranked highly by only one get a partial boost.
    """
    # Build rank position maps (1-indexed)
    dense_pos = {chunk_idx: pos + 1 for pos, (chunk_idx, _) in enumerate(dense_ranked)}
    bm25_pos  = {chunk_idx: pos + 1 for pos, (chunk_idx, _) in enumerate(bm25_ranked)}

    # All unique chunk indices
    all_indices = set(dense_pos) | set(bm25_pos)
    n = len(all_indices)

    rrf_scores: dict[int, float] = {}
    for idx in all_indices:
        d_rank = dense_pos.get(idx, n + 1)  # Default: last place if missing
        b_rank = bm25_pos.get(idx, n + 1)
        rrf_scores[idx] = 1.0 / (k + d_rank) + 1.0 / (k + b_rank)

    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)


def hybrid_retrieve(
    chunks: list[Chunk],
    top_k: int = HYBRID_TOP_K,
    model_name: str | None = None,
) -> list[Chunk]:
    """
    Hybrid retrieval: dense embeddings + BM25, combined with RRF.

    Steps:
      1. Rank all chunks with BM25 (keyword matching)
      2. Rank all chunks with dense embeddings (semantic similarity)
      3. Combine rankings with RRF
      4. Apply HierarchicalChunk priority boosts (date/institution sections)
      5. Always include first and last chunks
      6. Sort result by document position for coherent reading order

    Falls back to pure keyword scoring if sentence-transformers unavailable.
    """
    if not chunks:
        return []

    # For very short documents (< 4 chunks), keyword scoring is sufficient
    if len(chunks) < 4:
        return retrieve_top_chunks(chunks, top_k)

    from src.f2_summarise.chunker import HierarchicalChunk

    # Step 1 & 2: Get rankings from both methods
    bm25_ranked  = _bm25_rank(chunks)
    dense_ranked = _dense_rank(chunks, model_name)

    # Step 3: RRF combination
    rrf_ranked = _rrf_combine(dense_ranked, bm25_ranked)

    # Step 4: Apply HierarchicalChunk priority boosts
    # Date and institution sections get an extra boost to their RRF score
    PRIORITY_BOOST = 0.05   # Adds ~3 rank positions worth of score
    boosted = []
    for chunk_idx, rrf_score in rrf_ranked:
        chunk = chunks[chunk_idx]
        boost = 0.0
        if isinstance(chunk, HierarchicalChunk):
            if chunk.is_date_section:
                boost += PRIORITY_BOOST * 2
            if chunk.is_institution_section:
                boost += PRIORITY_BOOST
            if chunk.is_table:
                boost += PRIORITY_BOOST * 0.5
        boosted.append((chunk_idx, rrf_score + boost))

    boosted.sort(key=lambda x: x[1], reverse=True)
    selected_indices = {idx for idx, _ in boosted[:top_k]}

    # Step 5: Always include first and last chunks
    if 0 not in selected_indices:
        selected_indices.add(0)
    if len(chunks) - 1 not in selected_indices:
        selected_indices.add(len(chunks) - 1)

    # Step 6: Return in document order
    result = [chunks[i] for i in sorted(selected_indices)]
    return result


def retrieve_for_reranking(
    chunks: list[Chunk],
    candidate_k: int = DENSE_CANDIDATE_K,
    model_name: str | None = None,
) -> list[Chunk]:
    """
    Optimised retrieval pipeline for use WITH a cross-encoder reranker.

    Day 17 fix for the 261-second problem:
      OLD: dense embed ALL 470 chunks → top-8 by similarity
      NEW: BM25 top-50 → dense embed only those 50 → RRF top-15 candidates

    The cross-encoder reranker then picks the best 8 from the 15 candidates.
    Total embedding calls: 50 (not 470). Expected speedup: ~8x.

    Args:
        chunks:      All document chunks (e.g. 470 for CFPB Reg B).
        candidate_k: How many candidates to return for the reranker.
        model_name:  Embedding model to use.

    Returns:
        Top-candidate_k chunks (not yet reranked — reranker does that).
    """
    if not chunks:
        return []

    if len(chunks) <= candidate_k:
        # Small document — no pre-filtering needed
        return chunks

    # Step 1: BM25 pre-filter to top-50 (fast, free)
    bm25_top_indices = {idx for idx, _ in _bm25_rank(chunks)[:BM25_PREFILTER_K]}
    bm25_candidates = [c for i, c in enumerate(chunks) if i in bm25_top_indices]

    # Always include first and last chunks in BM25 candidate set
    if chunks[0] not in bm25_candidates:
        bm25_candidates.insert(0, chunks[0])
    if chunks[-1] not in bm25_candidates:
        bm25_candidates.append(chunks[-1])

    if len(bm25_candidates) <= candidate_k:
        return bm25_candidates

    # Step 2: Dense embedding of BM25 candidates only (50 chunks, not 470)
    try:
        from src.f2_summarise.embeddings import EmbeddingModel, DEFAULT_EMBEDDING_MODEL, cosine_similarity
        import numpy as np
        model = EmbeddingModel(model_name or DEFAULT_EMBEDDING_MODEL)

        candidate_texts = [c.text for c in bm25_candidates]
        candidate_embeddings = model.embed_batch(candidate_texts)
        candidate_vectors = [e.vector for e in candidate_embeddings]

        query_embeddings = model.embed_batch(COMPLIANCE_QUERIES)
        avg_query = np.mean([e.vector for e in query_embeddings], axis=0)

        dense_scored = [(i, cosine_similarity(avg_query, cv))
                        for i, cv in enumerate(candidate_vectors)]
        dense_ranked = sorted(dense_scored, key=lambda x: x[1], reverse=True)

    except Exception:
        # Fallback if embeddings fail
        dense_ranked = [(i, _score_chunk(c)) for i, c in enumerate(bm25_candidates)]
        dense_ranked.sort(key=lambda x: x[1], reverse=True)

    # Step 3: RRF on BM25 candidates
    bm25_reranked = _bm25_rank(bm25_candidates)
    rrf_ranked = _rrf_combine(dense_ranked, bm25_reranked)

    # Take top candidate_k by RRF score
    top_indices = {idx for idx, _ in rrf_ranked[:candidate_k]}

    # Always include first and last of original doc
    first_in_bm25 = next((i for i, c in enumerate(bm25_candidates) if c.index == 0), None)
    last_in_bm25 = next((i for i, c in enumerate(bm25_candidates)
                         if c.index == len(chunks) - 1), None)
    if first_in_bm25 is not None:
        top_indices.add(first_in_bm25)
    if last_in_bm25 is not None:
        top_indices.add(last_in_bm25)

    result = [bm25_candidates[i] for i in sorted(top_indices)]
    return result


def format_chunks_for_prompt(chunks: list[Chunk]) -> str:
    """
    Format retrieved chunks into a single string for the Claude prompt.
    Each chunk is labelled with its position for citation purposes.
    HierarchicalChunks include their section header as context.
    """
    from src.f2_summarise.chunker import HierarchicalChunk
    parts = []
    for chunk in chunks:
        label = f"[Chunk {chunk.index + 1}]"
        if isinstance(chunk, HierarchicalChunk) and chunk.section_header:
            flags = []
            if chunk.is_date_section:
                flags.append("DATE SECTION")
            if chunk.is_institution_section:
                flags.append("INSTITUTION SECTION")
            if chunk.is_table:
                flags.append("TABLE")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            label = f"[Chunk {chunk.index + 1}{flag_str} — Section: {chunk.section_header}]"
        parts.append(f"{label}\n{chunk.text}")
    return "\n\n---\n\n".join(parts)
