"""
RAGAS-style evaluation harness for F2 — Day 18.

KM concept: #174 RAGAS (Retrieval Augmented Generation Assessment)

Measures four metrics against the 50-entry golden set:

  1. FAITHFULNESS (0-1)
     Are all claims in the summary supported by the source document?
     Measured as: % of key_facts present in the summary.
     Target Week 3: >= 0.75   Target Day 45: >= 0.85

  2. HALLUCINATION RATE (0-1, lower is better)
     Did the summary invent facts not in the document?
     Measured as: % of must_not_contain items that ARE in the summary.
     Target: < 0.05 (less than 5% of summaries contain hallucinated claims)

  3. ANSWER RELEVANCE (0-1)
     Does the summary answer the compliance officer's core question?
     Measured as composite of:
       - Date extraction accuracy (effective_date correct?)
       - Institution type accuracy (correct institution types?)
       - Routing accuracy (correct DISMISS/REVIEW/APPROVE?)
       - No-action accuracy (correctly identified informational docs?)

  4. WHAT_CHANGED QUALITY (0-1)
     Does the what_changed field use the BEFORE/AFTER structure?
     Measured as: % of rule-change documents with "Previously:" in what_changed.

Why our own evaluator instead of the RAGAS library?
  The RAGAS Python library uses an LLM to judge faithfulness — adding cost
  and latency (another Claude call per document). Our golden set has human-
  labeled key_facts and must_not_contain. That IS the ground truth.
  Programmatic checking is deterministic, free, and uses our human judgment.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Scoring helpers ────────────────────────────────────────────────────────────

def _text_contains_fact(text: str, fact: str, threshold: float = 0.6) -> bool:
    """
    Check if a text contains a given fact.
    Uses multiple strategies: exact substring, keyword overlap, key phrase.
    threshold: minimum keyword overlap ratio (0-1).
    """
    text_lower = text.lower()
    fact_lower = fact.lower()

    # Strategy 1: Direct substring match
    if fact_lower in text_lower:
        return True

    # Strategy 2: Key phrase — remove stop words, check for significant keywords
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
        'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are',
        'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
        'did', 'will', 'would', 'could', 'should', 'may', 'might', 'shall',
        'this', 'that', 'these', 'those', 'it', 'its', 'not', 'no',
    }
    fact_words = [w for w in re.findall(r'\b\w+\b', fact_lower) if w not in stop_words and len(w) > 2]

    if not fact_words:
        return fact_lower in text_lower

    matches = sum(1 for w in fact_words if w in text_lower)
    overlap = matches / len(fact_words)

    return overlap >= threshold


def _date_matches(summary_date: Optional[str], expected_date: Optional[str]) -> bool:
    """True if dates match or both are null."""
    if expected_date is None and summary_date is None:
        return True
    if expected_date is None or summary_date is None:
        # One is null, other isn't — partial credit if expected is null
        return expected_date is None
    return summary_date.strip() == expected_date.strip()


def _institutions_match(summary_insts: list, expected_insts: list) -> float:
    """
    Score institution type accuracy (0-1).
    Partial credit: some overlap is better than none.
    """
    if not expected_insts:
        # No institutions expected — correct if summary also has none (or has some, which is fine)
        return 1.0

    if not summary_insts:
        return 0.0

    summary_text = " ".join(str(i).lower() for i in summary_insts)
    matches = 0
    for expected in expected_insts:
        key = expected.lower()
        # Check for key terms from expected institution type
        key_words = [w for w in key.split() if len(w) > 3 and w not in {'with', 'than', 'more', 'less'}]
        if any(w in summary_text for w in key_words[:3]):
            matches += 1

    return matches / len(expected_insts)


def _routing_matches(summary_routing: str, expected_routing: str) -> bool:
    """True if routing decisions match."""
    return summary_routing.lower() == expected_routing.lower()


def _has_no_action_correct(summary_why: str, expected_no_action: bool) -> bool:
    """Check if the no-action determination is correct."""
    why_lower = (summary_why or "").lower()
    summary_says_no_action = (
        "no immediate action" in why_lower or
        "no action required" in why_lower or
        "no action needed" in why_lower
    )
    return summary_says_no_action == expected_no_action


def _has_before_after(what_changed: str) -> bool:
    """True if what_changed uses BEFORE/AFTER structure."""
    text = (what_changed or "").lower()
    return "previously:" in text or "previously " in text


# ── Entry-level scoring ────────────────────────────────────────────────────────

@dataclass
class EntryScore:
    """Scores for one golden set entry."""
    entry_id: int
    title: str
    doc_type: str
    agency: str
    difficulty: str

    # Whether we found a summary for this entry
    summary_found: bool = False

    # Per-metric scores (None = not applicable or no summary)
    faithfulness: Optional[float] = None         # % key_facts present
    hallucination_rate: Optional[float] = None   # % must_not_contain items found (lower=better)
    date_accuracy: Optional[float] = None        # 1.0/0.5/0.0
    institution_accuracy: Optional[float] = None # overlap score
    routing_accuracy: Optional[float] = None     # 1.0 or 0.0
    no_action_accuracy: Optional[float] = None   # 1.0 or 0.0
    what_changed_quality: Optional[float] = None # 1.0 or 0.0 (BEFORE/AFTER present)

    # Raw details for debugging
    key_facts_found: list = field(default_factory=list)
    key_facts_missing: list = field(default_factory=list)
    hallucinations_found: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    @property
    def answer_relevance(self) -> Optional[float]:
        """Composite answer relevance score."""
        components = []
        if self.date_accuracy is not None:
            components.append(self.date_accuracy)
        if self.institution_accuracy is not None:
            components.append(self.institution_accuracy)
        if self.routing_accuracy is not None:
            components.append(self.routing_accuracy * 0.5)  # Lower weight
        if self.no_action_accuracy is not None:
            components.append(self.no_action_accuracy)
        return sum(components) / len(components) if components else None


def score_entry(entry: dict, summary: dict, routing_decision: str) -> EntryScore:
    """
    Score one golden set entry against its generated summary.
    Returns an EntryScore with all metric values populated.
    """
    es = EntryScore(
        entry_id=entry["id"],
        title=entry["title"][:60],
        doc_type=entry["doc_type"],
        agency=entry["agency"],
        difficulty=entry["difficulty"],
        summary_found=True,
    )

    # Build full summary text for searching
    summary_text = " ".join([
        summary.get("headline", ""),
        summary.get("plain_english_summary", ""),
        summary.get("what_changed", ""),
        summary.get("why_it_matters", ""),
        " ".join(summary.get("affected_institution_types") or []),
    ])

    # ── 1. Faithfulness (key_facts coverage) ──────────────────────────────────
    key_facts = entry.get("key_facts", [])
    if key_facts:
        found = []
        missing = []
        for fact in key_facts:
            if _text_contains_fact(summary_text, fact):
                found.append(fact)
            else:
                missing.append(fact)
        es.faithfulness = len(found) / len(key_facts)
        es.key_facts_found = found
        es.key_facts_missing = missing

    # ── 2. Hallucination rate (must_not_contain check) ────────────────────────
    must_not = entry.get("must_not_contain", [])
    if must_not:
        hallucinations = [item for item in must_not if _text_contains_fact(summary_text, item, threshold=0.8)]
        es.hallucination_rate = len(hallucinations) / len(must_not)
        es.hallucinations_found = hallucinations

    # ── 3. Date accuracy ───────────────────────────────────────────────────────
    expected_eff = entry.get("expected_effective_date")
    summary_eff = summary.get("effective_date")
    if _date_matches(summary_eff, expected_eff):
        es.date_accuracy = 1.0
    elif expected_eff and not summary_eff:
        es.date_accuracy = 0.0  # Missed a date that should be there
        es.notes.append(f"Missed effective_date: expected {expected_eff}, got null")
    elif not expected_eff and summary_eff:
        es.date_accuracy = 0.5  # Invented a date when none expected
        es.notes.append(f"Invented effective_date: got {summary_eff}, expected null")
    else:
        es.date_accuracy = 0.0
        es.notes.append(f"Wrong date: expected {expected_eff}, got {summary_eff}")

    # ── 4. Institution accuracy ────────────────────────────────────────────────
    expected_insts = entry.get("expected_institution_types", [])
    summary_insts = summary.get("affected_institution_types") or []
    es.institution_accuracy = _institutions_match(summary_insts, expected_insts)

    # ── 5. Routing accuracy ────────────────────────────────────────────────────
    expected_routing = entry.get("routing_expected", "")
    if expected_routing:
        es.routing_accuracy = 1.0 if _routing_matches(routing_decision, expected_routing) else 0.0
        if es.routing_accuracy == 0.0:
            es.notes.append(f"Wrong routing: expected {expected_routing}, got {routing_decision}")

    # ── 6. No-action accuracy ──────────────────────────────────────────────────
    expected_no_action = entry.get("no_action_required", False)
    why_it_matters = summary.get("why_it_matters", "")
    es.no_action_accuracy = 1.0 if _has_no_action_correct(why_it_matters, expected_no_action) else 0.0

    # ── 7. What-changed quality ────────────────────────────────────────────────
    # Only check for rule-change documents (not informational)
    if entry["doc_type"] in ("final_rule", "proposed_rule", "enforcement", "guidance"):
        what_changed = summary.get("what_changed", "")
        es.what_changed_quality = 1.0 if _has_before_after(what_changed) else 0.0

    return es


# ── Aggregate scoring ──────────────────────────────────────────────────────────

@dataclass
class EvalReport:
    """Aggregate results across all scored entries."""
    total_golden_entries: int = 0
    summaries_found: int = 0
    summaries_missing: int = 0

    # Aggregate metrics (averages across all scored entries)
    avg_faithfulness: float = 0.0
    avg_hallucination_rate: float = 0.0
    avg_answer_relevance: float = 0.0
    avg_date_accuracy: float = 0.0
    avg_institution_accuracy: float = 0.0
    avg_routing_accuracy: float = 0.0
    avg_no_action_accuracy: float = 0.0
    avg_what_changed_quality: float = 0.0

    # Pass/fail against targets
    faithfulness_target: float = 0.75
    faithfulness_passes: bool = False

    # Per-difficulty breakdown
    by_difficulty: dict = field(default_factory=dict)

    # Per-doc-type breakdown
    by_doc_type: dict = field(default_factory=dict)

    # Individual entry scores (for detailed report)
    entry_scores: list = field(default_factory=list)

    # Top failures (for Day 21 repair)
    top_failures: list = field(default_factory=list)


def aggregate_scores(entry_scores: list[EntryScore]) -> EvalReport:
    """Compute aggregate metrics from a list of entry scores."""
    report = EvalReport(
        total_golden_entries=len(entry_scores),
        entry_scores=entry_scores,
    )

    scored = [e for e in entry_scores if e.summary_found]
    report.summaries_found = len(scored)
    report.summaries_missing = len(entry_scores) - len(scored)

    if not scored:
        return report

    def avg(values):
        vals = [v for v in values if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    report.avg_faithfulness = avg(e.faithfulness for e in scored)
    report.avg_hallucination_rate = avg(e.hallucination_rate for e in scored)
    report.avg_answer_relevance = avg(e.answer_relevance for e in scored)
    report.avg_date_accuracy = avg(e.date_accuracy for e in scored)
    report.avg_institution_accuracy = avg(e.institution_accuracy for e in scored)
    report.avg_routing_accuracy = avg(e.routing_accuracy for e in scored)
    report.avg_no_action_accuracy = avg(e.no_action_accuracy for e in scored)
    report.avg_what_changed_quality = avg(
        e.what_changed_quality for e in scored if e.what_changed_quality is not None
    )

    report.faithfulness_passes = report.avg_faithfulness >= report.faithfulness_target

    # By difficulty
    for diff in ("easy", "medium", "hard"):
        diff_scores = [e for e in scored if e.difficulty == diff]
        if diff_scores:
            report.by_difficulty[diff] = {
                "count": len(diff_scores),
                "faithfulness": avg(e.faithfulness for e in diff_scores),
                "answer_relevance": avg(e.answer_relevance for e in diff_scores),
            }

    # By doc type
    for dt in set(e.doc_type for e in scored):
        dt_scores = [e for e in scored if e.doc_type == dt]
        report.by_doc_type[dt] = {
            "count": len(dt_scores),
            "faithfulness": avg(e.faithfulness for e in dt_scores),
            "answer_relevance": avg(e.answer_relevance for e in dt_scores),
        }

    # Top failures: entries with lowest faithfulness
    failures = sorted(
        [e for e in scored if e.faithfulness is not None and e.faithfulness < 0.75],
        key=lambda e: e.faithfulness or 0,
    )
    report.top_failures = [
        {
            "id": e.entry_id,
            "title": e.title,
            "faithfulness": e.faithfulness,
            "missing_facts": e.key_facts_missing[:3],
            "hallucinations": e.hallucinations_found,
            "notes": e.notes,
        }
        for e in failures[:5]
    ]

    return report


# ── Main runner ────────────────────────────────────────────────────────────────

def run_eval(
    golden_set_path: str,
    num_entries: int = 30,
    verbose: bool = True,
) -> EvalReport:
    """
    Run the RAGAS evaluation against the golden set.

    Args:
        golden_set_path: Path to fixtures/golden/summaries.json
        num_entries:     Number of golden entries to evaluate (roadmap: 30)
        verbose:         Print progress

    Returns:
        EvalReport with all metrics computed.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from sqlmodel import select
    from src.database import get_session
    from src.models import RegulatoryDocument, DocStatus

    # Load golden set
    with open(golden_set_path, encoding="utf-8") as f:
        golden_data = json.load(f)

    entries = golden_data["entries"][:num_entries]

    # Load all summarised documents from DB
    with get_session() as session:
        all_docs = session.exec(
            select(RegulatoryDocument).where(
                RegulatoryDocument.status == DocStatus.SUMMARISED
            )
        ).all()

    # Build lookup: first 8 chars of doc_id → document
    doc_lookup = {d.id[:8]: d for d in all_docs if d.summary_json}

    if verbose:
        print(f"\n{'='*65}")
        print(f"RAGAS EVALUATION — Day 18 Baseline")
        print(f"{'='*65}")
        print(f"Golden entries: {len(entries)}")
        print(f"Summaries in DB: {len(doc_lookup)}")
        print(f"{'='*65}\n")

    entry_scores: list[EntryScore] = []

    for entry in entries:
        # Match by first 8 chars of doc_id
        doc_id_prefix = (entry.get("doc_id") or "")[:8]
        doc = doc_lookup.get(doc_id_prefix)

        if not doc or not doc.summary_json:
            es = EntryScore(
                entry_id=entry["id"],
                title=entry["title"][:60],
                doc_type=entry["doc_type"],
                agency=entry["agency"],
                difficulty=entry["difficulty"],
                summary_found=False,
            )
            entry_scores.append(es)
            if verbose:
                print(f"  [{entry['id']:>2}] SKIP  {entry['title'][:50]} (no summary)")
            continue

        try:
            summary = json.loads(doc.summary_json)
            routing = summary.get("_routing_decision", "unknown")
            es = score_entry(entry, summary, routing)
            entry_scores.append(es)

            if verbose:
                faith_str = f"{es.faithfulness:.2f}" if es.faithfulness is not None else "N/A"
                rel_str = f"{es.answer_relevance:.2f}" if es.answer_relevance is not None else "N/A"
                status = "PASS" if (es.faithfulness or 0) >= 0.75 else "FAIL"
                print(f"  [{entry['id']:>2}] {status}  faith={faith_str} rel={rel_str}  "
                      f"[{entry['difficulty']:<6}] {entry['title'][:40]}")
                if es.key_facts_missing and verbose:
                    for mf in es.key_facts_missing[:2]:
                        print(f"           MISSING: {mf[:60]}")
                if es.hallucinations_found:
                    for h in es.hallucinations_found:
                        print(f"           HALLUC:  {h[:60]}")

        except Exception as exc:
            if verbose:
                print(f"  [{entry['id']:>2}] ERROR {entry['title'][:40]}: {exc}")
            es = EntryScore(
                entry_id=entry["id"], title=entry["title"][:60],
                doc_type=entry["doc_type"], agency=entry["agency"],
                difficulty=entry["difficulty"], summary_found=False,
            )
            entry_scores.append(es)

    report = aggregate_scores(entry_scores)

    if verbose:
        _print_report(report)

    return report


def _print_report(report: EvalReport) -> None:
    """Print the evaluation report to console."""
    print(f"\n{'='*65}")
    print("RAGAS BASELINE REPORT")
    print(f"{'='*65}")
    print(f"Entries evaluated: {report.summaries_found}/{report.total_golden_entries}")
    print(f"Entries missing:   {report.summaries_missing} (not yet summarised)")
    print()

    target = report.faithfulness_target
    pass_str = "PASS" if report.faithfulness_passes else "FAIL"
    print(f"  Faithfulness:        {report.avg_faithfulness:.3f}  (target >= {target}) [{pass_str}]")
    print(f"  Hallucination rate:  {report.avg_hallucination_rate:.3f}  (target < 0.05)")
    print(f"  Answer relevance:    {report.avg_answer_relevance:.3f}")
    print(f"  Date accuracy:       {report.avg_date_accuracy:.3f}")
    print(f"  Institution accuracy:{report.avg_institution_accuracy:.3f}")
    print(f"  Routing accuracy:    {report.avg_routing_accuracy:.3f}")
    print(f"  No-action accuracy:  {report.avg_no_action_accuracy:.3f}")
    print(f"  What-changed (B/A):  {report.avg_what_changed_quality:.3f}")

    if report.by_difficulty:
        print(f"\n  By difficulty:")
        for diff, scores in sorted(report.by_difficulty.items()):
            print(f"    {diff:<8} n={scores['count']}  "
                  f"faithfulness={scores['faithfulness']:.3f}  "
                  f"relevance={scores['answer_relevance']:.3f}")

    if report.by_doc_type:
        print(f"\n  By doc type:")
        for dt, scores in sorted(report.by_doc_type.items()):
            print(f"    {dt:<16} n={scores['count']}  "
                  f"faithfulness={scores['faithfulness']:.3f}")

    if report.top_failures:
        print(f"\n  Top failures (faithfulness < 0.75):")
        for f in report.top_failures:
            print(f"    [{f['id']}] faith={f['faithfulness']:.2f}  {f['title'][:45]}")
            for mf in f['missing_facts'][:2]:
                print(f"          Missing: {mf[:55]}")

    overall = "PASS" if report.faithfulness_passes else "FAIL"
    print(f"\n  OVERALL: {overall} (faithfulness {report.avg_faithfulness:.3f} vs target {report.faithfulness_target})")
    print(f"{'='*65}\n")
