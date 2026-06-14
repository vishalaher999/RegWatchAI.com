"""
Anomaly detection for F1.

Two signals are combined to flag unusual regulatory publications:

1. VOLUME ANOMALY — today's publication count for an agency is statistically
   unusual compared to its 30-day rolling history. Uses Z-score:
       Z = (today_count - mean) / std_dev
   A Z > 2.0 means the count is in the top ~2.5% of historical days.
   This threshold is tunable via VOLUME_Z_THRESHOLD.

2. OFF-SCHEDULE — a document was published on a day of week that is rare
   for that agency (< OFF_SCHEDULE_MIN_PCT of that agency's historical
   publications fall on that weekday). Regulators follow predictable schedules;
   a Friday FinCEN release when they normally publish Mon–Wed is a signal.

Both signals update the `is_anomaly` field on RegulatoryDocument records
and write an explanation to the AuditLog.
"""

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlmodel import select

from src.database import get_session
from src.models import AuditAction, AuditLog, RegulatoryDocument, SourceAgency

VOLUME_Z_THRESHOLD = 2.0      # Flag if daily count is 2+ std devs above mean
OFF_SCHEDULE_MIN_PCT = 0.10   # Flag if < 10% of agency's docs fall on this weekday
LOOKBACK_DAYS = 30            # Rolling window for baseline calculation


def _get_historical_daily_counts(
    agency: SourceAgency,
    lookback_days: int = LOOKBACK_DAYS,
) -> list[int]:
    """
    Return a list of daily document counts for an agency over the lookback window.
    Days with zero publications are included as 0 — they are part of the baseline.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    with get_session() as session:
        docs = session.exec(
            select(RegulatoryDocument).where(
                RegulatoryDocument.source_agency == agency,
                RegulatoryDocument.fetched_at >= cutoff,
            )
        ).all()

    # Group by date
    counts_by_date: Counter = Counter()
    for doc in docs:
        day = doc.fetched_at.date()
        counts_by_date[day] += 1

    # Fill in zero days so the baseline reflects quiet days too
    all_counts = []
    for i in range(lookback_days):
        day = (datetime.utcnow() - timedelta(days=i)).date()
        all_counts.append(counts_by_date.get(day, 0))

    return all_counts


def _zscore(value: float, mean: float, std: float) -> float:
    """Return Z-score. If std is 0 (no variation), return 0 — not anomalous."""
    if std == 0:
        return 0.0
    return (value - mean) / std


def _mean(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[int], mean: float) -> float:
    if len(values) < 2:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def detect_volume_anomaly(agency: SourceAgency, today_count: int) -> tuple[bool, str]:
    """
    Check if today's document count for an agency is statistically unusual.

    Returns (is_anomaly: bool, explanation: str).
    """
    historical = _get_historical_daily_counts(agency)

    # Exclude today's count from the baseline (it's the value we're testing)
    baseline = historical[1:]  # index 0 = today, index 1+ = prior days

    if len(baseline) < 7:
        # Not enough history to establish a baseline — don't flag
        return False, "insufficient history for baseline"

    mean = _mean(baseline)
    std = _std(baseline, mean)
    z = _zscore(today_count, mean, std)

    is_anomaly = z > VOLUME_Z_THRESHOLD
    explanation = (
        f"today={today_count}, mean={mean:.1f}, std={std:.1f}, z={z:.2f}"
        f" ({'ANOMALY' if is_anomaly else 'normal'})"
    )
    return is_anomaly, explanation


def detect_off_schedule(doc: RegulatoryDocument) -> tuple[bool, str]:
    """
    Check if a document was published on an unusual day of week for its agency.

    Returns (is_anomaly: bool, explanation: str).
    """
    if doc.published_date is None:
        return False, "no published_date to check"

    cutoff = datetime.utcnow() - timedelta(days=90)  # Longer window for day-of-week patterns

    with get_session() as session:
        historical_docs = session.exec(
            select(RegulatoryDocument).where(
                RegulatoryDocument.source_agency == doc.source_agency,
                RegulatoryDocument.published_date >= cutoff,
            )
        ).all()

    if len(historical_docs) < 20:
        return False, "insufficient history for day-of-week baseline"

    weekday_counts: Counter = Counter()
    for d in historical_docs:
        if d.published_date:
            weekday_counts[d.published_date.weekday()] += 1  # 0=Mon, 6=Sun

    total = sum(weekday_counts.values())
    doc_weekday = doc.published_date.weekday()
    weekday_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][doc_weekday]

    pct = weekday_counts.get(doc_weekday, 0) / total
    is_anomaly = pct < OFF_SCHEDULE_MIN_PCT

    explanation = (
        f"published on {weekday_name} ({pct:.0%} of {doc.source_agency.value} "
        f"docs historically on this day)"
        f" ({'OFF-SCHEDULE' if is_anomaly else 'normal'})"
    )
    return is_anomaly, explanation


def run_anomaly_check(new_docs: list[RegulatoryDocument]) -> int:
    """
    Run both anomaly detectors on a batch of newly ingested documents.

    Marks `is_anomaly = True` on flagged documents and writes AuditLog entries.
    Returns the count of flagged documents.
    """
    if not new_docs:
        return 0

    flagged = 0

    # Group docs by agency for volume check
    by_agency: defaultdict[SourceAgency, list[RegulatoryDocument]] = defaultdict(list)
    for doc in new_docs:
        by_agency[doc.source_agency].append(doc)

    for agency, docs in by_agency.items():
        today_count = len(docs)
        vol_anomaly, vol_explanation = detect_volume_anomaly(agency, today_count)

        for doc in docs:
            reasons = []

            if vol_anomaly:
                reasons.append(f"volume: {vol_explanation}")

            off_sched, sched_explanation = detect_off_schedule(doc)
            if off_sched:
                reasons.append(f"schedule: {sched_explanation}")

            if reasons:
                flagged += 1
                with get_session() as session:
                    # Re-fetch to get a session-bound instance
                    db_doc = session.get(RegulatoryDocument, doc.id)
                    if db_doc:
                        db_doc.is_anomaly = True
                        session.add(db_doc)

                        log = AuditLog(
                            action=AuditAction.INGEST,
                            actor="system:anomaly_detector",
                            doc_id=doc.id,
                            payload_json=json.dumps({
                                "anomaly": True,
                                "reasons": reasons,
                                "title": doc.title,
                                "agency": agency.value,
                            }),
                        )
                        session.add(log)
                        session.commit()

                print(f"  [anomaly] {doc.title[:60]}...")
                for reason in reasons:
                    print(f"    → {reason}")

    return flagged
