"""
Run the F2 RAGAS evaluation and save the baseline report.

Usage:
    python scripts/run_eval.py                    # first 30 golden entries
    python scripts/run_eval.py --entries 50       # full 50-entry set
    python scripts/run_eval.py --save             # also save JSON report
"""

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.ragas_eval import run_eval, EvalReport

GOLDEN_SET_PATH = "fixtures/golden/summaries.json"
REPORT_OUTPUT   = "evals/baseline_report.json"


def save_report(report: EvalReport, path: str) -> None:
    """Serialise the report to JSON for CI pipeline use."""
    data = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_entries": report.total_golden_entries,
        "summaries_found": report.summaries_found,
        "metrics": {
            "faithfulness":         report.avg_faithfulness,
            "hallucination_rate":   report.avg_hallucination_rate,
            "answer_relevance":     report.avg_answer_relevance,
            "date_accuracy":        report.avg_date_accuracy,
            "institution_accuracy": report.avg_institution_accuracy,
            "routing_accuracy":     report.avg_routing_accuracy,
            "no_action_accuracy":   report.avg_no_action_accuracy,
            "what_changed_quality": report.avg_what_changed_quality,
        },
        "targets": {
            "faithfulness_week3":  0.75,
            "faithfulness_day45":  0.85,
            "hallucination_rate":  0.05,
        },
        "pass": report.faithfulness_passes,
        "by_difficulty": report.by_difficulty,
        "by_doc_type":   report.by_doc_type,
        "top_failures":  report.top_failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Report saved to: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run F2 RAGAS evaluation")
    parser.add_argument("--entries", type=int, default=30,
                        help="Number of golden entries to evaluate (default: 30)")
    parser.add_argument("--save", action="store_true",
                        help="Save JSON report to evals/baseline_report.json")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-entry output")
    args = parser.parse_args()

    report = run_eval(
        golden_set_path=GOLDEN_SET_PATH,
        num_entries=args.entries,
        verbose=not args.quiet,
    )

    if args.save:
        save_report(report, REPORT_OUTPUT)
