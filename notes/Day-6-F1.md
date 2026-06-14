# Day 6 — F1 Scheduler & Golden Evaluation Set

**Date:** 2026-06-01  
**Feature:** F1 — Regulatory Feed Monitoring  
**Status:** Complete — automated daily pipeline + 10-document golden eval set ready for F2

---

## What Was Built

| File | Purpose |
|------|---------|
| `scripts/run_daily.py` | Single entry-point for the daily pipeline. Logs to `logs/daily_run.log`. |
| `scripts/schedule_daily.py` | Registers / removes / checks the Windows Task Scheduler task. |
| `fixtures/golden/f1_golden_set.json` | 10 hand-labeled documents — ground truth for F2 eval. |
| `logs/` | Created automatically on first run. Contains `daily_run.log`. |

---

## Why Each Decision Was Made

### Why a dedicated `run_daily.py` instead of calling an existing script?

Task Scheduler needs a fixed file path it calls forever. If we pointed it at `daily_validate.py`, adding F2 summarisation to the daily run (Week 2) would require modifying the scheduled task configuration. With `run_daily.py` as the stable entry point, we just add the F2 call inside it — the Task Scheduler config never changes.

### Why Windows Task Scheduler over Python-based scheduling (APScheduler, schedule)?

Task Scheduler is built into Windows, starts automatically on boot, requires no background process to stay alive, and is visible in the Windows Task Scheduler UI for non-technical inspection. A Python scheduler would require a long-running process — if the laptop restarts, it stops. Task Scheduler doesn't have that problem. It's the right tool for a single-machine MVP.

### Why hand-label the golden set instead of generating labels with Claude?

The golden set is ground truth — it represents what *correct* looks like independent of the model being tested. If Claude generates the labels and Claude produces the summaries, we're measuring self-consistency, not accuracy. The labels were written by reading the actual document text (not trusting the abstract), which is the only way to catch hallucination: when the AI says something the source document doesn't.

### Why 10 documents, not 50?

10 is enough to catch systematic prompt failures (always inventing dates, always misclassifying enforcement actions). It's labelled carefully — each entry was written from the real document content. A 50-document set with rushed labels would be worse than a 10-document set with accurate ones. We grow to 50 in Week 3 once F2's baseline prompt is established.

### Why include documents with `doc_id: null`?

Three golden set entries use the URL as their identifier because those documents weren't enriched with full text when the golden set was created. The eval harness will match on URL. This is intentional — it tests that the eval can handle partial DB state gracefully.

---

## AI/ML Concept Applied

**Eval-first development:**

The golden set is built *before* any F2 code is written. This is eval-first development — define what success looks like before you build the thing that's supposed to succeed.

Why does order matter? Because if you build first and eval second, you unconsciously design the eval around what your model already does well. The eval confirms your choices rather than challenging them. Building the eval first forces you to be honest: "What would a compliance officer actually need this summary to say?"

The `eval_instructions` section of the golden set makes this explicit:
- **Faithfulness**: no invented facts
- **Relevance**: answers the compliance officer's actual question
- **Doc type accuracy**: misclassifying proposed vs final rule is high-severity
- **Date extraction**: invented dates are worse than null

These are acceptance criteria, not metrics. F2 is done when it passes them — not when the loss curve looks good.

---

## How to Run

```bash
# Run the daily pipeline manually
python scripts/run_daily.py

# Check the log from the last run
type logs\daily_run.log

# Register the scheduled task (7 AM daily)
python scripts/schedule_daily.py

# Change the schedule time
python scripts/schedule_daily.py --time 06:30

# Check if the task is registered
python scripts/schedule_daily.py --status

# Remove the scheduled task
python scripts/schedule_daily.py --remove
```

---

## Scheduled Task Details

```
Task name:   RegWatch-AI-Daily
Schedule:    Daily at 07:00 AM
Next run:    2026-06-02 07:00:00
Status:      Ready
Log file:    logs/daily_run.log
```

---

## Golden Set Summary

| # | Agency | Doc Type | Key Label Challenge |
|---|--------|----------|---------------------|
| 1 | CFPB | final_rule | Compliance deadline varies by institution size |
| 2 | CFPB | proposed_rule | Comment deadline, not compliance deadline |
| 3 | Fed | enforcement | Individual action — no institutional compliance required |
| 4 | Fed | enforcement | Short document — high confidence expected |
| 5 | Fed | guidance | Living will feedback — large banks only |
| 6 | Fed | proposed_rule | Payment account proposal — comment period |
| 7 | CFPB | other | Admin SORN — low impact, lower confidence floor |
| 8 | Fed | other | FOMC statement — rates held, ALM implications |
| 9 | Fed | guidance | Interstate loan-to-deposit ratios — specific numbers required |
| 10 | Fed | other | SHED report — informational, lower urgency |

**Passing threshold for F2:** RAGAS faithfulness ≥ 0.85 AND answer_relevance ≥ 0.80 across all 10.

---

## PM Insight

**The golden set is the product's acceptance test.**

When you're pitching RegWatch AI to Sarah (CCO), she won't ask to see your RAGAS score. She'll ask: "Show me how it handles an enforcement action." "Show me what it does with a proposed rule." "Does it correctly say there's no compliance deadline for an FOMC statement?"

Every entry in the golden set is a question Sarah would ask. Entry 3 (enforcement action against an individual) tests whether the AI correctly tells Sarah "no action required for your institution" rather than creating a false-alarm compliance task. Entry 1 (CFPB Reg B) tests whether it surfaces the tiered compliance deadline rather than inventing a single date.

The golden set is where product requirements become measurable engineering criteria. F2 is not done until it passes all 10.
