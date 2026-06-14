"""
F4 task generation eval — Day 31.

KM concept: #177 ReAct

There is no golden "good task" label set yet (no human-graded examples of
what a correct task title/description/due_date looks like for F4 v1) — so
this eval is STRUCTURAL/TRACEABILITY validation, not semantic quality. It
checks that every generated task is well-formed and traceable back to its
source F3 finding. Semantic quality (is the due date right? is the title
clear?) is an explicitly documented gap, same honest-caveat pattern as F3's
Claude-labeled golden set (see notes/Day-31-F4.md).

CI gate: 100% of generated tasks must pass ALL structural checks:
  1. title references both the source policy section_id and the source
     regulation_title (or a recognisable substring of it)
  2. owner is one of the personas defined in CLAUDE.md ("Sarah", "Mike")
  3. due_date parses as an ISO date (YYYY-MM-DD)
  4. description contains the evidence excerpt from matched_chunk_text
     (checked against data/f3_indexes/impact_results.json, since tasks.json
     only stores the source identifiers, not the full matched chunk text)
"""

import json
import sys
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

TASKS_PATH = Path("data/f4_tasks/tasks.json")
IMPACT_RESULTS_PATH = Path("data/f3_indexes/impact_results.json")

VALID_OWNERS = {"Sarah", "Mike"}

# The agent quotes a snippet FROM somewhere in matched_chunk_text, not
# necessarily the start -- so "contains the evidence excerpt" is checked via
# longest contiguous substring shared between matched_chunk_text and the
# description. MIN_EXCERPT_MATCH_CHARS is the minimum length of that shared
# substring to count as "a real quote", not a coincidental short overlap.
MIN_EXCERPT_MATCH_CHARS = 30


def _load_impact_results() -> dict[tuple[str, str, str], str]:
    """Map (policy_name, section_id, regulation_doc_id) -> matched_chunk_text."""
    sections = json.loads(IMPACT_RESULTS_PATH.read_text(encoding="utf-8"))
    lookup = {}
    for section in sections:
        for match in section["matches"]:
            key = (section["policy_name"], section["section_id"], match["regulation_doc_id"])
            lookup[key] = match["matched_chunk_text"]
    return lookup


def validate_task(task: dict, chunk_lookup: dict[tuple[str, str, str], str]) -> list[str]:
    """Return a list of failure reasons for one task (empty list = valid)."""
    failures = []

    # 1. title references section_id and (part of) the regulation title
    if task["source_section_id"] not in task["title"]:
        failures.append("title does not reference source_section_id")
    reg_title_words = task["source_regulation_title"].split()
    title_lower = task["title"].lower()
    if not any(word.lower() in title_lower for word in reg_title_words if len(word) > 4):
        failures.append("title does not reference source_regulation_title")

    # 2. owner is a known persona
    if task["owner"] not in VALID_OWNERS:
        failures.append(f"owner '{task['owner']}' not in {VALID_OWNERS}")

    # 3. due_date is a valid ISO date
    try:
        date.fromisoformat(task["due_date"])
    except (ValueError, TypeError):
        failures.append(f"due_date '{task.get('due_date')}' is not a valid ISO date")

    # 4. description contains the evidence excerpt
    key = (task["source_policy_name"], task["source_section_id"], task["source_regulation_doc_id"])
    chunk_text = chunk_lookup.get(key)
    if chunk_text is None:
        failures.append("source finding not found in impact_results.json")
    else:
        matcher = SequenceMatcher(None, chunk_text, task["description"], autojunk=False)
        match = matcher.find_longest_match(0, len(chunk_text), 0, len(task["description"]))
        if match.size < MIN_EXCERPT_MATCH_CHARS:
            failures.append("description does not contain evidence excerpt from matched_chunk_text")

    return failures


def run_eval(verbose: bool = False) -> dict:
    tasks = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    chunk_lookup = _load_impact_results()

    results = []
    for i, task in enumerate(tasks):
        failures = validate_task(task, chunk_lookup)
        results.append({"index": i, "title": task["title"], "failures": failures})

    valid_count = sum(1 for r in results if not r["failures"])
    total = len(results)
    pass_rate = valid_count / total if total else 0.0

    if verbose:
        print(f"\n{'='*65}")
        print(f"F4 STRUCTURAL VALIDATION — {valid_count}/{total} tasks pass ({pass_rate:.1%})")
        print(f"CI gate: 100% structural validity")
        print(f"{'='*65}\n")
        for r in results:
            status = "PASS" if not r["failures"] else "FAIL"
            print(f"  [{status}] #{r['index']} {r['title']}")
            for f in r["failures"]:
                print(f"         - {f}")
        print()

    return {"pass_rate": pass_rate, "total": total, "valid": valid_count, "results": results}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    report = run_eval(verbose=True)
    sys.exit(0 if report["pass_rate"] == 1.0 else 1)


if __name__ == "__main__":
    main()
