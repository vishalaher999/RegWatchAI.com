import json
with open('evals/judge_calibration.json') as f:
    data = json.load(f)
print(f"Agreement rate: {data['agreement_rate']:.1%}")
print(f"Judge avg faithfulness: {data['avg_judge_faithfulness']:.3f}")
print(f"Keyword avg faithfulness would be from eval report")
print()
print("DISAGREEMENTS:")
for d in data['disagreements'][:5]:
    kw = d['keyword_faithfulness']
    j = d['judge_faithfulness']
    print(f"  Entry {d['entry_id']}: keyword={kw:.2f} vs judge={j:.2f} (delta={d['delta']:.2f})")
    print(f"    Title: {d['title'][:55]}")
    reason = d.get('faithfulness_reason', '')
    print(f"    Judge says: {reason[:100]}")
    issue = d.get('biggest_issue', '')
    if issue:
        print(f"    Issue: {issue[:80]}")
    print()
