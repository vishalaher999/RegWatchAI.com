"""
F3 impact classification eval — Day 26.

KM concept: #246 Golden dataset

Runs classify_impact() (src/f3_impact/classifier.py) against the 30
labeled pairs in fixtures/golden/impact_pairs.json and checks accuracy
against the CI gate target (>= 0.80, per CLAUDE.md eval targets).

Why a fixed golden set instead of re-grading impact_results.json wholesale:
  impact_results.json has 251 matches with no ground truth. The golden set
  is a small, hand-labeled sample (with rationale per pair) that lets us
  measure whether the v1 thresholds (0.55/0.45/0.35) actually agree with a
  human judgment of "is this regulation relevant to this policy section?".

How dense_score is sourced:
  The golden set stores a `dense_score_snapshot` from the Day 25 run, but
  this eval re-looks-up the CURRENT dense_score from data/f3_indexes/matches.json
  by (policy_name, section_id, regulation_doc_id). If the matcher or embeddings
  change, this eval reflects that — it is not frozen to the snapshot.
"""

import json
import sys
from collections import Counter
from pathlib import Path

from src.f3_impact.citations import is_named_regulation_match
from src.f3_impact.classifier import classify_impact
from src.f3_impact.matcher import INDEX_DIR

GOLDEN_PATH = Path("fixtures/golden/impact_pairs.json")
CI_GATE_THRESHOLD = 0.80

# KM #258 Regression CI: CI_GATE_THRESHOLD (0.80) is the aspirational target
# from CLAUDE.md and is allowed to stay red. REGRESSION_BASELINE is the
# measured accuracy as of Day 30 (23/30 = 76.7%, after Day 27's
# named_regulation_match fix + Day 30's multi-query retrieval, KM #164) —
# tests/test_f3_eval.py asserts against THIS, so any future change that drops
# accuracy below the current measured level fails CI immediately, even while
# the 80% gate is still being worked toward. Ratchet this up as accuracy
# improves; never lower it without a documented reason.
REGRESSION_BASELINE = 23 / 30


def _load_dense_score_lookup() -> dict[tuple[str, str, str], float]:
    """Map (policy_name, section_id, regulation_doc_id) -> dense_score from matches.json."""
    matches_path = INDEX_DIR / "matches.json"
    with open(matches_path, "r", encoding="utf-8") as f:
        sections = json.load(f)

    lookup: dict[tuple[str, str, str], float] = {}
    for section in sections:
        for match in section["matches"]:
            key = (section["policy_name"], section["section_id"], match["regulation_doc_id"])
            lookup[key] = match["dense_score"]
    return lookup


def run_eval(verbose: bool = True) -> dict:
    """
    Run the F3 impact classification eval.

    Returns a dict with `accuracy`, `correct`, `total`, `confusion`,
    and `mismatches` (list of pairs where predicted != true).
    """
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        golden = json.load(f)

    dense_lookup = _load_dense_score_lookup()

    confusion: Counter = Counter()
    mismatches = []
    correct = 0
    total = 0

    for pair in golden["pairs"]:
        key = (pair["policy_name"], pair["section_id"], pair["regulation_doc_id"])
        dense_score = dense_lookup.get(key, pair["dense_score_snapshot"])
        named_match = is_named_regulation_match(pair["policy_name"], pair["regulation_title"])

        predicted = classify_impact(dense_score, named_match).value
        true = pair["true_impact_level"]

        confusion[(true, predicted)] += 1
        total += 1
        if predicted == true:
            correct += 1
        else:
            mismatches.append(
                {
                    "pair_id": pair["pair_id"],
                    "policy_name": pair["policy_name"],
                    "section_id": pair["section_id"],
                    "regulation_title": pair["regulation_title"][:60],
                    "dense_score": dense_score,
                    "named_regulation_match": named_match,
                    "true": true,
                    "predicted": predicted,
                    "rationale": pair["rationale"],
                }
            )

    accuracy = correct / total if total else 0.0

    report = {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "confusion": dict(confusion),
        "mismatches": mismatches,
    }

    if verbose:
        _print_report(report)

    return report


def _print_report(report: dict) -> None:
    print(f"\n{'='*65}")
    print("F3 IMPACT CLASSIFICATION EVAL")
    print(f"{'='*65}")
    print(f"Accuracy: {report['correct']}/{report['total']} = {report['accuracy']:.1%}")
    print(f"CI gate target: >= {CI_GATE_THRESHOLD:.0%}")
    print(f"Result: {'PASS' if report['accuracy'] >= CI_GATE_THRESHOLD else 'FAIL'}")

    print("\nConfusion matrix (true -> predicted):")
    levels = ["high", "medium", "low", "not_applicable"]
    header = " " * 18 + "".join(f"{p:>16}" for p in levels)
    print(header)
    for true_level in levels:
        row = f"{true_level:>16}  "
        for pred_level in levels:
            count = report["confusion"].get((true_level, pred_level), 0)
            row += f"{count:>16}"
        print(row)

    if report["mismatches"]:
        print(f"\nMismatches ({len(report['mismatches'])}):")
        for m in report["mismatches"]:
            print(
                f"  [#{m['pair_id']:2d}] {m['policy_name']} §{m['section_id']} vs "
                f"{m['regulation_title']} | dense={m['dense_score']:.3f} "
                f"named_match={m['named_regulation_match']} "
                f"true={m['true']:14s} predicted={m['predicted']}"
            )
            print(f"        {m['rationale']}")

    print(f"\n{'='*65}\n")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    report = run_eval(verbose=True)
    sys.exit(0 if report["accuracy"] >= CI_GATE_THRESHOLD else 1)


if __name__ == "__main__":
    main()
