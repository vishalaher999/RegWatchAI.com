"""
Chunking strategy benchmark for F2.

Tests all 5 strategies on 20 real regulatory documents from the DB.
Scores each strategy on 4 metrics and prints a ranked comparison table.

No API calls — pure local computation. Run in seconds.

Usage:
    python scripts/benchmark_chunking.py
    python scripts/benchmark_chunking.py --docs 10
    python scripts/benchmark_chunking.py --verbose

Metrics:
  1. date_coverage      — retrieved chunks contain year patterns (compliance deadlines)
  2. institution_coverage — retrieved chunks contain institution type keywords
  3. coherence          — chunks don't start mid-sentence (no split sentences)
  4. retrieval_efficiency — % of document content in the retrieved top-k chunks
                            (lower = more selective = less noise for Claude)
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import select

from src.database import get_session
from src.f2_summarise.chunker import STRATEGIES, chunk_stats, chunk_with_strategy
from src.f2_summarise.retriever import retrieve_top_chunks
from src.models import RegulatoryDocument

# ── Scoring helpers ────────────────────────────────────────────────────────────

_DATE_PATTERN = re.compile(r'\b(202[4-9]|203[0-9])\b')
_DATE_PHRASES = re.compile(
    r'effective\s+date|compliance\s+date|compliance\s+deadline|takes\s+effect|'
    r'no\s+later\s+than|must\s+comply\s+by|january|february|march|april|may|june|'
    r'july|august|september|october|november|december',
    re.IGNORECASE,
)
_INSTITUTION_TERMS = re.compile(
    r'community\s+bank|credit\s+union|national\s+bank|state\s+bank|'
    r'financial\s+institution|depository\s+institution|federally\s+insured|'
    r'bank\s+holding|thrift|mortgage\s+servicer|lender',
    re.IGNORECASE,
)
_SENTENCE_START = re.compile(r'^[A-Z\(\d§]')  # chunk starts with sentence-beginning char


def score_date_coverage(retrieved_text: str) -> float:
    """Did the retrieved chunks capture date information? (0.0–1.0)"""
    has_year = bool(_DATE_PATTERN.search(retrieved_text))
    has_phrase = bool(_DATE_PHRASES.search(retrieved_text))
    return (0.5 * has_year) + (0.5 * has_phrase)


def score_institution_coverage(retrieved_text: str) -> float:
    """Did the retrieved chunks mention institution types? (0.0–1.0)"""
    matches = _INSTITUTION_TERMS.findall(retrieved_text)
    # Scale: 0=none, 0.5=1-2 mentions, 1.0=3+ distinct mentions
    unique = len(set(m.lower() for m in matches))
    return min(unique / 3.0, 1.0)


def score_coherence(chunks) -> float:
    """What fraction of chunks start with a sentence-beginning character? (0.0–1.0)"""
    if not chunks:
        return 0.0
    good = sum(1 for c in chunks if _SENTENCE_START.match(c.text.strip()))
    return good / len(chunks)


def score_retrieval_efficiency(all_chunks, retrieved_chunks) -> float:
    """
    Retrieval efficiency = how much signal is in the retrieved chunks.

    Measured as: unique content in retrieved / total document content.
    Lower ratio = more selective (better). We invert it so higher = better.
    Optimal: retrieve 20% of document content that contains 80% of the signal.
    """
    if not all_chunks:
        return 0.0
    total_chars = sum(len(c.text) for c in all_chunks)
    retrieved_chars = sum(len(c.text) for c in retrieved_chunks)
    if total_chars == 0:
        return 0.0
    ratio = retrieved_chars / total_chars
    # Score: retrieving 10-30% of content = best (score 1.0)
    # Retrieving >60% = poor selectivity (score 0.0)
    if ratio <= 0.30:
        return 1.0
    elif ratio <= 0.50:
        return 0.6
    elif ratio <= 0.70:
        return 0.3
    return 0.0


# ── Benchmark runner ───────────────────────────────────────────────────────────

def benchmark_strategy(strategy_name: str, docs: list[RegulatoryDocument]) -> dict:
    """Run one chunking strategy on all docs, return aggregate scores."""
    total_date = 0.0
    total_institution = 0.0
    total_coherence = 0.0
    total_efficiency = 0.0
    total_chunk_count = 0
    total_avg_size = 0.0
    valid_docs = 0

    for doc in docs:
        if not doc.raw_content or len(doc.raw_content) < 200:
            continue

        try:
            chunks = chunk_with_strategy(doc.raw_content, strategy_name)
            if not chunks:
                continue

            retrieved = retrieve_top_chunks(chunks)
            retrieved_text = " ".join(c.text for c in retrieved)

            total_date += score_date_coverage(retrieved_text)
            total_institution += score_institution_coverage(retrieved_text)
            total_coherence += score_coherence(chunks)
            total_efficiency += score_retrieval_efficiency(chunks, retrieved)

            stats = chunk_stats(chunks)
            total_chunk_count += stats["count"]
            total_avg_size += stats["avg_chars"]
            valid_docs += 1

        except Exception as e:
            print(f"  [warn] {strategy_name} failed on doc {doc.id[:8]}: {e}")

    if valid_docs == 0:
        return {"strategy": strategy_name, "error": "no valid docs"}

    n = valid_docs
    date_score = total_date / n
    inst_score = total_institution / n
    coh_score = total_coherence / n
    eff_score = total_efficiency / n

    # Weighted composite score
    # Date coverage weighted highest — it's the hardest and most critical field
    composite = (
        date_score * 0.35 +
        inst_score * 0.25 +
        coh_score * 0.20 +
        eff_score * 0.20
    )

    return {
        "strategy": strategy_name,
        "docs_tested": valid_docs,
        "date_coverage": round(date_score, 3),
        "institution_coverage": round(inst_score, 3),
        "coherence": round(coh_score, 3),
        "retrieval_efficiency": round(eff_score, 3),
        "composite_score": round(composite, 3),
        "avg_chunks_per_doc": round(total_chunk_count / n, 1),
        "avg_chunk_size": round(total_avg_size / n),
    }


def run_benchmark(num_docs: int = 20, verbose: bool = False) -> list[dict]:
    """
    Run all 5 chunking strategies on real documents from the DB.
    Returns results sorted by composite score (best first).
    """
    print(f"\nLoading {num_docs} documents from database...")
    with get_session() as session:
        docs = session.exec(select(RegulatoryDocument)).all()

    # Prefer longer documents — they stress-test chunking more meaningfully
    docs = [d for d in docs if d.raw_content and len(d.raw_content) >= 500]
    docs = sorted(docs, key=lambda d: len(d.raw_content or ""), reverse=True)[:num_docs]

    print(f"Testing on {len(docs)} documents")
    print(f"Document sizes: {min(len(d.raw_content) for d in docs):,} – "
          f"{max(len(d.raw_content) for d in docs):,} chars\n")

    results = []
    for strategy_name in STRATEGIES:
        print(f"  Testing '{strategy_name}'...", end=" ", flush=True)
        result = benchmark_strategy(strategy_name, docs)
        results.append(result)
        print(f"composite={result.get('composite_score', '?'):.3f}")

    results.sort(key=lambda r: r.get("composite_score", 0), reverse=True)
    return results


def print_results(results: list[dict]) -> None:
    print(f"\n{'='*80}")
    print("CHUNKING BENCHMARK RESULTS")
    print(f"{'='*80}")
    print(f"\n{'Strategy':<18} {'Date':>8} {'Inst':>8} {'Coher':>8} {'Effic':>8} {'SCORE':>8} {'Chunks':>8} {'AvgSz':>8}")
    print(f"{'-'*18} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")

    for i, r in enumerate(results):
        if "error" in r:
            print(f"{r['strategy']:<18} ERROR: {r['error']}")
            continue
        rank = "[WINNER]" if i == 0 else f"  #{i+1}   "
        print(
            f"{r['strategy']:<18} "
            f"{r['date_coverage']:>8.3f} "
            f"{r['institution_coverage']:>8.3f} "
            f"{r['coherence']:>8.3f} "
            f"{r['retrieval_efficiency']:>8.3f} "
            f"{r['composite_score']:>8.3f} "
            f"{r['avg_chunks_per_doc']:>8.1f} "
            f"{r['avg_chunk_size']:>8}"
        )

    winner = results[0]
    print(f"\n{'='*80}")
    print(f"WINNER: '{winner['strategy']}'  (composite score: {winner['composite_score']:.3f})")
    print(f"{'='*80}")
    print(f"\nMetric weights used:")
    print(f"  Date coverage:          35% — most critical (compliance deadlines)")
    print(f"  Institution coverage:   25% — who must act")
    print(f"  Coherence:              20% — chunk quality")
    print(f"  Retrieval efficiency:   20% — selectivity (less noise to Claude)")
    print(f"\nRecommendation: update DEFAULT_STRATEGY in summariser.py to '{winner['strategy']}'")
    print(f"{'='*80}\n")

    return winner["strategy"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark F2 chunking strategies")
    parser.add_argument("--docs", type=int, default=20, help="Number of docs to test")
    parser.add_argument("--verbose", action="store_true", help="Show per-doc results")
    args = parser.parse_args()

    results = run_benchmark(num_docs=args.docs, verbose=args.verbose)
    winner = print_results(results)
