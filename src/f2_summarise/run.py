"""
F2 summarisation CLI.

Usage:
    python -m src.f2_summarise.run                    # summarise 5 new docs
    python -m src.f2_summarise.run --limit 20         # summarise up to 20
    python -m src.f2_summarise.run --agency fed       # Fed docs only
    python -m src.f2_summarise.run --doc-id <uuid>    # one specific document
    python -m src.f2_summarise.run --show             # show existing summaries
"""

import argparse
import json
import sys

from sqlmodel import select

from src.database import get_session
from src.f2_summarise.summariser import summarise_batch, summarise_document
from src.models import DocStatus, RegulatoryDocument


def show_summaries(limit: int = 10) -> None:
    """Print existing summaries to console."""
    with get_session() as session:
        docs = session.exec(
            select(RegulatoryDocument)
            .where(RegulatoryDocument.status == DocStatus.SUMMARISED)
        ).all()

    docs = sorted(docs, key=lambda d: d.fetched_at or "", reverse=True)[:limit]

    print(f"\n{'='*70}")
    print(f"EXISTING SUMMARIES ({len(docs)} shown)")
    print(f"{'='*70}")

    for doc in docs:
        if not doc.summary_json:
            continue
        try:
            s = json.loads(doc.summary_json)
        except Exception:
            continue

        conf = s.get("confidence_score", "?")
        flag = " [REVIEW]" if doc.review_flag else ""
        print(f"\n{'-'*70}")
        print(f"Agency: {doc.source_agency.value.upper()}  |  Confidence: {conf}/100{flag}")
        print(f"HEADLINE: {s.get('headline', 'N/A')}")
        print(f"\nSUMMARY: {s.get('plain_english_summary', 'N/A')}")
        print(f"\nWHAT CHANGED: {s.get('what_changed', 'N/A')}")
        print(f"\nWHY IT MATTERS: {s.get('why_it_matters', 'N/A')}")
        print(f"\nEFFECTIVE DATE: {s.get('effective_date', 'null')}")
        print(f"COMPLIANCE DEADLINE: {s.get('compliance_deadline', 'null')}")
        print(f"AFFECTED INSTITUTIONS: {', '.join(s.get('affected_institution_types', []))}")
        print(f"CITATIONS: {', '.join(s.get('source_citations', []))}")

    print(f"\n{'='*70}\n")


def summarise_one(doc_id: str) -> None:
    with get_session() as session:
        doc = session.get(RegulatoryDocument, doc_id)
        if not doc:
            print(f"[error] Document {doc_id} not found")
            sys.exit(1)
        # Force re-summarise by resetting status
        doc.status = DocStatus.NEW
        doc.summary_json = None
        session.add(doc)
        session.commit()

    with get_session() as session:
        doc = session.get(RegulatoryDocument, doc_id)
        summarise_document(doc, verbose=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F2 AI Summarisation")
    parser.add_argument("--limit", type=int, default=5, help="Max documents to summarise")
    parser.add_argument("--agency", type=str, help="Filter by agency slug (fed, cfpb, ...)")
    parser.add_argument("--doc-id", type=str, help="Summarise one specific document by UUID")
    parser.add_argument("--show", action="store_true", help="Show existing summaries")
    args = parser.parse_args()

    if args.show:
        show_summaries(limit=args.limit)
    elif args.doc_id:
        summarise_one(args.doc_id)
    else:
        summarise_batch(limit=args.limit, agency_filter=args.agency)
