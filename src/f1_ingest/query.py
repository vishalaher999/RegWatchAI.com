"""
F1 database inspection CLI.

Quick views into what RegWatch AI has ingested. Intended for development
and demos — not a production reporting tool (that's F5).

Usage:
    python -m src.f1_ingest.query                  # full summary
    python -m src.f1_ingest.query --recent 10      # 10 most recent docs
    python -m src.f1_ingest.query --anomalies       # flagged docs only
    python -m src.f1_ingest.query --agency fed      # single agency view
"""

import argparse
from collections import Counter

from sqlmodel import select

from src.database import get_session
from src.models import DocType, RegulatoryDocument, SourceAgency


def _truncate(text: str, max_len: int = 70) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def show_summary() -> None:
    with get_session() as session:
        all_docs = session.exec(select(RegulatoryDocument)).all()

    total = len(all_docs)
    print(f"\n{'='*60}")
    print(f"  REGWATCH AI — FEED SUMMARY  ({total} documents total)")
    print(f"{'='*60}")

    # By agency
    agency_counts: Counter = Counter()
    for doc in all_docs:
        agency_counts[doc.source_agency.value] += 1

    print("\n  By Agency:")
    for agency, count in sorted(agency_counts.items(), key=lambda x: -x[1]):
        print(f"    {agency:<30} {count:>4} docs")

    # By doc type
    type_counts: Counter = Counter()
    for doc in all_docs:
        type_counts[doc.doc_type.value] += 1

    print("\n  By Document Type:")
    for dtype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {dtype:<30} {count:>4} docs")

    # Status
    anomaly_count = sum(1 for d in all_docs if d.is_anomaly)
    review_count = sum(1 for d in all_docs if d.review_flag)
    print(f"\n  Anomalies flagged:   {anomaly_count}")
    print(f"  In review queue:     {review_count}")
    print(f"{'='*60}\n")


def show_recent(n: int = 10, agency_slug: str | None = None) -> None:
    with get_session() as session:
        query = select(RegulatoryDocument)
        if agency_slug:
            try:
                agency_enum = SourceAgency(agency_slug)
                query = query.where(RegulatoryDocument.source_agency == agency_enum)
            except ValueError:
                print(f"[error] Unknown agency slug: {agency_slug}")
                print(f"  Valid slugs: {[a.value for a in SourceAgency]}")
                return
        docs = session.exec(query).all()

    # Sort by fetched_at descending, take n
    docs_sorted = sorted(docs, key=lambda d: d.fetched_at or "", reverse=True)[:n]

    label = f"agency={agency_slug}" if agency_slug else "all agencies"
    print(f"\n  RECENT {n} DOCUMENTS ({label})\n")
    print(f"  {'#':<3} {'TYPE':<15} {'AGENCY':<18} TITLE")
    print(f"  {'-'*3} {'-'*15} {'-'*18} {'-'*40}")

    for i, doc in enumerate(docs_sorted, 1):
        anomaly_marker = " ⚠" if doc.is_anomaly else ""
        print(
            f"  {i:<3} {doc.doc_type.value:<15} {doc.source_agency.value:<18} "
            f"{_truncate(doc.title, 50)}{anomaly_marker}"
        )
    print()


def show_anomalies() -> None:
    with get_session() as session:
        docs = session.exec(
            select(RegulatoryDocument).where(RegulatoryDocument.is_anomaly == True)
        ).all()

    print(f"\n  ANOMALY-FLAGGED DOCUMENTS ({len(docs)} total)\n")
    if not docs:
        print("  No anomalies detected yet.\n")
        return

    for doc in sorted(docs, key=lambda d: d.fetched_at or "", reverse=True):
        date_str = doc.published_date.strftime("%Y-%m-%d") if doc.published_date else "unknown date"
        print(f"  ⚠  [{doc.source_agency.value}] {date_str}")
        print(f"     {_truncate(doc.title, 75)}")
        print(f"     Type: {doc.doc_type.value}  |  URL: {doc.url[:60]}...")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RegWatch AI — feed inspection tool")
    parser.add_argument("--recent", type=int, metavar="N", help="Show N most recent documents")
    parser.add_argument("--anomalies", action="store_true", help="Show only anomaly-flagged documents")
    parser.add_argument("--agency", type=str, help="Filter by agency slug (fed, cfpb, occ, fdic, fincen, federal_register)")
    args = parser.parse_args()

    if args.anomalies:
        show_anomalies()
    elif args.recent:
        show_recent(args.recent, args.agency)
    else:
        show_summary()
        show_recent(10, args.agency)
