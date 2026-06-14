"""
LLM judge calibration against human golden set labels — Day 20.

Compares Claude Haiku judge scores against our keyword-based RAGAS scores
for the same documents. Measures agreement rate.

Agreement: both methods score within AGREEMENT_TOLERANCE of each other.

Usage:
    python scripts/calibrate_judge.py                 # run on all available summaries
    python scripts/calibrate_judge.py --limit 10      # cheaper — 10 docs only
    python scripts/calibrate_judge.py --save          # save calibration report
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.llm_judge import judge_summary
from evals.ragas_eval import run_eval, EntryScore

AGREEMENT_TOLERANCE = 0.20   # Scores within 0.20 = "agree"
CALIBRATED_THRESHOLD = 0.80  # 80%+ agreement = judge is calibrated
GOLDEN_SET_PATH = "fixtures/golden/summaries.json"


def run_calibration(limit: int = 20, verbose: bool = True) -> dict:
    """
    Run LLM judge on summarised documents and compare against keyword eval.
    Returns calibration metrics dict.
    """
    from sqlmodel import select
    from src.database import get_session
    from src.models import RegulatoryDocument, DocStatus
    from src.f2_summarise.chunker import chunk_with_strategy
    from src.f2_summarise.retriever import retrieve_top_chunks
    from src.f2_summarise.retriever import format_chunks_for_prompt

    # Load golden set
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        golden_data = json.load(f)

    golden_entries = {e["doc_id"][:8]: e for e in golden_data["entries"] if e.get("doc_id")}

    # Load summarised docs
    with get_session() as session:
        docs = session.exec(
            select(RegulatoryDocument).where(
                RegulatoryDocument.status == DocStatus.SUMMARISED
            )
        ).all()

    # Filter to docs with golden entries
    matchable = [d for d in docs if d.id[:8] in golden_entries and d.summary_json and d.raw_content]
    matchable = matchable[:limit]

    if verbose:
        print(f"\n{'='*65}")
        print("LLM JUDGE CALIBRATION")
        print(f"{'='*65}")
        print(f"Documents to evaluate: {len(matchable)}")
        print(f"Judge model: claude-haiku-4-5-20251001 (temp=0.1)")
        print(f"Agreement tolerance: ±{AGREEMENT_TOLERANCE}")
        print(f"{'='*65}\n")

    # Run keyword eval first (reference scores)
    keyword_report = run_eval(GOLDEN_SET_PATH, num_entries=50, verbose=False)
    keyword_scores = {
        es.entry_id: es
        for es in keyword_report.entry_scores
        if es.summary_found and es.faithfulness is not None
    }

    comparisons = []
    total_cost = 0.0

    for i, doc in enumerate(matchable):
        entry = golden_entries.get(doc.id[:8], {})
        entry_id = entry.get("id", 0)
        keyword_es = keyword_scores.get(entry_id)

        if verbose:
            print(f"  [{i+1}/{len(matchable)}] {doc.title[:55]}...")

        # Get context text (re-chunk the document)
        try:
            chunks = chunk_with_strategy(doc.raw_content, "hierarchical")
            top_chunks = retrieve_top_chunks(chunks, top_k=5)
            context_text = format_chunks_for_prompt(top_chunks)
        except Exception:
            context_text = doc.raw_content[:2000]

        summary = json.loads(doc.summary_json)

        # Run LLM judge
        t0 = time.time()
        judge_score = judge_summary(
            title=doc.title,
            agency=doc.source_agency.value,
            context_text=context_text,
            summary=summary,
        )
        elapsed = time.time() - t0
        total_cost += judge_score.cost_estimate_usd

        # Compare against keyword score
        keyword_faith = keyword_es.faithfulness if keyword_es else None
        judge_faith = judge_score.faithfulness
        agree = (
            keyword_faith is not None and
            abs(judge_faith - keyword_faith) <= AGREEMENT_TOLERANCE
        )

        comparisons.append({
            "entry_id": entry_id,
            "title": doc.title[:50],
            "keyword_faithfulness": keyword_faith,
            "judge_faithfulness": judge_faith,
            "judge_action_clarity": judge_score.action_clarity,
            "judge_date_precision": judge_score.date_precision,
            "judge_composite": round(judge_score.composite, 3),
            "agree": agree,
            "delta": round(abs(judge_faith - (keyword_faith or 0)), 3) if keyword_faith else None,
            "biggest_issue": judge_score.biggest_issue,
            "faithfulness_reason": judge_score.faithfulness_reason,
            "cost_usd": judge_score.cost_estimate_usd,
            "elapsed_s": round(elapsed, 1),
        })

        if verbose:
            kw = f"{keyword_faith:.2f}" if keyword_faith is not None else " N/A"
            agree_str = "AGREE" if agree else "DIFFER"
            print(f"         Keyword={kw}  Judge={judge_faith:.2f}  [{agree_str}]  "
                  f"${judge_score.cost_estimate_usd:.4f}  {elapsed:.1f}s")
            if judge_score.biggest_issue:
                print(f"         Issue: {judge_score.biggest_issue[:60]}")

    # Compute agreement metrics
    agreements = [c for c in comparisons if c["agree"] and c["delta"] is not None]
    disagrees = [c for c in comparisons if not c["agree"] and c["delta"] is not None]
    valid = [c for c in comparisons if c["delta"] is not None]

    agreement_rate = len(agreements) / len(valid) if valid else 0.0
    avg_delta = sum(c["delta"] for c in valid) / len(valid) if valid else 0.0
    avg_judge_faith = sum(c["judge_faithfulness"] for c in comparisons) / len(comparisons) if comparisons else 0.0
    avg_judge_composite = sum(c["judge_composite"] for c in comparisons) / len(comparisons) if comparisons else 0.0

    calibrated = agreement_rate >= CALIBRATED_THRESHOLD

    results = {
        "docs_evaluated": len(comparisons),
        "valid_comparisons": len(valid),
        "agreement_rate": round(agreement_rate, 3),
        "calibrated": calibrated,
        "avg_delta": round(avg_delta, 3),
        "avg_judge_faithfulness": round(avg_judge_faith, 3),
        "avg_judge_composite": round(avg_judge_composite, 3),
        "total_cost_usd": round(total_cost, 4),
        "comparisons": comparisons,
        "disagreements": [c for c in comparisons if not c["agree"]],
    }

    if verbose:
        _print_calibration_report(results)

    return results


def _print_calibration_report(results: dict) -> None:
    print(f"\n{'='*65}")
    print("CALIBRATION REPORT")
    print(f"{'='*65}")
    print(f"  Documents evaluated:  {results['docs_evaluated']}")
    print(f"  Valid comparisons:    {results['valid_comparisons']}")
    print(f"  Agreement rate:       {results['agreement_rate']:.1%}  "
          f"({'CALIBRATED' if results['calibrated'] else 'NOT CALIBRATED'})")
    print(f"  Target:               >= {CALIBRATED_THRESHOLD:.0%}")
    print(f"  Avg delta (keyword vs judge): {results['avg_delta']:.3f}")
    print()
    print(f"  Judge avg faithfulness:  {results['avg_judge_faithfulness']:.3f}")
    print(f"  Judge avg composite:     {results['avg_judge_composite']:.3f}")
    print(f"  Total cost:              ${results['total_cost_usd']:.4f}")
    print()

    if results["disagreements"]:
        print(f"  Disagreements ({len(results['disagreements'])}):")
        for d in results["disagreements"]:
            kw = f"{d['keyword_faithfulness']:.2f}" if d['keyword_faithfulness'] is not None else "N/A"
            print(f"    [{d['entry_id']:>2}] keyword={kw}  judge={d['judge_faithfulness']:.2f}  "
                  f"delta={d['delta']:.2f}  {d['title'][:40]}")
            if d.get("faithfulness_reason"):
                print(f"          Judge says: {d['faithfulness_reason'][:60]}")

    overall = "CALIBRATED" if results["calibrated"] else "NOT CALIBRATED"
    print(f"\n  RESULT: Judge is {overall}")
    print(f"  (agreement {results['agreement_rate']:.1%} vs threshold {CALIBRATED_THRESHOLD:.0%})")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrate LLM judge against golden set")
    parser.add_argument("--limit", type=int, default=20, help="Max documents to evaluate")
    parser.add_argument("--save", action="store_true", help="Save calibration report JSON")
    args = parser.parse_args()

    results = run_calibration(limit=args.limit)

    if args.save:
        with open("evals/judge_calibration.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        print("Calibration report saved to: evals/judge_calibration.json")
