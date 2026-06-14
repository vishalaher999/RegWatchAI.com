# Metrics Dashboard — F2 Quality Monitoring
# Version 1 | Day 20 | Override Rate + Confidence + Judge Scores

## Who This Dashboard Serves

Mike (risk manager) needs to know at a glance:
  - Is the AI performing well this week?
  - How many summaries needed human correction?
  - Are there patterns in what's failing?

Sarah (CCO) needs:
  - How much of my queue do I actually need to review?
  - Is the AI getting better or worse over time?

─────────────────────────────────────────────────────────────────────
METRICS DASHBOARD WIREFRAME
─────────────────────────────────────────────────────────────────────

┌──────────────────────────────────────────────────────────────────────┐
│  REGWATCH AI — QUALITY METRICS                Last 30 days           │
│  ────────────────────────────────────────────────────────────────── │
│                                                                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │
│  │ Summaries  │ │ Auto-      │ │ Override   │ │ Avg        │       │
│  │ Generated  │ │ Dismissed  │ │ Rate       │ │ Confidence │       │
│  │    25      │ │   16 (64%) │ │   24%      │ │  76/100    │       │
│  │            │ │            │ │ [TARGET<20%│ │            │       │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │
│                                                                      │
│  ── CONFIDENCE DISTRIBUTION ─────────────────────────────────────── │
│                                                                      │
│  90-100 (HIGH)    ██░░░░░░░░░░░░░░░░░░░  3 summaries (12%)         │
│  80-89  (GOOD)    ████░░░░░░░░░░░░░░░░░  4 summaries (16%)         │
│  70-79  (MODERATE)███░░░░░░░░░░░░░░░░░░  2 summaries (8%)          │
│  60-69  (LOW)     ████████░░░░░░░░░░░░░  8 summaries (32%)         │
│  <60    (VERY LOW)████░░░░░░░░░░░░░░░░░  4 summaries (16%)         │
│  DISMISSED         (auto — informational)  4 summaries (16%)        │
│                                                                      │
│  ── OVERRIDE RATE BY DOC TYPE ───────────────────────────────────── │
│                                                                      │
│  Final Rule     ████████████░░░░░░░░░  0 overrides / 0 approved    │
│  Proposed Rule  ████░░░░░░░░░░░░░░░░░  0 overrides / 0 approved    │
│  Enforcement    ████████░░░░░░░░░░░░░  2 overrides / 4 total       │
│  Guidance       ░░░░░░░░░░░░░░░░░░░░░  0 overrides / 1 total       │
│  Other (dismiss)                        auto-dismissed              │
│                                                                      │
│  ── JUDGE SCORES TREND (last 7 days) ─────────────────────────────  │
│                                                                      │
│  Faithfulness:  [Mon 1.0] [Tue 1.0] [Wed 0.9] [Thu 1.0] [Fri 1.0] │
│  Action clarity:[Mon 0.8] [Tue 0.9] [Wed 0.8] [Thu 0.9] [Fri 1.0] │
│  Date precision:[Mon 1.0] [Tue 1.0] [Wed 1.0] [Thu 0.5] [Fri 1.0] │
│                                                                      │
│  ── TOP FAILURE PATTERNS ─────────────────────────────────────────  │
│                                                                      │
│  1. Missing "no compliance required" for informational docs  (6×)   │
│  2. Missing specific regulatory citations (ILSA, Reg V)      (2×)   │
│  3. No BEFORE/AFTER structure in what_changed                (4×)   │
│                                                                      │
│  [View Full Report]  [Download CSV]  [Run Eval]                     │
└──────────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
TWO FAITHFULNESS DEFINITIONS — CRITICAL FINDING (Day 20)
─────────────────────────────────────────────────────────────────────

The calibration revealed that "faithfulness" means different things
to the keyword evaluator and the LLM judge:

KEYWORD EVAL (Day 18):
  Faithfulness = "Did the summary say the required things?"
  Measures: % of key_facts present in summary text
  Low score = summary omitted important facts from golden labels
  Example: 0.50 because "Personnel announcement" wasn't in summary

LLM JUDGE (Day 20):
  Faithfulness = "Did the summary invent facts not in the document?"
  Measures: are claims supported by the source text?
  Score = 1.0 for all our summaries — they don't hallucinate
  Example: 1.0 because summary only states things that are in the doc

CONCLUSION:
  Our summaries are FAITHFUL (no hallucination) but INCOMPLETE
  (missing some expected key facts). These are different problems.
  
  The right metric for the CI gate is COMPLETENESS not FAITHFULNESS.
  Rename Day 19 metric to "completeness" in v2 of the eval.

DASHBOARD IMPLICATION:
  Show BOTH metrics:
  - Completeness: 0.685 (missing required facts) ← our keyword metric
  - Hallucination rate: 0.100 (invented facts) ← from must_not_contain check
  - Judge faithfulness: 1.000 (no invented facts) ← LLM judge

─────────────────────────────────────────────────────────────────────
METRICS TO SHOW (updated after calibration insight)
─────────────────────────────────────────────────────────────────────

For Mike's overview dashboard:

| Metric | What it means | Target |
|--------|---------------|--------|
| Summary completeness | Did AI capture all required facts? | >= 0.75 |
| Hallucination rate | Did AI invent facts? | < 0.05 |
| Judge faithfulness | Claude Haiku: no invented facts? | >= 0.90 |
| Auto-dismiss rate | Informational docs correctly identified | -- |
| Override rate | Summaries edited by Sarah before use | < 20% |
| Avg confidence | Model's self-reported certainty | -- |
