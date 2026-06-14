"""F2 run statistics for Day 14."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlmodel import select
from src.database import get_session
from src.models import RegulatoryDocument, DocStatus

with get_session() as s:
    docs = s.exec(select(RegulatoryDocument).where(RegulatoryDocument.status == DocStatus.SUMMARISED)).all()

total = len(docs)
confidences = []
routing_counts = {}
review_q = 0
has_eff_date = 0
has_deadline = 0
has_institutions = 0
has_what_changed = 0
total_duration = 0.0

for d in docs:
    if not d.summary_json:
        continue
    s2 = json.loads(d.summary_json)
    conf = s2.get('confidence_score', 0)
    confidences.append(conf)
    routing = s2.get('_routing_decision', 'unknown')
    routing_counts[routing] = routing_counts.get(routing, 0) + 1
    if d.review_flag:
        review_q += 1
    if s2.get('effective_date'):
        has_eff_date += 1
    if s2.get('compliance_deadline'):
        has_deadline += 1
    if s2.get('affected_institution_types'):
        has_institutions += 1
    wc = s2.get('what_changed', '')
    if wc and ('Previously:' in wc or 'previously' in wc.lower()):
        has_what_changed += 1

avg_conf = sum(confidences) / len(confidences) if confidences else 0
queue_pct = review_q / total * 100 if total else 0

print("=== F2 MVP — DAY 14 STATISTICS ===")
print(f"Total summarised:       {total}")
print(f"Avg confidence:         {avg_conf:.1f}/100")
print(f"Min / Max confidence:   {min(confidences)} / {max(confidences)}")
print()
print("Routing breakdown:")
for k, v in sorted(routing_counts.items()):
    print(f"  {k:<14} {v:>3} ({v/total*100:.0f}%)")
print()
print(f"Review queue:           {review_q}/{total} ({queue_pct:.0f}%)")
if queue_pct < 20:
    print("Queue target (<20%):    PASS")
else:
    print("Queue target (<20%):    FAIL - above target")
print()
print("Field completeness:")
print(f"  effective_date set:   {has_eff_date}/{total} ({has_eff_date/total*100:.0f}%)")
print(f"  compliance_deadline:  {has_deadline}/{total} ({has_deadline/total*100:.0f}%)")
print(f"  institution_types:    {has_institutions}/{total} ({has_institutions/total*100:.0f}%)")
print(f"  what_changed (Prev):  {has_what_changed}/{total} ({has_what_changed/total*100:.0f}%)")
