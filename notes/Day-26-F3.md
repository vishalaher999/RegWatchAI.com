# Day 26 — F3 Eval Pipeline + Golden Dataset (CI Gate FAILS at 40%)

**Date:** 2026-06-13
**Feature:** F3 — Policy Impact Mapping (Week 4, Day 5 of 7)
**KM:** #246 Golden dataset
**Status:** Eval pipeline built and working correctly. The result it produced is a FAIL — and that's the point of building it today instead of later.

---

## What Was Built

| File | Change |
|------|--------|
| `fixtures/golden/impact_pairs.json` | 30 hand-labeled (policy section, regulation) pairs with rationale per pair |
| `evals/f3_eval.py` | Runs classifier against golden set, prints confusion matrix, CI gate at 80% |
| `tests/test_f3_eval.py` | 3 tests: real golden set, controlled fake dataset, CI gate constant |
| `docs/Build-vs-Buy-Matrix-v1.md` | Product: build vs buy analysis, informed directly by today's result |
| `docs/ARCHITECTURE.md` | New entries |

---

## Roadmap v2.2 — Day 26 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | #246 Golden dataset | `fixtures/golden/impact_pairs.json` — 30 pairs, stratified, each with rationale |
| Engineering | Label 30 pairs + build F3 eval pipeline, CI gate 80% | `evals/f3_eval.py` — works correctly, **reports 40% (FAIL)** |
| Product | Build vs buy matrix | `docs/Build-vs-Buy-Matrix-v1.md` |
| Deliverable | F3 eval pipeline live; 30 pairs labeled | Live. Gate is RED — this is the headline finding of the day. |

---

## The Result

```
Accuracy: 12/30 = 40.0%
CI gate target: >= 80%
Result: FAIL

Confusion matrix (true -> predicted):
                              high          medium             low  not_applicable
            high                 8               2               0               0
          medium                 1               1               1               0
             low                 4               1               1               0
  not_applicable                 4               3               2               2
```

**Reading the matrix:**
- When the true answer is HIGH, the classifier gets it right 8/10 (80%) — good.
- When the true answer is NOT_APPLICABLE, the classifier gets it right only 2/11 (18%) — it predicts HIGH or MEDIUM for 7 of 11 true negatives.
- When the true answer is LOW, 4/6 are predicted HIGH.

**The pattern in every false positive:** the regulation is a long, generically-worded
document — "Equal Credit Opportunity Act (Regulation B)" or "Agency Information
Collection Activities: Comment Request" — that embeds at 0.44-0.61 cosine similarity
against almost ANY policy section, regardless of topic, because of shared generic
banking-compliance vocabulary ("institution," "must," "disclosure," "requirement").

**The pattern in the false negatives (3 cases):** true ECOA-relevant matches
(pairs #21, #26, #27 — pricing consistency, HMDA data collection, fair-lending
training) scored 0.47-0.52 — just under the 0.55 HIGH threshold — because the
substantive overlap with Reg B is real but doesn't dominate the section's overall
embedding the way generic vocabulary does for the false positives.

---

## Why This Is a Good Day, Not a Bad One

Day 24 flagged "RRF scores cluster near a floor — low confidence in matching."
Day 25 flagged "Reg B over-matches several unrelated policies — needs validation."
Day 26 just **quantified both** with a real number against ground truth: 40%,
not 80%. That's exactly what an eval-first pipeline is for — it turns a vague
"this seems off" into a measured gap with a confusion matrix that points
directly at the fix.

If we'd shipped the v1 classifier to Sarah without this eval, she'd see ~60%
of "HIGH impact" flags be false alarms (8 correct vs ~5+ false positives in a
representative sample) — exactly the kind of alert fatigue that makes
compliance officers stop trusting a tool.

---

## What the Confusion Matrix Says About the Fix

`dense_score` (cosine similarity) is **necessary but not sufficient**. It's
good at "is this roughly the same topic area" but bad at "does this specific
regulation's title name the SAME legal rule this policy section is governed
by." The build-vs-buy matrix concludes this is a **feature-engineering
problem**, not a "buy a better classifier/vector DB" problem:

- A cheap, high-leverage Day 27 feature: does the candidate regulation's title
  contain the name of a regulation the policy section is already governed by
  (e.g., policy section cites "ECOA/Regulation B" and the regulation title is
  literally "Equal Credit Opportunity Act (Regulation B)")? This single
  feature would fix most of today's false positives AND false negatives —
  the false negatives (#21, #26, #27) are ALL Fair-Lending-ECOA-Policy
  sections matched against the correctly-named "Equal Credit Opportunity Act
  (Regulation B)" regulation; the false positives are BSA/TRID sections
  matched against that SAME regulation, where the named-regulation match
  would correctly NOT fire.
- This is now a labeled-data problem with 30 real examples — small, but
  enough to sanity-check a 2-feature rule (`dense_score` + `named_regulation_match`)
  before considering KM #17/#20 (trained LogReg) for Day 27+.

---

## PM Insight

The CI gate failing on the day it's built is the system working as designed.
The alternative — discovering this in Week 6 during the React UI build, or
worse, after Sarah starts ignoring HIGH-impact flags — would cost far more.
Today's 40% isn't a setback to the roadmap; it's the roadmap doing its job:
catch the calibration gap with cheap synthetic-ish data, before it's expensive.

The build-vs-buy matrix conclusion reinforces this: the fix is a feature we
can build in roughly a day (named-regulation matching), not a vendor
integration or an embedding-model swap. The moat stays intact.

---

## Next: Day 27 (when user says "next")

Per roadmap v2.2 — Day 27 is the natural place to act on today's finding:
add a named-regulation-matching feature to the classifier (or matcher), and
re-run `evals/f3_eval.py` to see how much of the 40% -> 80% gap it closes.
(Confirm exact roadmap Day 27 KM/Eng/Product/Deliverable columns before
starting, per build rule 3.)
