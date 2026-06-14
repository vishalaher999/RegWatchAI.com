"""
One-time backfill: fetch full text for documents already in the DB.

Processes documents with missing or short raw_content, oldest first.
Safe to run multiple times — already-enriched documents are skipped.

Usage:
    python scripts/enrich_fulltext.py              # enriches up to 20 docs
    python scripts/enrich_fulltext.py --limit 50   # enrich up to 50
    python scripts/enrich_fulltext.py --limit 0    # enrich all (slow)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.f1_ingest.fulltext import run_fulltext_enrichment

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich documents with full text")
    parser.add_argument("--limit", type=int, default=20,
                        help="Max documents to enrich per run (0 = all, default 20)")
    args = parser.parse_args()

    limit = args.limit if args.limit > 0 else 9999

    print(f"Starting full-text enrichment (limit={limit})...\n")
    result = run_fulltext_enrichment(limit=limit)

    print(f"\nEnrichment complete:")
    print(f"  Enriched: {result['enriched']}")
    print(f"  Skipped:  {result['skipped']}  (text too short after fetch)")
    print(f"  Failed:   {result['failed']}  (fetch error)")
