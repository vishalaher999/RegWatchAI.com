# Day 41 — Model Card (SR 11-7 + EU AI Act) + Pricing (KM #271/#273)

**Date:** 2026-06-14
**Roadmap:** Week 6 ("Deploy & Demo"), Day 6 of 7

---

## What Was Built

| Artifact | Type | Status |
|---|---|---|
| `docs/Model-Card-v1.md` | NEW | Done |
| `docs/Pricing-v1.md` | NEW | Done |
| `docs/ARCHITECTURE.md` | EDIT | Day 41 entries added |
| `notes/Day-41-GTM.md` | NEW | This file |

No code changes, no new tests — today's deliverables are both Product docs.

---

## Roadmap v2.2 — Day 41 columns

| Column | Content |
|---|---|
| KM reference | #271 (EU AI Act), #273 (SR 11-7) |
| Deploy buffer | "Fix any deploy issues; smoke-test all endpoints on live URL" |
| Product | "Model card; classify RegWatch under EU AI Act + SR 11-7; pricing page (3 tiers)" |
| Deliverable | "Model card + pricing live" |

---

## What Changed and Why

**`docs/Model-Card-v1.md`** inventories every model in the F1-F5 pipeline
(§1), states intended use and known limitations (§2), maps SR 11-7's three
pillars — development, independent validation, ongoing monitoring — to
artifacts already built across Days 1-40 (§3), and gives a self-assessed
EU AI Act risk tier of **Limited Risk** (§4), reasoning from the Annex III
high-risk category most relevant to financial services (creditworthiness
decisions about individuals) and noting RegWatch doesn't make any such
decision — every output requires human approval.

**`docs/Pricing-v1.md`** defines 3 tiers (Monitor / Comply / Enterprise)
mapped directly to feature availability — "Comply" mirrors the existing
3-policy-document pilot scope from `docs/Enterprise-Pilot-Program-v1.md`
(BSA/AML/TRID, the same fixtures used for the F3 eval set), so the pricing
tier a bank would actually pilot is something already validated against the
30-pair labeled set, not a hypothetical larger scope.

---

## On the "Deploy buffer / smoke-test live URL" item

Day 40's Docker build and cloud deploy were never executed in this
environment (no Docker CLI, no cloud account access) — see
`notes/Day-40-API.md`. There is no live URL to smoke-test yet. This item
remains blocked on you running through `docs/Deployment-Guide-v1.md`'s
Docker/Render steps; once a live URL exists, smoke-testing the 9 endpoints
from `api/main.py` against it is a ~10-minute follow-up (the same checks
already done locally via `TestClient` in Day 40, just re-pointed at the
live URL).

---

## Result

Both Day 41 deliverables (`Model-Card-v1.md`, `Pricing-v1.md`) written and
cross-referenced in `docs/ARCHITECTURE.md`. Full test suite unchanged from
Day 40 (182 passed, 11 deselected) — no code touched today.

---

## v1 Limitations

1. **EU AI Act classification is a self-assessment**, explicitly flagged as
   not legal advice. The model card names the specific scenario (a
   customer-facing automated decision) that would push the classification
   to High-Risk, so this isn't a "set and forget" determination.
2. **Pricing numbers are directional**, not validated against any real
   pilot usage data — the 90-day pilot is partly designed to generate the
   data needed to firm these up.
3. **Smoke-test of live endpoints is still blocked** on the Day 40 deploy
   steps being run manually (Docker not available in this dev environment).

---

## PM Insight

Today's two docs are the same kind of "infrastructure exists, now make it
legible to an outside party" move as Day 38's compliance report and Day 39's
pilot doc — but aimed at two different outside parties: the model card is
for a bank's vendor-risk/compliance reviewer, and the pricing page is for
whoever signs the contract. Both draw entirely on artifacts from Days
36-40 (audit trail, override rate, guardrails, PII redaction, API) — the
"GTM package" the roadmap calls for this week isn't new capability, it's
packaging existing capability for the two audiences who need to say yes
before a pilot starts.

---

**Next: Day 42** — do not start without explicit "next".
