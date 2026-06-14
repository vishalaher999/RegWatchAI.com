# Day 28 — Week 4 Review: F3 MVP Sample + Executive Deck + Exit-Gate Scorecard

**Date:** 2026-06-13
**Feature:** F3 — Policy Impact Mapping (Week 4, Day 7 of 7 — Review day)
**KM:** Review
**Status:** Week 4's "Review" day. No new code. Consolidated F3's output into
a concrete sample + strategy deck, and produced an honest exit-gate
scorecard — most criteria not yet met, documented rather than glossed over.

---

## What Was Built

| File | Change |
|------|--------|
| `docs/F3-MVP-Sample-v1.md` | NEW — 10 real (policy section, regulation) pairs from `data/f3_indexes/impact_results.json`, spanning HIGH/MEDIUM/LOW/N-A, with evidence text and rationale. Includes one known-limitation example (#8) deliberately. |
| `docs/Executive-Deck-v1.md` | NEW — 5-slide outline: problem, pipeline, F3 MVP output, MVAP definition, next steps. |
| `docs/ARCHITECTURE.md` | New entries for both. |

---

## Roadmap v2.2 — Day 28 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | Review | This note — Week 4 retrospective + exit-gate scorecard (below) |
| Engineering | Run impact mapping on 10 real regulation-policy pairs | `docs/F3-MVP-Sample-v1.md` — 4 HIGH, 1 MEDIUM, 3 LOW (incl. 1 known error), 2 correctly-suppressed N/A |
| Product | Executive deck — RegWatch strategy (5 slides). MVAP definition. | `docs/Executive-Deck-v1.md` — defines MVAP as "useful and honest today," distinct from the 80% gate |
| Deliverable | F3 MVP: impact on 10 pairs | `docs/F3-MVP-Sample-v1.md` |

---

## Week 4 Exit-Gate Scorecard (honest)

The roadmap's Week 4 exit gate lists 6 criteria. Status as of today:

| Criterion | Status | Notes |
|-----------|--------|-------|
| Upload 5+ policies | ❌ **Not met** | 3 synthetic policy fixtures (BSA-AML, Fair Lending/ECOA, TRID). Real policy upload UI doesn't exist yet — fixtures only. |
| Map 10 regulations | ✅ **Met** | 251 matches across 72 policy sections vs. real ingested regulations (25 summarised docs). The 10-pair sample (`F3-MVP-Sample-v1.md`) demonstrates this. |
| High/Med/Low/N-A with section IDs | ✅ **Met** | `classify_matches()` output includes `impact_level` + `section_id` for every match — see `data/f3_indexes/impact_results.json`. |
| F3 eval CI live at ≥80% | ⚠️ **Partially met** | CI pipeline is live (`evals/f3_eval.py`, `tests/test_f3_eval.py`) and runs every test pass. Accuracy is 73.3% (22/30) — below the 80% target. The pipeline itself is the deliverable Day 26 built; the 80% number is not yet reached. |
| Design partner outreach sent | ❌ **Not met** | 5 profiles + 2 email drafts exist (`docs/Design-Partner-Profiles-v1.md`), but per build rules Claude does not send emails — these are drafts for the user to send manually. |
| Sarah acceptance criteria met | ⚠️ **Partially met** | The output (section IDs, impact levels, evidence, plain-English rationale) is structurally what Sarah needs (Slide 3 of the exec deck). Whether she'd *actually* accept 73.3% accuracy and 3 fixture policies hasn't been tested — that's what design partner outreach (once sent) would tell us.

**Bottom line: 2 of 6 fully met, 2 partially met, 2 not met.** This is not a
"Week 4 failed" situation — F1-F3's core pipeline runs end-to-end on real
data and produces explainable output (the hardest technical bet). The unmet
items are either (a) scope items deferred by design (5+ real policies needs
an upload UI, which isn't on the roadmap until later), (b) a number that's
trending the right direction (40% → 73.3% in one day), or (c) an action that
requires the user, not Claude, to take (sending emails).

---

## PM Insight

The honest version of a Review day is more useful than a green checkmark.
Reporting "6/6 exit criteria met" when 2 require an upload UI that doesn't
exist yet, and 1 requires an accuracy number that's currently 6.7 points
short, would just move the discovery of those gaps to Week 5 — at a point
where F4 (task generation) depends on F3's output being trustworthy.

The MVAP framing in the executive deck is meant to resolve the tension
directly: RegWatch doesn't need to hit 80%/5-policies/zero-false-positives to
be useful *today* — it needs to be useful *and honest about its limits*
today. The F3 MVP sample practices that by including a known-wrong example
(#8) right alongside the correct ones. That's the artifact a design partner
conversation should be built around — not a cherry-picked demo.

---

## Next: Week 5, Day 29 (when user says "next")

Per roadmap v2.2 — Week 5 (Days 29-35): "F3 v2 + F4 — Impact Deep + Task
Generation." Day 29 columns: KM #167 Contextual retrieval / Engineering:
"Improve policy matching with contextual chunk enrichment" / Product: "Trust
strategy — how RegWatch earns compliance trust" / Deliverable: "Contextual
retrieval for F3". Confirm these columns again before starting (build rule
3) — do not start Day 29 without explicit "next".
