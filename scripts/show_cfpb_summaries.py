"""Show CFPB summary quality for hybrid retrieval comparison."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlmodel import select
from src.database import get_session
from src.models import RegulatoryDocument, SourceAgency, DocStatus

with get_session() as s:
    docs = s.exec(select(RegulatoryDocument).where(
        RegulatoryDocument.source_agency == SourceAgency.CFPB,
        RegulatoryDocument.status == DocStatus.SUMMARISED
    )).all()

for d in docs:
    if not d.summary_json:
        continue
    s2 = json.loads(d.summary_json)
    conf = s2.get("confidence_score", 0)
    routing = s2.get("_routing_decision", "?")
    eff = s2.get("effective_date") or "null"
    inst = s2.get("affected_institution_types") or []
    wc = (s2.get("what_changed") or "")[:250]
    print(f"=== {d.title[:60]}")
    print(f"    Confidence: {conf}/100 | Routing: {routing}")
    print(f"    Effective date: {eff}")
    print(f"    Institutions: {inst[:3]}")
    print(f"    What changed: {wc}")
    print()
