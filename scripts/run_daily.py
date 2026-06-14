"""
Daily RegWatch AI pipeline runner.

Called by Windows Task Scheduler every morning at 7:00 AM.
Runs the full F1 pipeline and appends results to a log file.

Steps:
  1. Feed health check
  2. Feed ingestion (new documents)
  3. Full-text enrichment (up to 20 docs per run)

Log file: logs/daily_run.log
Exit codes: 0 = success, 1 = one or more feeds unhealthy
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path regardless of where Task Scheduler calls from
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set up file logging before any imports that might log
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "daily_run.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("regwatch.daily")

from src.f1_ingest.health import health_summary, run_health_check
from src.f1_ingest.ingest import run_ingest, print_summary
from src.f1_ingest.fulltext import run_fulltext_enrichment


def main() -> int:
    started = datetime.utcnow()
    log.info("=" * 60)
    log.info(f"RegWatch AI daily run started — {started.strftime('%Y-%m-%d %H:%M UTC')}")
    log.info("=" * 60)

    # ── Step 1: Health check ──────────────────────────────────────────────────
    log.info("STEP 1: Feed health check")
    health_results = run_health_check(verbose=False)
    summary = health_summary(health_results)

    for agency in summary["agencies"]:
        status = agency["status"]
        log.info(f"  {agency['slug']:<22} {status}")

    unhealthy = [a for a in summary["agencies"] if a["status"] != "OK"]
    if unhealthy:
        for a in unhealthy:
            log.warning(f"  UNHEALTHY: {a['slug']} — {a.get('error', a['status'])}")
    else:
        log.info(f"  All {len(health_results)} agencies healthy")

    # ── Step 2: Ingestion ─────────────────────────────────────────────────────
    log.info("STEP 2: Feed ingestion")
    ingest_result = run_ingest()

    total_new = sum(v["new"] for v in ingest_result.values())
    total_dupes = sum(v["duplicates"] for v in ingest_result.values())
    total_anomalies = sum(v.get("anomalies", 0) for v in ingest_result.values())

    log.info(f"  New: {total_new}  |  Duplicates: {total_dupes}  |  Anomalies: {total_anomalies}")

    if total_anomalies > 0:
        log.warning(f"  {total_anomalies} anomaly/anomalies flagged — check dashboard")

    # ── Step 3: Full-text enrichment ──────────────────────────────────────────
    log.info("STEP 3: Full-text enrichment (up to 20 docs)")
    enrich_result = run_fulltext_enrichment(limit=20)
    log.info(
        f"  Enriched: {enrich_result['enriched']}  |"
        f"  Skipped: {enrich_result['skipped']}  |"
        f"  Failed: {enrich_result['failed']}"
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    duration = (datetime.utcnow() - started).total_seconds()
    exit_code = 0 if not unhealthy else 1
    status_word = "COMPLETED" if exit_code == 0 else "COMPLETED WITH WARNINGS"

    log.info("-" * 60)
    log.info(f"Daily run {status_word} in {duration:.1f}s")
    log.info(
        json.dumps({
            "date": started.strftime("%Y-%m-%d"),
            "new_docs": total_new,
            "anomalies": total_anomalies,
            "unhealthy_feeds": len(unhealthy),
            "enriched": enrich_result["enriched"],
            "duration_seconds": round(duration, 1),
        })
    )
    log.info("=" * 60)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
