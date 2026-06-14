# Day 18 — F2 v2: RAGAS Evaluation Baseline

**Date:** 2026-06-02
**Feature:** F2 — AI Summarisation v2
**KM:** #174 RAGAS
**Status:** Complete — baseline 0.685 (FAIL vs 0.75 target), failure modes identified

---

## What Was Built

| File | Purpose |
|------|---------|
| `evals/__init__.py` | Package stub |
| `evals/ragas_eval.py` | Eval harness — 4 metrics, entry scoring, aggregate report |
| `evals/baseline_report.json` | Machine-readable results (for CI pipeline Day 19) |
| `scripts/run_eval.py` | CLI: `python scripts/run_eval.py --entries 30 --save` |
| `docs/RAGAS-Baseline-Report-v1.md` | Human-readable baseline report |

---

## Baseline Results

Evaluated: 20 of 30 golden entries (10 not yet summarised from FinCEN/OCC/FDIC).

| Metric | Score | Target | Status |
|--------|-------|--------|--------|
| Faithfulness | 0.685 | ≥ 0.75 | **FAIL** |
| Hallucination rate | 0.100 | < 0.05 | FAIL |
| Answer relevance | 0.769 | — | INFO |
| Date accuracy | 0.900 | — | EXCELLENT |
| Institution accuracy | 0.800 | — | GOOD |
| No-action accuracy | 0.950 | — | EXCELLENT |

---

## The 4 Failure Modes (for Day 21 repair)

1. **Missing "no compliance required" explicit statement** (6 documents)
   Claude routes informational docs as DISMISS but doesn't always state "no compliance required" in the summary text → key_facts check fails.

2. **Missing specific regulatory citations** (2 documents)
   Claude summarises accurately but says "this regulation" instead of "the Interstate Land Sales Full Disclosure Act (ILSA)" → key_fact exact match fails.

3. **BEFORE/AFTER structure only 20% of rule docs**
   Prompt v2's instruction works on major rules but not minor/administrative ones.

4. **Hallucination: "community banks must"** (3 documents)
   Claude over-applies community bank framing to land developer or state-law regulations where it's not warranted.

---

## What's Working Well

- **Date accuracy: 0.900** — NER + hierarchical priority retrieval found dates in 9 of 10 documents. Massive improvement from ~32% keyword-only (Day 8).
- **No-action accuracy: 0.950** — Prompt v2 "No immediate action required" permission is working.
- **Institution accuracy: 0.800** — Reranker consistently retrieves institution-type chunks with asset thresholds.

---

## The Gap: 0.685 → 0.750 (need +0.065)

Three prompt changes on Day 21 will close the gap:
1. Mandatory "no compliance required" statement for informational docs (+0.03)
2. Specific regulatory citation requirement (+0.02)
3. Stricter BEFORE/AFTER enforcement (+0.01 + hallucination fix +0.01)

Projected post-fix faithfulness: **0.755 (PASS)**

---

## KM Concept: #174 RAGAS

RAGAS (Retrieval Augmented Generation Assessment) is a framework for evaluating RAG systems. The four original RAGAS metrics:
1. **Faithfulness** — claims in answer supported by context?
2. **Answer Relevance** — answer relevant to the question?
3. **Context Precision** — retrieved context relevant to the question?
4. **Context Recall** — were all relevant chunks retrieved?

We adapted this for compliance:
- Faithfulness → key_facts present in summary
- Answer Relevance → date accuracy + institution accuracy + routing accuracy
- Skipped Context Precision/Recall (we measure this via the embedding benchmark)
- Added: hallucination_rate, no_action_accuracy, what_changed_quality

The adaptation is more specific to our use case — and more deterministic (no LLM needed to judge).

---

## PM Insight

**The eval is the PM's scorecard.**

Before Day 18, every quality claim was judgment: "the reranker makes summaries better." After Day 18, it's measurement: faithfulness 0.685. The number is honest.

More importantly, the failure analysis tells you WHAT to fix. "Faithfulness is 0.685" is an engineering problem. "Claude doesn't name specific regulatory programs" is a prompt engineering problem — fixable in an afternoon. The eval converts a vague quality concern into an actionable fix list.

This is why "eval-first" is a build rule for this project. Without the golden set (Day 14B) and the eval harness (Day 18), we'd be shipping a product and hoping it's good enough. With the eval, we ship knowing exactly where it fails and having a plan to fix it.
