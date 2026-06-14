"""
Embedding model benchmark for F2 v2 — Day 15.

Tests 3 sentence-transformers models on 4 regulatory retrieval query types.
Measures Precision@3 and Recall@3 against NER-identified relevant chunks.

Why these 4 query types?
  These are exactly the fields where our keyword retriever underperforms —
  the current Day 8 keyword scorer only finds chunks with exact keyword matches.
  Embeddings find semantically similar chunks regardless of exact wording.

Usage:
  python scripts/benchmark_embeddings.py              # all 3 models, 10 docs
  python scripts/benchmark_embeddings.py --docs 5    # faster test run
  python scripts/benchmark_embeddings.py --model minilm  # one model only
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sqlmodel import select

from src.database import get_session
from src.f2_summarise.chunker import chunk_with_strategy
from src.f2_summarise.embeddings import BENCHMARK_MODELS, EmbeddingModel, cosine_similarity
from src.models import RegulatoryDocument

import re

# Compliance-relevant patterns for relevance detection
# (defined locally rather than importing private ner module internals)
_DATE_PHRASES = re.compile(
    r'effective\s+date|compliance\s+date|compliance\s+deadline|takes?\s+effect|'
    r'no\s+later\s+than|must\s+comply\s+by|implementation\s+date|'
    r'january|february|march|april|may|june|july|august|september|october|november|december',
    re.IGNORECASE,
)
_INSTITUTION_TERMS = re.compile(
    r'community\s+bank|credit\s+union|national\s+bank|state\s+bank|'
    r'financial\s+institution|depository\s+institution|federally\s+insured|'
    r'bank\s+holding|thrift|mortgage\s+servicer|lender',
    re.IGNORECASE,
)
_EFFECTIVE_DATE_CONTEXT = re.compile(
    r'effective\s+(?:date|on|as\s+of)|takes?\s+effect|becomes?\s+effective',
    re.IGNORECASE,
)
_COMPLIANCE_DEADLINE_CONTEXT = re.compile(
    r'must\s+comply\s+(?:by|no\s+later\s+than)|compliance\s+deadline|'
    r'no\s+later\s+than|required\s+to\s+comply\s+by',
    re.IGNORECASE,
)

# ── Query templates ────────────────────────────────────────────────────────────
# These represent the kinds of questions the summariser implicitly asks
# when retrieving chunks for each summary field.

QUERY_TYPES = {
    "effective_date": [
        "When does this rule take effect?",
        "What is the effective date of this regulation?",
        "When does compliance begin?",
    ],
    "compliance_deadline": [
        "When must institutions comply by?",
        "What is the compliance deadline?",
        "By what date must banks implement changes?",
    ],
    "institution_types": [
        "Which types of financial institutions are affected?",
        "What banks and credit unions must comply?",
        "Who is subject to this rule?",
    ],
    "what_changed": [
        "What changed from the previous rule?",
        "What are the new requirements?",
        "What did the agency amend?",
    ],
}

# ── Relevance detection ────────────────────────────────────────────────────────

def _chunk_has_date(text: str) -> bool:
    """True if chunk contains date/deadline content."""
    t = text.lower()
    return (bool(_DATE_PHRASES.search(t)) or
            bool(re.search(r'\b202[4-9]\b', t)) or
            bool(_EFFECTIVE_DATE_CONTEXT.search(t)) or
            bool(_COMPLIANCE_DEADLINE_CONTEXT.search(t)))


def _chunk_has_institution(text: str) -> bool:
    """True if chunk mentions institution types."""
    return bool(_INSTITUTION_TERMS.search(text))


def _chunk_has_compliance_action(text: str) -> bool:
    """True if chunk contains compliance action language."""
    t = text.lower()
    action_patterns = re.compile(
        r'\b(must|shall|required to|required by|must comply|'
        r'compliance required|obligation|prohibited|must implement|'
        r'need to|needs to)\b'
    )
    return bool(action_patterns.search(t))


def _chunk_has_change(text: str) -> bool:
    """True if chunk discusses what changed."""
    t = text.lower()
    change_patterns = re.compile(
        r'\b(amend|amendment|revise|revision|previously|prior to|'
        r'replac|supersed|new requirement|change|update|modify|'
        r'previously required|now requires|no longer)\b'
    )
    return bool(change_patterns.search(t))


RELEVANCE_FN = {
    "effective_date":     _chunk_has_date,
    "compliance_deadline": _chunk_has_date,
    "institution_types":  _chunk_has_institution,
    "what_changed":       _chunk_has_change,
}


# ── Benchmark core ─────────────────────────────────────────────────────────────

def precision_at_k(retrieved_indices: list[int], relevant_set: set[int], k: int) -> float:
    """Fraction of top-k retrieved items that are relevant."""
    top_k = retrieved_indices[:k]
    hits = sum(1 for i in top_k if i in relevant_set)
    return hits / k if k > 0 else 0.0


def recall_at_k(retrieved_indices: list[int], relevant_set: set[int], k: int) -> float:
    """Fraction of relevant items found in top-k."""
    if not relevant_set:
        return 1.0  # No relevant items = trivially retrieved
    top_k = retrieved_indices[:k]
    hits = sum(1 for i in top_k if i in relevant_set)
    return hits / len(relevant_set)


def benchmark_model_on_doc(
    model: EmbeddingModel,
    doc: RegulatoryDocument,
    k: int = 3,
) -> dict:
    """
    Run the embedding model on one document and return per-query-type scores.
    """
    chunks = chunk_with_strategy(doc.raw_content, "hierarchical")
    if len(chunks) < 3:
        return {}  # Too few chunks for meaningful benchmark

    chunk_texts = [c.text for c in chunks]

    # Embed all chunks in one batch (efficient)
    chunk_embeddings = model.embed_batch(chunk_texts)
    chunk_vectors = [e.vector for e in chunk_embeddings]

    results = {}

    for query_type, queries in QUERY_TYPES.items():
        # Find which chunks are relevant for this query type
        relevance_fn = RELEVANCE_FN[query_type]
        relevant_indices = {i for i, c in enumerate(chunks) if relevance_fn(c.text)}

        if not relevant_indices:
            continue  # Skip if no relevant chunks for this query type

        # Average scores across all query variants for this type
        p_scores = []
        r_scores = []

        for query in queries:
            query_vec = model.embed(query).vector
            # Score each chunk by cosine similarity to query
            scores = [(i, cosine_similarity(query_vec, cv)) for i, cv in enumerate(chunk_vectors)]
            scores.sort(key=lambda x: x[1], reverse=True)
            ranked = [i for i, _ in scores]

            p_scores.append(precision_at_k(ranked, relevant_indices, k))
            r_scores.append(recall_at_k(ranked, relevant_indices, k))

        results[query_type] = {
            "precision_at_k": round(sum(p_scores) / len(p_scores), 3),
            "recall_at_k":    round(sum(r_scores) / len(r_scores), 3),
            "relevant_chunks": len(relevant_indices),
            "total_chunks":    len(chunks),
        }

    return results


def run_benchmark(
    model_keys: list[str],
    num_docs: int = 10,
    k: int = 3,
) -> dict:
    """
    Run all models on a sample of documents.
    Returns nested dict: model_key → query_type → {precision, recall}.
    """
    # Load documents — prefer longer ones for meaningful chunking
    with get_session() as session:
        docs = session.exec(select(RegulatoryDocument)).all()

    docs = [d for d in docs if d.raw_content and len(d.raw_content) >= 1000]
    docs = sorted(docs, key=lambda d: len(d.raw_content or ""), reverse=True)[:num_docs]

    print(f"\nBenchmarking {len(model_keys)} models on {len(docs)} documents (P@{k}, R@{k})")
    print(f"Doc sizes: {min(len(d.raw_content) for d in docs):,} – {max(len(d.raw_content) for d in docs):,} chars\n")

    all_results: dict[str, dict] = {}

    for model_key in model_keys:
        model_name = BENCHMARK_MODELS[model_key]
        model = EmbeddingModel(model_name)
        print(f"Model: {model_key} ({model_name})")

        query_type_scores: dict[str, list] = {qt: [] for qt in QUERY_TYPES}
        t_start = time.time()

        for i, doc in enumerate(docs):
            doc_results = benchmark_model_on_doc(model, doc, k=k)
            for qt, scores in doc_results.items():
                query_type_scores[qt].append(scores)
            print(f"  [{i+1}/{len(docs)}] {doc.source_agency.value}: {len(doc.raw_content):,} chars, "
                  f"{sum(len(v) for v in query_type_scores.values())} query-type results")

        elapsed = time.time() - t_start
        print(f"  Completed in {elapsed:.1f}s\n")

        # Aggregate across documents
        aggregated = {}
        for qt, score_list in query_type_scores.items():
            if not score_list:
                continue
            aggregated[qt] = {
                "precision_at_k": round(sum(s["precision_at_k"] for s in score_list) / len(score_list), 3),
                "recall_at_k":    round(sum(s["recall_at_k"] for s in score_list) / len(score_list), 3),
                "docs_with_data": len(score_list),
            }

        # Composite score: weighted average across query types
        weights = {"effective_date": 0.35, "compliance_deadline": 0.30,
                   "institution_types": 0.20, "what_changed": 0.15}
        composite = 0.0
        total_weight = 0.0
        for qt, w in weights.items():
            if qt in aggregated:
                composite += aggregated[qt]["precision_at_k"] * w
                total_weight += w
        composite = round(composite / total_weight, 3) if total_weight > 0 else 0.0

        aggregated["_composite"] = composite
        aggregated["_elapsed_seconds"] = round(elapsed, 1)
        all_results[model_key] = aggregated

    return all_results


def print_results(results: dict, k: int = 3) -> str:
    """Print benchmark results table and return the winning model key."""
    print(f"\n{'='*72}")
    print(f"EMBEDDING BENCHMARK RESULTS  (Precision@{k} and Recall@{k})")
    print(f"{'='*72}")

    header = f"{'Model':<10} {'Eff.Date':>9} {'Deadline':>9} {'Inst.':>9} {'Changed':>9} {'COMPOSITE':>10} {'Time':>7}"
    print(header)
    print("-" * 72)

    ranked = sorted(results.items(), key=lambda x: x[1].get("_composite", 0), reverse=True)

    for i, (model_key, data) in enumerate(ranked):
        rank_str = "[WINNER]" if i == 0 else f"   #{i+1}   "
        p = lambda qt: f"{data[qt]['precision_at_k']:.3f}" if qt in data else "  N/A "
        print(
            f"{model_key:<10} "
            f"{p('effective_date'):>9} "
            f"{p('compliance_deadline'):>9} "
            f"{p('institution_types'):>9} "
            f"{p('what_changed'):>9} "
            f"{data.get('_composite', 0):>10.3f} "
            f"{data.get('_elapsed_seconds', 0):>6.1f}s"
        )

    winner_key = ranked[0][0]
    winner_model = BENCHMARK_MODELS[winner_key]
    composite = ranked[0][1].get("_composite", 0)

    print(f"\n{'='*72}")
    print(f"WINNER: '{winner_key}' — {winner_model}")
    print(f"Composite P@{k}: {composite:.3f}")
    print(f"{'='*72}")
    print(f"\nMetric weights: effective_date=35%, compliance_deadline=30%, institution_types=20%, what_changed=15%")
    print(f"Action: update DEFAULT_EMBEDDING_MODEL in embeddings.py to '{winner_model}'")
    print(f"{'='*72}\n")

    return winner_key


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark embedding models for F2 retrieval")
    parser.add_argument("--docs", type=int, default=10, help="Number of documents to test")
    parser.add_argument("--model", choices=list(BENCHMARK_MODELS.keys()),
                        help="Test one model only (default: all 3)")
    parser.add_argument("--k", type=int, default=3, help="Top-k for precision/recall (default: 3)")
    args = parser.parse_args()

    model_keys = [args.model] if args.model else list(BENCHMARK_MODELS.keys())
    results = run_benchmark(model_keys, num_docs=args.docs, k=args.k)
    winner = print_results(results, k=args.k)
