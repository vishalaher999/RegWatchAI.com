"""Quick DB status check."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import select
from src.database import get_session
from src.models import RegulatoryDocument

with get_session() as s:
    all_docs = s.exec(select(RegulatoryDocument)).all()

total = len(all_docs)
enriched = [d for d in all_docs if d.raw_content and len(d.raw_content) >= 500]

by_agency = {}
for d in all_docs:
    a = d.source_agency.value
    if a not in by_agency:
        by_agency[a] = {"total": 0, "enriched": 0, "chars": 0}
    by_agency[a]["total"] += 1
    if d.raw_content and len(d.raw_content) >= 500:
        by_agency[a]["enriched"] += 1
        by_agency[a]["chars"] += len(d.raw_content)

print(f"Total documents: {total}")
print(f"Enriched:        {len(enriched)} ({len(enriched)/total*100:.0f}%)")
print()
print(f"{'Agency':<22} {'Docs':>5} {'Enriched':>8} {'Total chars':>12}")
print("-" * 52)
for agency, counts in sorted(by_agency.items()):
    print(f"{agency:<22} {counts['total']:>5} {counts['enriched']:>8} {counts['chars']:>12,}")

total_chars = sum(c["chars"] for c in by_agency.values())
print("-" * 52)
print(f"{'TOTAL':<22} {total:>5} {len(enriched):>8} {total_chars:>12,}")
