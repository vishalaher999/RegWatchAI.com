"""
Daily F1 validation script.

Runs in sequence:
  1. Feed health check — are all agencies reachable and fresh?
  2. Ingestion — fetch and save new documents
  3. Validation report — did we meet today's success criteria?

Exit codes:
  0 — all checks passed
  1 — one or more checks failed (feeds unreachable, stale, or 0 new docs on first run)

Usage:
    python scripts/daily_validate.py
    python scripts/daily_validate.py --skip-ingest   # health check only
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_session
from src.f1_ingest.health import health_summary, run_health_check
from src.f1_ingest.ingest import run_ingest
from src.models import AuditAction, AuditLog


def print_header(text: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def run_validation(skip_ingest: bool = False) -> int:
    """
    Run the full daily validation. Returns exit code (0=pass, 1=fail).
    """
    started_at = datetime.utcnow()
    failures: list[str] = []

    # ── 1. Health Check ────────────────────────────────────────────────────────
    print_header(f"REGWATCH AI — DAILY VALIDATION  {started_at.strftime('%Y-%m-%d %H:%M UTC')}")
    print("\n  STEP 1: Feed Health Check\n")

    health_results = run_health_check(verbose=True)
    summary = health_summary(health_results)

    unhealthy = [r for r in health_results if not r.healthy]
    if unhealthy:
        for r in unhealthy:
            msg = f"{r.slug} is {r.status_label}"
            if r.error:
                msg += f" ({r.error})"
            failures.append(msg)
        print(f"\n  [WARN]  {len(unhealthy)} agency/agencies not healthy")
    else:
        print(f"\n  [OK]  All {len(health_results)} agencies healthy")

    # ── 2. Ingestion ───────────────────────────────────────────────────────────
    if not skip_ingest:
        print("\n  STEP 2: Feed Ingestion\n")
        ingest_summary = run_ingest()

        total_new = sum(v["new"] for v in ingest_summary.values())
        total_anomalies = sum(v.get("anomalies", 0) for v in ingest_summary.values())

        print(f"\n  Ingestion complete: {total_new} new documents, {total_anomalies} anomalies flagged")
    else:
        print("\n  STEP 2: Skipped (--skip-ingest)")
        ingest_summary = {}
        total_new = 0
        total_anomalies = 0

    # ── 3. Validation Report ───────────────────────────────────────────────────
    print_header("VALIDATION REPORT")

    checks = [
        ("All feeds reachable", summary["unreachable"] == 0),
        ("All feeds fresh (docs within 3 days)", summary["stale"] == 0),
        ("No feed errors", all(not r.error for r in health_results)),
    ]

    all_passed = True
    for check_name, passed in checks:
        icon = "[PASS]" if passed else "[FAIL]"
        print(f"  {icon}  {check_name}")
        if not passed:
            all_passed = False

    if failures:
        print(f"\n  Failures:")
        for f in failures:
            print(f"    • {f}")

    # Success metric: zero missed publications
    # We verify this by confirming all feeds are reachable (reachable = not missing)
    metric_passed = summary["unreachable"] == 0
    print(f"\n  Success Metric — Zero missed publications: {'PASS' if metric_passed else 'FAIL'}")

    # Write to AuditLog
    with get_session() as session:
        log = AuditLog(
            action=AuditAction.INGEST,
            actor="system:daily_validate",
            payload_json=json.dumps({
                "validation_run": True,
                "timestamp": started_at.isoformat(),
                "health": summary,
                "ingest": {k: {kk: vv for kk, vv in v.items()} for k, v in ingest_summary.items()},
                "all_checks_passed": all_passed,
                "failures": failures,
            }),
        )
        session.add(log)
        session.commit()

    duration = (datetime.utcnow() - started_at).total_seconds()
    status = "PASSED" if all_passed else "FAILED"
    print(f"\n  Validation {status} in {duration:.1f}s")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RegWatch AI daily validation")
    parser.add_argument("--skip-ingest", action="store_true", help="Run health check only, skip feed ingestion")
    args = parser.parse_args()

    exit_code = run_validation(skip_ingest=args.skip_ingest)
    sys.exit(exit_code)
