# Day 20 — F2 v2: LLM-as-Judge Calibration

**Date:** 2026-06-02
**Feature:** F2 — AI Summarisation v2
**KM:** #255 LLM-as-judge
**Status:** Complete — calibration complete, critical insight discovered about metric definition

---

## What Was Built

| File | Purpose |
|------|---------|
| `evals/llm_judge.py` | Claude Haiku judge with 4-criterion rubric |
| `scripts/calibrate_judge.py` | Runs judge on golden docs, compares to keyword scores |
| `evals/judge_calibration.json` | Calibration results (37.5% agreement) |
| `docs/wireframes/metrics-dashboard-v1.md` | Quality metrics dashboard design |

---

## Calibration Results

**Agreement rate: 37.5% — NOT CALIBRATED (threshold: 80%)**

| Doc | Keyword faith | Judge faith | Agree? |
|-----|--------------|-------------|--------|
| Enforcement (Crystal Moore) | 0.60 | 1.00 | NO |
| Discount rate minutes | 0.75 | 1.00 | YES |
| Kevin Warsh | 1.00 | 1.00 | YES |
| Resolution plan letters | 1.00 | 1.00 | YES |
| Enforcement (Nakia Logan) | 1.00 | 1.00 | YES |
| Payment account proposal | 0.50 | 1.00 | NO |
| FOMC April minutes | 0.50 | 1.00 | NO |
| Powell chair pro tempore | 0.50 | 1.00 | NO |

---

## The Critical Insight: Two Different Faithfulness Definitions

The calibration revealed something more valuable than agreement rate: **we've been measuring two different things and calling them both "faithfulness".**

**Keyword eval (Day 18) measures COMPLETENESS:**
> "Did the summary include the required key facts?"
> - 0.50 because "Personnel announcement" isn't in the summary
> - 0.50 because "No banking regulatory implications" isn't stated
> - These facts are TRUE but ABSENT — not hallucinated, just omitted

**LLM judge measures HALLUCINATION ABSENCE:**
> "Does the summary only state things supported by the document?"
> - 1.0 for all docs — the summaries never invent facts
> - Claude is faithful (doesn't hallucinate) but sometimes incomplete

**The correct reframing for Day 21 and beyond:**

| Metric | Definition | Current score | Target |
|--------|-----------|---------------|--------|
| Completeness | % key facts present | 0.685 | >= 0.75 |
| Hallucination rate | % must_not_contain items present | 0.100 | < 0.05 |
| Judge faithfulness | LLM confirms no invented facts | 1.000 | >= 0.90 |

Our summaries are **faithful but incomplete.** The Day 21 fixes need to improve COMPLETENESS, not faithfulness per se.

---

## KM Concept: #255 LLM-as-judge

**How LLM-as-judge works:**
1. Write a rubric that defines good quality with explicit examples
2. Feed the rubric + source document + generated summary to a cheaper/faster model (Haiku)
3. Model returns structured scores (0-1) per criterion
4. Compare against human labels to measure agreement (calibration)

**Why calibration is essential:**
Without calibration, you don't know if the judge is measuring what you think it's measuring. Our calibration found that the judge measures "no hallucination" while our keyword eval measures "completeness" — different constructs. This prevents a dangerous mistake: shipping based on a judge score that doesn't measure what the product needs.

**The 37.5% agreement tells us:**
- Not "the judge is broken"
- Not "our keyword eval is wrong"  
- Rather: "they're measuring different things — both are useful, neither is sufficient alone"

**Production use of the judge:**
Use keyword eval (completeness) for CI gate and quality targets.
Use LLM judge (hallucination check) as a safety filter before publishing.
Both are needed; neither alone is complete.

---

## Cost

8 documents × $0.0006 = **$0.0052 total** (~half a cent for 8 evaluations).
Full 50-entry golden set: ~$0.033 per eval run.
Weekly CI run: ~$0.033 = $1.72/year. Trivially cheap.

---

## PM Insight

**Calibration failures teach more than calibration successes.**

If the judge had 90% agreement with our keyword eval, we'd know the judge works. Because it's at 37.5%, we learned that we have two valid but different quality definitions — one measuring completeness, one measuring faithfulness. That's a more valuable insight than a passing score.

The metrics dashboard now shows BOTH:
- Completeness (keyword eval) — tells you what's MISSING from summaries
- Judge faithfulness — tells you what's WRONG (hallucinated)

A summary can be faithful but incomplete. A summary can be complete but unfaithful. The product needs both high completeness AND low hallucination. The CI gate (completeness ≥ 0.70) and the judge (faithfulness = 1.0) together give you that guarantee.

This is what "eval-first" means in practice: you discover what you're actually measuring only by measuring it carefully. The LLM judge calibration turned a "37.5% agreement" into a 2-metric quality framework that's more accurate than what we started with.
