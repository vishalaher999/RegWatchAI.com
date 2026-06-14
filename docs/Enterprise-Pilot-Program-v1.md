# Enterprise Pilot Program v1 — 90-Day Community Bank Pilot

**Date:** 2026-06-13
**Feature:** Week 6, Day 4 of 7
**KM concept:** #267/268 PII (Product half — "Enterprise pilot program doc")
**Status:** Draft program structure, tied to current eval targets and Day 39's
PII redaction pipeline. No pilot bank is signed; this is the offer document.

---

## Why now

Days 1-38 built the full F1-F5 pipeline against public data and synthetic
policy fixtures. A pilot is the first time real data enters the system: a
real bank's policy library (BSA, AML, Fair Lending, TRID, etc.), which
contains real account numbers, employee SSNs in HR-adjacent sections, and
customer examples. Day 39's PII redaction (`src/f3_impact/pii.py`) is what
makes "upload your policy library" a safe ask — without it, this pilot
program couldn't responsibly exist.

---

## What the pilot includes

- Onboarding: bank uploads its policy library (PDF/DOCX/TXT) for the
  agencies/regulations it cares about (Fed, CFPB, OCC, FDIC, FinCEN).
- F1: continuous monitoring of those agencies' regulatory feeds.
- F2: plain-English summaries of every relevant rule change, routed by
  confidence (APPROVED / REVIEW / ESCALATE / DISMISS — `src/f2_summarise/router.py`).
- F3: impact mapping — which policy sections each rule change affects, with
  High/Medium/Low/Not Applicable classification.
- F4: drafted compliance tasks (owner, due date, description) for HIGH
  findings, with human-in-the-loop approval before anything is final.
- F5: full audit trail (`AuditLog`) for every AI decision — model version,
  prompt version, inputs, and now (Day 39) PII redaction counts for every
  policy file processed.
- Weekly compliance report (Day 38, `scripts/weekly_compliance_report.py`)
  delivered to Mike/Sarah.

---

## Onboarding flow (Week 0)

1. Bank uploads policy library (community bank policy libraries in this
   project's experience run 50-100 N.M-numbered sections per policy, per
   `src/f3_impact/extractor.py`).
2. **PII redaction (Day 39)** — every section's text is scanned by
   `src/f3_impact/pii.py` before embedding. Redaction counts by type
   (SSN, EIN, account/routing numbers, card numbers, emails, phones) are
   logged as `AuditLog(PII_REDACT)` rows — one per policy file — so the
   bank can audit exactly what was scrubbed before it reached Pinecone.
3. F3 dual-index build (`src/f3_impact/build_indexes.py`) embeds the
   redacted policy sections into the bank's dedicated Pinecone namespace
   (multi-tenant isolation — one namespace per client, never shared).
4. Baseline F3 impact mapping run against the bank's existing policy set
   and the last 90 days of regulatory activity, to calibrate expectations
   before live monitoring starts.

---

## 90-day timeline

| Week(s) | Milestone |
|---------|-----------|
| 0 | Onboarding (policy upload, PII redaction, index build, baseline run) |
| 1-2 | Live monitoring begins. Daily F1 ingestion, F2 summaries land in the review queue. Sarah reviews REVIEW/ESCALATE items. |
| 3-4 | First weekly compliance reports (Day 38 template) delivered. Calibration check-in: is the REVIEW queue <20% of summaries (router target)? |
| 5-8 | F3/F4 fully active — HIGH findings generate drafted tasks via HITL approval. Override-rate tracking begins (Day 37). |
| 9-12 | Steady state. Final report: cumulative override rate, guardrail-warning rate (Day 38), F3 accuracy on the bank's own findings (spot-checked against the 30-pair golden set methodology). |
| 13 (end) | Go/no-go conversation: convert to paid, extend pilot, or end engagement. |

---

## Success metrics (tie to existing eval targets)

The pilot doesn't get new metrics — it's existing eval targets run against a
real bank's data instead of fixtures:

- F1 doc classification ≥90% (held-out set methodology, Day-built)
- F2 RAGAS faithfulness ≥0.85
- F3 impact classification ≥80%, section-match precision@5 ≥0.75
- F4 override rate (Day 37) — tracked, not gated; informs whether HITL
  review time decreases over the pilot
- Day 38 guardrail-warning rate — % of summaries where `_apply_guardrails()`
  fired, tracked weekly; a declining trend signals the citation-forcing
  layer is working as retrieval/prompting matures
- Review queue size < 20% of summaries (router target)

---

## What's explicitly OUT of scope for v1

- **No SLA guarantees.** This is a pilot, not a production contract —
  framed as a 90-day evaluation with a go/no-go decision at the end.
- **No custom model fine-tuning.** Pilot runs on the same
  `claude-sonnet-4-20250514` / `claude-haiku-4-5-20251001` models as the
  rest of the project.
- **No frontend SSO/multi-user accounts.** Single shared login for the
  pilot bank's compliance team — full auth is a post-pilot build item.
- **PII redaction is regex-only (v1).** Catches SSNs, EINs, account/routing
  numbers, card numbers, emails, phone numbers. Does NOT catch free-text PII
  (customer/employee names, street addresses) — a human reviewer should spot
  -check the redacted policy library before it's indexed. NER-based name/
  address redaction is a documented v2 gap (see `src/f3_impact/pii.py`).
- **No PDF compliance report** (Day 38 v1 is Markdown).

---

## How this connects to the rest of RegWatch

- Built directly on Day 38's `scripts/weekly_compliance_report.py` (the
  recurring deliverable during the pilot) and Day 37's override-rate
  tracking (the pilot's "is HITL still needed as much" signal).
- Day 39's `src/f3_impact/pii.py` + `AuditAction.PII_REDACT` is the
  prerequisite that makes Step 2 of onboarding (real policy library upload)
  consistent with CLAUDE.md's "Public regulatory data only — no Moody's
  internal or client data" constraint — the *pipeline* only ever sees
  redacted text, even though the *source upload* contains real PII.
- Multi-tenant Pinecone namespace isolation (CLAUDE.md stack) is what makes
  "one pilot bank's data never touches another's" true at the storage layer;
  PII redaction is the complementary control at the ingestion layer.
