"""Check actual summary text for failing golden entries."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlmodel import select
from src.database import get_session
from src.models import RegulatoryDocument, DocStatus

with open('fixtures/golden/summaries.json') as f:
    golden = {e['doc_id'][:8]: e for e in json.load(f)['entries'] if e.get('doc_id')}

with get_session() as s:
    docs = s.exec(select(RegulatoryDocument).where(RegulatoryDocument.status == DocStatus.SUMMARISED)).all()
    doc_map = {d.id[:8]: d for d in docs if d.summary_json}

# Check the key failing entries
for prefix, entry in golden.items():
    if entry['id'] not in [4, 5, 9, 19]:
        continue
    doc = doc_map.get(prefix)
    if not doc:
        continue
    s2 = json.loads(doc.summary_json)
    print(f"=== Entry {entry['id']}: {entry['title'][:55]}")
    print(f"KEY FACTS TO FIND: {entry['key_facts']}")
    print(f"WHAT_CHANGED: {(s2.get('what_changed') or '')[:200]}")
    print(f"WHY_IT_MATTERS: {(s2.get('why_it_matters') or '')[:200]}")
    print(f"PLAIN_ENGLISH: {(s2.get('plain_english_summary') or '')[:200]}")
    print()
