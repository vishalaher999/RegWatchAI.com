"""
Impact classifier v1 for F3 — Policy Impact Mapping.

KM concept: #17/#20 LogReg/XGBoost (see "Why thresholds, not a trained
model, in v1" below)

Takes the regulation matches produced by matcher.py and assigns each one
an ImpactLevel: HIGH, MEDIUM, LOW, or NOT_APPLICABLE.

Why thresholds, not a trained model, in v1:
  LogReg/XGBoost need labeled training data. Day 26 builds the first
  labeled set (30 regulation-policy pairs) — it doesn't exist yet.
  A threshold rule is:
    - Usable today (no training step)
    - Explainable (SR 11-7: "0.566 >= 0.55 -> High" is auditable;
      a trained model's decision boundary is not, without extra work)
    - A documented baseline for Day 26 to validate/recalibrate, or
      replace with a trained classifier if thresholds underperform
      the 80% CI gate.

Why dense_score, not rrf_score, drives the thresholds:
  Day 24 found RRF scores cluster near their mathematical floor
  (~0.03) for nearly every match — almost no separation between
  "strong match" and "noise". Dense cosine similarity has real
  dynamic range (Day 23: 0.566 for a true match vs ~0.42 for an
  unrelated section), so it's the signal worth thresholding.

Day 27 — named_regulation_match adjustment:
  Day 26's eval scored 40% (12/30) against the golden set. The errors
  split cleanly along one line: does the candidate regulation's title
  name a law the POLICY ITSELF already cites (src/f3_impact/citations.py)?
    - named_regulation_match=True  but dense_score just under HIGH_THRESHOLD
      -> these were false negatives (e.g. Fair-Lending-ECOA-Policy vs
      "Equal Credit Opportunity Act (Regulation B)", dense=0.47-0.52).
    - named_regulation_match=False but dense_score moderate-to-high
      -> these were false positives (e.g. BSA-AML-Policy/TRID vs the
      SAME "Equal Credit Opportunity Act (Regulation B)" regulation,
      dense=0.44-0.58 — generic compliance language, not substantive).
  NAMED_MATCH_BOOST and NO_MATCH_PENALTY shift dense_score before
  thresholding, using the SAME thresholds — explainability is preserved
  ("0.47 + 0.10 = 0.57 >= 0.55 -> High, because Reg B is in this policy's
  own Regulatory Framework section").
"""

import json
from enum import Enum
from pathlib import Path

from src.database import get_session
from src.f3_impact.citations import is_named_regulation_match
from src.f3_impact.matcher import INDEX_DIR
from src.models import AuditAction, AuditLog

# Thresholds — v1 baseline, calibrate against Day 26's 30 labeled pairs.
HIGH_THRESHOLD = 0.55
MEDIUM_THRESHOLD = 0.45
LOW_THRESHOLD = 0.35

# Day 27 adjustments — applied to dense_score before thresholding.
NAMED_MATCH_BOOST = 0.10
NO_MATCH_PENALTY = -0.20


class ImpactLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NOT_APPLICABLE = "not_applicable"


def classify_impact(dense_score: float, named_regulation_match: bool = False) -> ImpactLevel:
    """
    Map a dense cosine similarity score to an ImpactLevel using v1 thresholds.

    If `named_regulation_match` is True, dense_score is boosted by
    NAMED_MATCH_BOOST before thresholding (the regulation names a law the
    policy itself cites — a real signal dense_score under-weighted).
    If False, dense_score is reduced by NO_MATCH_PENALTY's magnitude (the
    regulation doesn't name any law this policy cites — moderate dense_score
    here is more likely generic compliance-language similarity than a
    substantive match).
    """
    adjustment = NAMED_MATCH_BOOST if named_regulation_match else NO_MATCH_PENALTY
    adjusted_score = dense_score + adjustment

    if adjusted_score >= HIGH_THRESHOLD:
        return ImpactLevel.HIGH
    if adjusted_score >= MEDIUM_THRESHOLD:
        return ImpactLevel.MEDIUM
    if adjusted_score >= LOW_THRESHOLD:
        return ImpactLevel.LOW
    return ImpactLevel.NOT_APPLICABLE


def classify_matches(sections: list[dict]) -> list[dict]:
    """
    Add `impact_level` to every match in `sections` (the output of
    matcher.build_matches()). Returns a new list; does not mutate input.
    """
    results = []
    for section in sections:
        new_section = dict(section)
        new_section["matches"] = [
            {
                **match,
                "named_regulation_match": is_named_regulation_match(
                    section["policy_name"], match["regulation_title"]
                ),
                "impact_level": classify_impact(
                    match["dense_score"],
                    is_named_regulation_match(section["policy_name"], match["regulation_title"]),
                ).value,
            }
            for match in section["matches"]
        ]
        results.append(new_section)
    return results


def log_map_decisions(results: list[dict]) -> int:
    """
    Write one AuditLog(MAP) entry per classified (policy section, regulation)
    match (Day 36, KM #242 Compliance logging).

    Before Day 36, F3 wrote no AuditLog at all (docs/F4-Audit-Report-v1.md
    Section 7, gap #1) -- a Task's audit trail had no record of *why* F3
    classified its source finding as HIGH. Each entry is doc_id-scoped to
    the regulation, with payload identifying the policy section and the
    thresholds/scores behind the decision -- explainable per this module's
    docstring ("0.566 >= 0.55 -> High" is auditable).

    Returns the number of entries written.
    """
    count = 0
    with get_session() as session:
        for section in results:
            for match in section["matches"]:
                session.add(AuditLog(
                    action=AuditAction.MAP,
                    actor="system",
                    doc_id=match["regulation_doc_id"],
                    payload_json=json.dumps({
                        "policy_name": section["policy_name"],
                        "section_id": section["section_id"],
                        "regulation_title": match["regulation_title"],
                        "dense_score": match["dense_score"],
                        "named_regulation_match": match["named_regulation_match"],
                        "impact_level": match["impact_level"],
                        "high_threshold": HIGH_THRESHOLD,
                        "medium_threshold": MEDIUM_THRESHOLD,
                        "low_threshold": LOW_THRESHOLD,
                    }),
                ))
                count += 1
        session.commit()
    return count


def main() -> None:
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    matches_path = INDEX_DIR / "matches.json"
    with open(matches_path, "r", encoding="utf-8") as f:
        sections = json.load(f)

    results = classify_matches(sections)

    out_path = INDEX_DIR / "impact_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logged = log_map_decisions(results)
    print(f"Logged {logged} AuditLog(MAP) entries")

    counts: dict[str, int] = {level.value: 0 for level in ImpactLevel}
    for section in results:
        for match in section["matches"]:
            counts[match["impact_level"]] += 1

    print("Impact level distribution across all matches:")
    for level, count in counts.items():
        print(f"  {level:15s} {count}")

    print(f"\nSaved to {out_path}")

    print("\nAny HIGH or MEDIUM findings:")
    found = False
    for section in results:
        for match in section["matches"]:
            if match["impact_level"] in ("high", "medium"):
                found = True
                print(
                    f"  {section['policy_name']} §{section['section_id']} "
                    f"({section['section_title']}) -> "
                    f"[{match['impact_level'].upper()}] "
                    f"{match['regulation_title'][:60]} "
                    f"(dense={match['dense_score']:.3f})"
                )
    if not found:
        print("  none")


if __name__ == "__main__":
    main()
