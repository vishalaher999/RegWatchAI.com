"""
F2 RAGAS evaluation CI gate — Day 19.

Runs the full RAGAS evaluation against the golden set and asserts
that quality metrics stay above the defined CI floor.

This test is marked @pytest.mark.eval — excluded from the default fast test run.

Run commands:
    pytest tests/test_f2_eval_ci.py -m eval -v     # CI gate only
    pytest tests/ -m "not eval"                     # fast tests only (default)
    pytest tests/ -m ""                             # everything including CI gate

CI floor thresholds:
    faithfulness >= 0.70    (Week 3 target is 0.75; floor is 0.70 to allow dev iteration)
    hallucination_rate < 0.15  (target is 0.05; floor allows for active debugging)
    answer_relevance >= 0.65

Why 0.70 not 0.75?
    The CI gate is a regression detector, not a quality target.
    0.75 is the Week 3 goal fixed on Day 21.
    0.70 catches genuine regressions (a bug in the retriever, a broken prompt)
    without blocking active prompt iteration.
    Setting CI too tight makes every dev commit block on quality — counterproductive.

What triggers a CI failure?
    - Prompt changes that break key_fact extraction
    - Chunker changes that fragment compliance-critical sections
    - Retriever changes that stop finding date/institution chunks
    - Reranker changes that deprioritise relevant content
    - Any change that makes Claude hallucinate institution obligations

How to fix a CI failure:
    1. Run: python scripts/run_eval.py --entries 30 --save
    2. Read evals/baseline_report.json for the specific failure
    3. Check top_failures for which entries dropped
    4. Fix the root cause (prompt, chunker, retriever)
    5. Re-run until CI passes
"""

import json
import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── CI thresholds ──────────────────────────────────────────────────────────────
FAITHFULNESS_FLOOR     = 0.70   # Must not drop below this — ever
HALLUCINATION_CEILING  = 0.15   # Must not exceed this
ANSWER_RELEVANCE_FLOOR = 0.65   # Composite answer quality floor
MIN_ENTRIES_EVALUATED  = 15     # Must evaluate at least this many entries

GOLDEN_SET_PATH = "fixtures/golden/summaries.json"
BASELINE_REPORT = "evals/baseline_report.json"


@pytest.mark.eval
def test_f2_faithfulness_above_floor():
    """
    Core CI gate: F2 faithfulness must stay >= 0.70.

    This test protects against regressions in:
      - Prompt quality (prompt changes that break key_fact coverage)
      - Chunking (changes that fragment compliance-critical sections)
      - Retrieval (changes that stop finding date/institution chunks)
    """
    from evals.ragas_eval import run_eval

    report = run_eval(
        golden_set_path=GOLDEN_SET_PATH,
        num_entries=30,
        verbose=False,
    )

    assert report.summaries_found >= MIN_ENTRIES_EVALUATED, (
        f"CI requires at least {MIN_ENTRIES_EVALUATED} summaries to be meaningful. "
        f"Only {report.summaries_found} found. "
        f"Run: python -m src.f2_summarise.run --limit 30"
    )

    assert report.avg_faithfulness >= FAITHFULNESS_FLOOR, (
        f"Faithfulness regression detected: {report.avg_faithfulness:.3f} < {FAITHFULNESS_FLOOR}\n"
        f"Top failures:\n" +
        "\n".join(
            f"  [{f['id']}] faith={f['faithfulness']:.2f}: {f['title']}"
            for f in report.top_failures[:3]
        ) +
        f"\n\nRun 'python scripts/run_eval.py --entries 30' for full diagnosis."
    )


@pytest.mark.eval
def test_f2_hallucination_rate_below_ceiling():
    """
    Claude must not invent institution obligations where the document doesn't support them.
    Must_not_contain items (from golden set) must NOT appear in summaries.
    """
    from evals.ragas_eval import run_eval

    report = run_eval(
        golden_set_path=GOLDEN_SET_PATH,
        num_entries=30,
        verbose=False,
    )

    assert report.avg_hallucination_rate <= HALLUCINATION_CEILING, (
        f"Hallucination rate too high: {report.avg_hallucination_rate:.3f} > {HALLUCINATION_CEILING}\n"
        f"Claude is inventing institution obligations not in the source document.\n"
        f"Check must_not_contain failures in: python scripts/run_eval.py --entries 30"
    )


@pytest.mark.eval
def test_f2_answer_relevance_above_floor():
    """
    Summaries must answer the compliance officer's core question:
    what changed, who is affected, what must they do by when.
    """
    from evals.ragas_eval import run_eval

    report = run_eval(
        golden_set_path=GOLDEN_SET_PATH,
        num_entries=30,
        verbose=False,
    )

    assert report.avg_answer_relevance >= ANSWER_RELEVANCE_FLOOR, (
        f"Answer relevance too low: {report.avg_answer_relevance:.3f} < {ANSWER_RELEVANCE_FLOOR}\n"
        f"Composite of: date_accuracy={report.avg_date_accuracy:.3f}, "
        f"institution_accuracy={report.avg_institution_accuracy:.3f}, "
        f"routing_accuracy={report.avg_routing_accuracy:.3f}"
    )


@pytest.mark.eval
def test_f2_golden_set_integrity():
    """
    Verify the golden set file is valid and has the expected structure.
    This catches accidental corruption of the ground truth labels.
    """
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        data = json.load(f)

    assert "entries" in data, "Golden set missing 'entries' key"
    entries = data["entries"]
    assert len(entries) >= 30, f"Expected >= 30 entries, got {len(entries)}"

    required_fields = ["id", "title", "agency", "doc_type", "difficulty",
                       "key_facts", "routing_expected", "no_action_required"]
    for entry in entries[:30]:
        for field in required_fields:
            assert field in entry, (
                f"Entry {entry.get('id', '?')} missing required field: {field}"
            )
        assert len(entry["key_facts"]) >= 2, (
            f"Entry {entry['id']} has fewer than 2 key_facts — labels are too sparse"
        )
