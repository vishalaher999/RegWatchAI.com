# Progressive Autonomy Roadmap v1 — HITL -> Gradual Automation (Day 30)

**Why this matters:** RegWatch's value isn't "fully autonomous compliance" —
it's "surface the right things to the right person fast," with Sarah keeping
the final call on anything consequential (Trust-Strategy-v1.md, mechanism
#4). But "everything always needs human review forever" doesn't scale either.
This doc lays out how RegWatch can *earn* more autonomy over time, gated on
what F3's own eval data says it's actually reliable at — not on a calendar or
a vibe.

---

## The core principle

**Autonomy increases per PREDICTION CLASS, gated by that class's measured
precision on the golden set — not granted uniformly across F3's output.**

The Day 30 confusion matrix (23/30 = 76.7%) gives a precision breakdown for
each of classify_impact()'s four output classes:

| Predicted class | Total predicted | Correct | Precision |
|---|---|---|---|
| HIGH | 11 | 10 | 90.9% |
| MEDIUM | 0 | 0 | n/a (never predicted) |
| LOW | 10 | 5 | 50.0% |
| NOT_APPLICABLE | 9 | 8 | 88.9% |

This is a precision table, not an accuracy table — it answers "when F3 says
X, how often is X actually right?", which is the question that matters for
deciding what a human can skip checking. HIGH and NOT_APPLICABLE are both
~90%; LOW is a coin flip. MEDIUM has never been predicted, so it has no
precision to measure yet — it stays fully manual by default, not because it's
been judged unreliable, but because there's no evidence either way.

---

## Stage 0 (current state) — Everything reviewed

- F3 produces `impact_results.json`; F4 (when built) generates draft tasks
  from it.
- **Every finding, every task, regardless of impact_level, goes to Sarah for
  review before anything happens.** No autonomy yet.
- This is where RegWatch is today, and where it should stay until F4's HITL
  approval flow (Week 5, Day 32) exists at all — autonomy can't be "graduated
  into" before the review mechanism it graduates away from is built.

---

## Stage 1 — Surface high-precision findings without review queue delay

- HIGH and NOT_APPLICABLE findings (currently ~90% precision each) appear on
  Sarah's dashboard immediately, with their evidence (`matched_chunk_text`,
  `dense_score`, `named_regulation_match`) — same as today, but NOT held in a
  "pending review" queue state first.
- LOW and MEDIUM findings continue to queue for review before Sarah sees them
  as "ready."
- **No tasks are auto-generated yet** — F4 still drafts tasks from ALL
  findings, and ALL tasks still require approval. Stage 1 only changes how
  fast Sarah SEES a finding, not what happens as a result of it.
- **Exit criterion to enter Stage 1:** HIGH and NOT_APPLICABLE precision both
  hold at >=85% across at least two consecutive eval runs on an EXPANDED
  golden set (the current 30 pairs is too small to trust a one-time number —
  see "What this roadmap depends on" below).

---

## Stage 2 — Auto-generate (but not auto-act-on) tasks for HIGH findings

- For findings F3 classifies HIGH **and** `named_regulation_match=True`
  (the subset Day 27 showed is both the largest and most reliable slice — all
  10/10 true-HIGH golden pairs have `named_regulation_match=True`), F4
  auto-generates a task and adds it directly to Sarah's queue as "ready for
  approval" — skipping any intermediate triage step.
- HIGH findings with `named_regulation_match=False` (rarer, and the pattern
  with the one false positive, #21, where a true MEDIUM was over-predicted as
  HIGH) continue through the slower triage path.
- LOW/MEDIUM/NOT_APPLICABLE findings: still no auto-generated tasks. F3 just
  reports them.
- **Sarah still approves every task before any action is taken** — Stage 2 is
  about removing triage latency, not approval.
- **Exit criterion to enter Stage 2:** Stage 1 has run for a defined period
  with no precision regression (REGRESSION_BASELINE-style gate, same pattern
  as `evals/f3_eval.py`), AND F4's HITL approval flow exists and is in active
  use.

---

## Stage 3 (aspirational, not scheduled) — Limited auto-action on a narrow, proven slice

- For a SPECIFIC, NAMED subset of task types that have an unbroken track
  record of correct HIGH + `named_regulation_match=True` classifications AND
  Sarah-approved tasks with no corrections over a meaningful sample —
  RegWatch could take a low-risk action automatically (e.g., adding an item
  to a tracking log) while still notifying Sarah, rather than waiting for
  approval first.
- This stage is intentionally vague because it shouldn't be designed until
  Stage 2 has produced real approval/correction data to design it FROM. Any
  jump from "F3 says HIGH" directly to "system acts" without that evidence
  would be the exact "trusted blindly on the one finding that mattered"
  failure mode Trust-Strategy-v1.md warns about.

---

## What this roadmap depends on (honest gaps)

- **The 30-pair golden set is too small to gate real autonomy decisions on.**
  A precision of "10/11" or "8/9" has wide error bars at this sample size.
  Before Stage 1 is seriously considered, the golden set needs to grow
  (ideally via SME-reviewed real findings, not more Claude-generated pairs —
  see F3-AUDIT.md Section 8).
- **MEDIUM has zero data points.** Until the classifier predicts MEDIUM for
  *something* in the golden set, there's no way to know whether MEDIUM
  findings are reliable enough for even Stage 1's "skip the queue" treatment.
  MEDIUM stays Stage-0-only until that changes.
- **Every stage above is GATED ON F4 EXISTING.** This entire roadmap is about
  what happens to F3's output once F4 (task generation) and its HITL approval
  flow (Day 32) exist — none of it is actionable yet. Its purpose today is to
  make sure F4 is BUILT with these gates in mind from the start, rather than
  retrofitted later.
- **Precision tables must be recomputed every time F3's matcher or classifier
  changes** (e.g. Day 30's multi-query retrieval changed the distribution
  from 24/1/14/212 to 27/1/21/198 high/medium/low/N-A). A stage gate based on
  a stale precision table is worse than no gate.

---

## How this connects to the rest of RegWatch

- **Trust-Strategy-v1.md** (Day 29) established the mechanisms (evidence,
  disclosed limitations, auditability, HITL, regression CI, honest framing).
  This roadmap is the application of mechanism #4 (HITL where least certain)
  as a graduated SCHEDULE rather than a fixed rule.
- **F3-AUDIT.md Section 9 (Q6)** already frames F3's Week 4 exit-gate
  scorecard honestly (2/6 met). This roadmap extends that honesty forward:
  autonomy is something RegWatch will EARN, on a schedule driven by F3's own
  eval numbers, not promise.
- **F4 (Day 32+)** should read this doc before designing its approval flow —
  the queue/no-queue and auto-generate/no-generate distinctions above are
  meant to map onto F4's data model from day one.
