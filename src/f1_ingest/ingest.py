"""
F1 ingestion orchestrator.

Runs the full pipeline for all active agencies:
  1. Load active agencies from DB
  2. Fetch each RSS feed
  3. Deduplicate against existing records
  4. Save new documents
  5. Enrich new documents with full text
  6. Run anomaly detection on new documents
  7. Write an AuditLog record for the run

Run via:  python -m src.f1_ingest.ingest
"""

import json

from sqlmodel import select

from src.database import get_session
from src.f1_ingest.agencies import FR_API_SLUGS
from src.f1_ingest.anomaly import run_anomaly_check
from src.f1_ingest.dedup import is_duplicate
from src.f1_ingest.fetcher import fetch_feed, fetch_fr_api
from src.f1_ingest.fulltext import run_fulltext_enrichment
from src.models import Agency, AuditLog, AuditAction, RegulatoryDocument


def log_document_ingest(session, doc: RegulatoryDocument, agency_slug: str) -> None:
    """
    Write one AuditLog(INGEST) entry scoped to this specific document
    (Day 36, KM #242 Compliance logging).

    Before Day 36, INGEST was only logged once per agency run with no
    doc_id, so an ingest event could never be traced to a specific
    RegulatoryDocument (see docs/F4-Audit-Report-v1.md Section 7, gap #2).
    This per-document entry is what get_task_audit_trail (Day 34) now
    surfaces as the first entry in a Task's trail.
    """
    session.add(AuditLog(
        action=AuditAction.INGEST,
        actor="system",
        doc_id=doc.id,
        payload_json=json.dumps({
            "agency": agency_slug,
            "title": doc.title,
            "doc_type": doc.doc_type.value,
            "url": doc.url,
        }),
    ))


def run_ingest(agency_slugs: list[str] | None = None) -> dict:
    """
    Run feed ingestion for all active agencies (or a subset by slug).

    Returns a summary dict with counts per agency.
    """
    summary: dict[str, dict] = {}

    with get_session() as session:
        query = select(Agency).where(Agency.active == True)
        if agency_slugs:
            query = query.where(Agency.slug.in_(agency_slugs))
        agencies = session.exec(query).all()

    if not agencies:
        print("[warn] No active agencies found. Run scripts/setup_db.py first.")
        return summary

    for agency in agencies:
        print(f"\n[{agency.slug}] Fetching {agency.name}...")
        fetcher = fetch_fr_api if agency.slug in FR_API_SLUGS else fetch_feed
        documents = fetcher(agency)
        print(f"  Found {len(documents)} entries in feed")

        new_count = 0
        duplicate_count = 0
        saved_docs: list[RegulatoryDocument] = []

        for doc in documents:
            if is_duplicate(doc.content_hash):
                duplicate_count += 1
                continue

            with get_session() as session:
                session.add(doc)
                log_document_ingest(session, doc, agency.slug)
                session.commit()
                session.refresh(doc)
                new_count += 1
                saved_docs.append(doc)

        # Enrich new documents with full text before anomaly check
        if saved_docs:
            enrich_result = run_fulltext_enrichment(limit=len(saved_docs))
            print(f"  Full text: {enrich_result['enriched']} enriched | {enrich_result['failed']} failed")

        # Run anomaly detection on the documents we just saved
        flagged = run_anomaly_check(saved_docs)

        # Write one AuditLog entry per agency run
        with get_session() as session:
            log = AuditLog(
                action=AuditAction.INGEST,
                actor="system",
                payload_json=json.dumps({
                    "agency": agency.slug,
                    "feed_url": agency.feed_url,
                    "fetched": len(documents),
                    "new": new_count,
                    "duplicates": duplicate_count,
                    "anomalies_flagged": flagged,
                }),
            )
            session.add(log)
            session.commit()

        summary[agency.slug] = {
            "fetched": len(documents),
            "new": new_count,
            "duplicates": duplicate_count,
            "anomalies": flagged,
        }
        print(f"  Saved {new_count} new | Skipped {duplicate_count} dupes | {flagged} anomalies")

    return summary


def print_summary(summary: dict) -> None:
    print("\n" + "=" * 58)
    print("INGEST SUMMARY")
    print("=" * 58)
    total_new = sum(v["new"] for v in summary.values())
    total_dupes = sum(v["duplicates"] for v in summary.values())
    total_anomalies = sum(v.get("anomalies", 0) for v in summary.values())
    for slug, counts in summary.items():
        anom = counts.get("anomalies", 0)
        anom_str = f"  ⚠ {anom} anomalies" if anom else ""
        print(f"  {slug:<22} {counts['new']:>3} new  {counts['duplicates']:>3} dupes{anom_str}")
    print("-" * 58)
    print(f"  {'TOTAL':<22} {total_new:>3} new  {total_dupes:>3} dupes  {total_anomalies} anomalies")
    print("=" * 58)


if __name__ == "__main__":
    summary = run_ingest()
    print_summary(summary)
