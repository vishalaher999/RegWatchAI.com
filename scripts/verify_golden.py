"""Verify golden set and policy files for Day 14B."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from collections import Counter

with open('fixtures/golden/summaries.json') as f:
    data = json.load(f)

entries = data['entries']
print(f"Golden set entries: {len(entries)}")
print()

agencies = Counter(e['agency'] for e in entries)
print("By agency:")
for k, v in sorted(agencies.items()):
    print(f"  {k}: {v}")
print()

types = Counter(e['doc_type'] for e in entries)
print("By doc_type:")
for k, v in sorted(types.items()):
    print(f"  {k}: {v}")
print()

routing = Counter(e['routing_expected'] for e in entries)
print("Expected routing:")
for k, v in sorted(routing.items()):
    print(f"  {k}: {v}")
print()

no_action = sum(1 for e in entries if e['no_action_required'])
print(f"No action required: {no_action}/{len(entries)}")
print(f"Action required:    {len(entries)-no_action}/{len(entries)}")
print()

diff = Counter(e['difficulty'] for e in entries)
print("Difficulty:")
for k, v in sorted(diff.items()):
    print(f"  {k}: {v}")
print()

print("Policy files:")
for pol in ['BSA-AML-Policy.txt', 'Fair-Lending-ECOA-Policy.txt', 'TRID-Mortgage-Disclosure-Policy.txt']:
    path = f'fixtures/policies/{pol}'
    size = os.path.getsize(path)
    with open(path, encoding='utf-8') as f:
        content = f.read()
    sections = content.count('SECTION')
    print(f"  {pol}")
    print(f"    Size: {size:,} bytes | Sections: {sections}")
