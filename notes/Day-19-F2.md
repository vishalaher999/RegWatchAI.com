# Day 19 — F2 v2: Golden Set CI + ROI Calculator

**Date:** 2026-06-02
**Feature:** F2 — AI Summarisation v2
**KM:** #246 Golden Dataset
**Status:** Complete — CI gate live, ROI calculator built, golden set v1 confirmed

---

## What Was Built

| File | Purpose |
|------|---------|
| `tests/test_f2_eval_ci.py` | 4 pytest tests with @pytest.mark.eval — CI quality gate |
| `scripts/roi_calculator.py` | ROI calculator with Sarah persona defaults |
| `docs/ROI-Calculator-v1.md` | Output: $205K total value, pays back in < 1 week |

---

## CI Gate Results

```
pytest tests/test_f2_eval_ci.py -m eval -v

test_f2_faithfulness_above_floor     FAILED  (0.685 < 0.70 floor)
test_f2_hallucination_rate_below...  PASSED  (0.100 < 0.15 ceiling)
test_f2_answer_relevance_above...    PASSED  (0.769 > 0.65 floor)
test_f2_golden_set_integrity         PASSED  (50 entries, all valid)
```

**Faithfulness CI: RED.** This is correct — we're at 0.685, below the 0.70 floor. The CI gate is working exactly as designed. Day 21 (prompt fixes) will turn it green.

---

## CI Architecture

```
pytest tests/             → 90 fast tests (no eval, no slow)
pytest tests/ -m eval     → 4 RAGAS eval tests (CI quality gate)
pytest tests/ -m slow     → 7 live integration tests (hit real feeds)
pytest tests/ -m ""       → all 101 tests
```

Thresholds:
- Faithfulness floor: 0.70 (below this = regression, block deploy)
- Hallucination ceiling: 0.15 (above this = hallucinating institutional obligations)
- Answer relevance floor: 0.65 (below this = summaries not answering compliance questions)
- Min entries: 15 (fewer than this = meaningless eval)

---

## ROI Calculator Results (Sarah persona)

| Metric | Value |
|--------|-------|
| Hours saved/officer/month | 29.1 hrs |
| Hours saved/year total | 699 hrs (0.34 FTE) |
| Labour savings/year | $28,559 |
| RegWatch cost/year | $23,988 |
| Net labour savings | $4,571 |
| Risk reduction/year | $176,400 |
| Total value/year | $204,959 |
| Payback period | < 1 week |

The labour savings alone (19% ROI) are a defensible floor — any sceptical CFO can verify the math. The risk reduction ($176K) is the upside that makes the conversation interesting.

---

## KM Concept: #246 Golden Dataset

A golden dataset is a labeled set of examples that defines "correct" behaviour. It serves three purposes in production:

1. **Development feedback** — during active development, run the eval after each change to see if you improved or regressed
2. **CI gate** — in production, block deployments if the golden set score drops below a floor
3. **Product compass** — the golden set encodes product judgment ("for THIS document, a correct summary MUST contain these facts")

The key property: a golden dataset must be **stable**. If you change the ground truth labels frequently, the CI gate becomes meaningless — you're just moving the goalposts. Our golden set was hand-labeled in one session (Day 14B) and should only be updated when the product specification itself changes (e.g., when F2 adds new summary fields).

**When to update the golden set:**
- New F2 output fields added → add those fields to key_facts for affected entries
- Summary quality target changes (0.75 → 0.85) → add more stringent key_facts
- New document type patterns discovered → add entries covering that pattern

**Never update golden labels to pass the eval.** If the eval fails, fix the code, not the labels.

---

## PM Insight

**The ROI calculator is the product's mirror.**

When you show Sarah the ROI calculator with her numbers ($0.5B bank, 2 officers, $85K salary), two things happen:

1. She stops thinking about "is this AI tool good?" and starts thinking "what is my time worth?" — a question that always has a big number answer.

2. You've implicitly committed to the value proposition. If she buys and doesn't save those hours, the renewal conversation is hard. If she does save them, renewal is easy.

The calculator is also a sales tool in Mike's (consultant's) hands. He can run it for each of his 8 clients with their specific numbers. That's 8 individualised ROI cases made in 8 minutes — a more powerful sales tool than any product demo.

The ROI calculation that matters most is the one in the footnotes: compliance officers cost $41/hour. RegWatch saves 30 hours/month per officer. That's $1,230/month in labour value from one officer alone — already more than the $1,999 plan price when you include the second officer and the risk reduction.

Sarah doesn't need to do that math. She just needs to see the output with her numbers on it.
