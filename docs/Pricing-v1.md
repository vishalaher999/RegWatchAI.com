# RegWatch AI — Pricing v1 (Day 41, KM #271)

**Date:** 2026-06-14
**Status:** Draft pricing for the 90-day pilot → paid transition described in
`docs/Enterprise-Pilot-Program-v1.md`. No bank has been quoted these numbers
yet — this is a starting point for design partner conversations, not a
published rate card.

---

## Who's buying

Community banks ($100M-$10B assets) with a small compliance team (often
1-3 people, the "Sarah" persona) who currently track regulatory changes
manually via agency email alerts and spreadsheets, and re-review policies
against new rules by hand.

---

## Three tiers

| | **Monitor** | **Comply** | **Enterprise** |
|---|---|---|---|
| **Target bank** | Smallest community banks, single compliance officer | Mid-size community banks, 2-3 person compliance team | Larger community banks / multi-charter holding companies |
| **F1 — Feed monitoring** | All 5 agencies (Fed, CFPB, OCC, FDIC, FinCEN) | All 5 agencies | All 5 agencies + custom agency feeds |
| **F2 — Summarisation** | Included (review queue access) | Included | Included |
| **F3 — Policy impact mapping** | — | Up to 3 policy documents (BSA, AML, TRID, etc.) | Unlimited policy documents |
| **F4 — Task generation (HITL)** | — | Included | Included + custom task-routing rules |
| **F5 — Audit trail & weekly report** | Weekly compliance report (email) | Weekly report + full audit log access | Weekly report + audit log + compliance-report API |
| **API access (Day 40)** | — | Read-only API | Read-only API + priority support for integration |
| **PII redaction (Day 39)** | n/a (no policy upload) | Included | Included |
| **Support** | Email | Email + onboarding call | Dedicated onboarding + quarterly model-card review |
| **Indicative monthly price** | $300-$500 | $1,000-$2,000 | Custom (starts ~$3,000+) |

---

## How the tiers map to what's actually built

- **Monitor** is F1+F2 only — a bank gets the feed monitoring and
  plain-English summaries (with confidence scores and citations) but doesn't
  upload any policy documents, so F3/F4 don't apply. This is the lowest-risk
  entry point: no client data (not even policy PDFs) enters the system.
- **Comply** is the core pilot offer from `docs/Enterprise-Pilot-Program-v1.md`
  — adds F3 (policy impact mapping, gated by Day 39's PII redaction) and F4
  (task generation with human approval). The "3 policy documents" limit
  mirrors the current fixture set (BSA, AML, TRID) used for eval, so the
  pilot scope is something already proven against the 30-pair labeled set.
- **Enterprise** removes the document-count ceiling and adds the Day 40 API
  as a first-class deliverable (for banks that want to pull RegWatch data
  into their own GRC tooling), plus the model card (Day 41) as a recurring
  artifact for the bank's vendor-risk review cycle.

---

## Why these numbers (directionally)

- Anchored to what a compliance officer's time is worth: if RegWatch saves
  even 5-10 hours/month of manual feed-reading and policy cross-referencing,
  $1,000-$2,000/month is well below the loaded cost of that time at most
  community banks.
- Deliberately **not** anchored to per-seat or per-document-processed
  pricing yet — usage patterns are unknown until a design partner runs a
  real pilot. The 90-day pilot (`docs/Enterprise-Pilot-Program-v1.md`)
  exists partly to gather the usage data needed to validate or replace these
  numbers before they become a real rate card.

---

## What's explicitly NOT priced yet

- Per-additional-agency or per-additional-policy add-on pricing.
- Annual/multi-year discounts.
- A "Monitor" → "Comply" mid-contract upgrade path (process exists
  conceptually, not formalized).
- Implementation/setup fees — assumed bundled into onboarding for now.

These are flagged rather than guessed at, consistent with the project's
eval-first approach: don't define a metric (or a price) you can't yet
validate.
