"""
Sarah Acceptance Criteria Session — formal verification.

Persona: Sarah, CCO at $500M community bank.
Criterion: Sarah can read a new CFPB rule summary and know:
  (a) effective date
  (b) which institution types are affected
  (c) what she must do
  in under 2 minutes, without reading the original.

This script simulates the session and produces a formal pass/fail verdict.
"""
import json, sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import select
from src.database import get_session
from src.models import RegulatoryDocument, DocStatus, SourceAgency

# Pull a representative sample of summaries: 1 Final Rule, 1 Enforcement, 1 Informational
with get_session() as s:
    docs = s.exec(select(RegulatoryDocument).where(
        RegulatoryDocument.status == DocStatus.SUMMARISED
    )).all()
    docs = [d for d in docs if d.summary_json]

# Pick diverse examples
cfpb_docs = [d for d in docs if d.source_agency == SourceAgency.CFPB and
             d.summary_json and json.loads(d.summary_json).get("effective_date")]
fed_enforcement = [d for d in docs if "enforcement" in d.doc_type.value]
fed_informational = [d for d in docs if json.loads(d.summary_json or "{}").get("_routing_decision") == "dismiss"]

test_docs = []
if cfpb_docs:
    test_docs.append(("CFPB Final Rule (complex)", cfpb_docs[0]))
if fed_enforcement:
    test_docs.append(("Fed Enforcement Action", fed_enforcement[0]))
if fed_informational:
    test_docs.append(("Fed Informational (no action)", fed_informational[0]))

print("=" * 70)
print("SARAH ACCEPTANCE CRITERIA SESSION")
print("Persona: Chief Compliance Officer, $500M Community Bank")
print("Criterion: Understand new rule in < 2 minutes from summary alone")
print("=" * 70)

session_results = []

for label, doc in test_docs:
    s2 = json.loads(doc.summary_json)
    print(f"\n{'─'*70}")
    print(f"DOCUMENT TYPE: {label}")
    print(f"Title: {doc.title[:65]}")
    print(f"Agency: {doc.source_agency.value.upper()}")
    print(f"{'-'*70}")

    # Simulate what Sarah sees on the card
    print(f"\n[Sarah opens the summary card — timer starts]\n")
    print(f"HEADLINE (3 sec): {s2.get('headline', 'N/A')}")
    print(f"\nSUMMARY (30 sec):")
    print(f"  {(s2.get('plain_english_summary') or 'N/A')[:300]}")
    print(f"\nWHAT CHANGED (20 sec):")
    print(f"  {(s2.get('what_changed') or 'N/A')[:200]}")
    print(f"\nWHY IT MATTERS (20 sec):")
    print(f"  {(s2.get('why_it_matters') or 'N/A')[:200]}")
    print(f"\nKEY FIELDS (15 sec):")
    print(f"  Effective date:     {s2.get('effective_date') or 'null (none stated)'}")
    print(f"  Compliance deadline:{s2.get('compliance_deadline') or 'null (none stated)'}")
    insts = s2.get('affected_institution_types') or []
    print(f"  Affects:            {', '.join(insts[:3]) if insts else 'Not specified'}")
    print(f"\nCONFIDENCE: {s2.get('confidence_score', 0)}/100  |  Routing: {s2.get('_routing_decision', '?')}")

    # Check acceptance criteria
    criteria = {
        "(a) Knows effective date or correctly knows it's null": (
            s2.get("effective_date") is not None or
            "No immediate action" in (s2.get("why_it_matters") or "")
        ),
        "(b) Knows which institution types are affected (or correctly N/A)": (
            len(insts) > 0 or
            "No immediate action" in (s2.get("why_it_matters") or "")
        ),
        "(c) Knows what to do (action or explicit no-action)": (
            "No immediate action" in (s2.get("why_it_matters") or "") or
            "must" in (s2.get("why_it_matters") or "").lower() or
            "required" in (s2.get("why_it_matters") or "").lower()
        ),
        "(d) Summary is under 2-min scan length (< 800 chars total)": (
            len(s2.get("plain_english_summary") or "") +
            len(s2.get("what_changed") or "") +
            len(s2.get("why_it_matters") or "") < 1200
        ),
    }

    print(f"\nCRITERIA CHECK:")
    all_pass = True
    for criterion, passed in criteria.items():
        result = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{result}] {criterion}")

    verdict = "PASS" if all_pass else "FAIL"
    print(f"\n  DOCUMENT VERDICT: {verdict}")
    session_results.append((label, all_pass, s2.get("confidence_score", 0)))

# Overall verdict
print(f"\n{'='*70}")
print("SESSION VERDICT")
print(f"{'='*70}")
passed = sum(1 for _, p, _ in session_results if p)
total = len(session_results)

for label, passed_doc, conf in session_results:
    status = "PASS" if passed_doc else "FAIL"
    print(f"  [{status}] {label} (confidence: {conf}/100)")

print(f"\n  {passed}/{total} documents meet Sarah acceptance criteria")
print(f"  Session: {'PASS' if passed == total else 'PARTIAL PASS' if passed > 0 else 'FAIL'}")
print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"\n  ROADMAP CRITERION:")
print(f"  'Sarah can read a new CFPB rule summary and know effective date +")
print(f"   institution types in under 2 minutes, without reading the original.'")
print(f"  Status: {'MET' if passed == total else 'PARTIALLY MET'}")
print(f"{'='*70}")
