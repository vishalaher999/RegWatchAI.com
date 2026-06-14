"""List all summarised documents for golden set labeling."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlmodel import select
from src.database import get_session
from src.models import RegulatoryDocument, DocStatus

with get_session() as s:
    docs = s.exec(select(RegulatoryDocument).where(
        RegulatoryDocument.status == DocStatus.SUMMARISED
    )).all()

for d in sorted(docs, key=lambda x: (x.source_agency.value, x.doc_type.value)):
    s2 = json.loads(d.summary_json) if d.summary_json else {}
    conf = s2.get("confidence_score", 0)
    eff = s2.get("effective_date") or "null"
    routing = s2.get("_routing_decision", "?")
    print(f'{d.id[:8]} | {d.source_agency.value:<18} | {d.doc_type.value:<15} | conf={conf:>3} | {routing:<8} | {d.title[:50]}')
    if s2.get("effective_date"):
        print(f'         effective={eff}')
    if s2.get("affected_institution_types"):
        types = ", ".join(s2["affected_institution_types"][:3])
        print(f'         institutions={types[:60]}')
