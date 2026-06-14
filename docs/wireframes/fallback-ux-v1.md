# Fallback UX — F2 AI Summarisation
# Version 1 | Day 12 | When Summary Fails or Has Low Confidence

## Three Failure States

State 1: SUMMARY FAILED — Claude couldn't produce valid JSON (rare)
State 2: VERY LOW CONFIDENCE (<60) — summary produced but unreliable
State 3: LOW CONFIDENCE (60-79) — in review queue, needs human check

─────────────────────────────────────────────────────────────────────
STATE 1: SUMMARY FAILED
─────────────────────────────────────────────────────────────────────

When: Both primary (Sonnet) and fallback (Haiku) models failed.
Cause: Network error, API outage, malformed document, token limit exceeded.

┌─────────────────────────────────────────────────────────────────┐
│  [CFPB]  [Final Rule]                    [● NOT PROCESSED]      │
│                                                                  │
│  Equal Credit Opportunity Act (Regulation B)                    │
│  Published: Apr 22, 2026  ·  Source: Federal Register           │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│  [!] Summary not available for this document.                   │
│                                                                  │
│      Possible reasons:                                           │
│      - Document is very long (400,000+ characters)              │
│      - AI service temporarily unavailable                       │
│      - Document format not supported                            │
│                                                                  │
│  [View Original Document ↗]  [Request Manual Summary]           │
│  [Retry AI Summary]                                             │
└─────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
STATE 2: VERY LOW CONFIDENCE (<60)
─────────────────────────────────────────────────────────────────────

When: Summary produced but confidence score very low.
Cause: Document excerpt too short, document is informational only,
       or key sections (dates, institution scope) not in retrieved chunks.

┌─────────────────────────────────────────────────────────────────┐
│  [FED]  [Other]                    [● VERY LOW  45/100]         │
│                                                                  │
│  Minutes of the Board's discount rate meeting                   │
│                                                                  │
│  ─ UNVERIFIED SUMMARY ─────────────────────────────────────── ─ │
│  [!] This summary has very low confidence and should NOT be     │
│      used for compliance decisions without verification.         │
│                                                                  │
│  Headline: Fed releases April 2026 discount rate meeting minutes │
│                                                                  │
│  Summary: Routine meeting minutes. No policy changes noted.     │
│                                                                  │
│  Effective date: Unknown      Compliance deadline: Unknown       │
│  Affects: [Not determined]                                       │
│                                                                  │
│  [Review Original Document ↗]  [Mark as Reviewed]               │
│  [Edit Summary]  [Flag as Irrelevant]                           │
│                                                                  │
│  Why low confidence? The available document excerpt (731 chars)  │
│  may not contain the full content of the original publication.  │
└─────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
STATE 3: REVIEW QUEUE (60–79)
─────────────────────────────────────────────────────────────────────

When: Summary produced, moderate confidence, flagged for human check.
Cause: Dates missing, institution scope unclear, complex regulatory text.

┌─────────────────────────────────────────────────────────────────┐
│  [FED]  [Enforcement]                   [● REVIEW  75/100]      │
│                                                                  │
│  Fed issues enforcement actions against former bank employees   │
│                                                                  │
│  ─ NEEDS REVIEW BEFORE USE ───────────────────────────────────  │
│  This summary has been generated but needs a quick human check  │
│  before being used for compliance decisions. Estimated: 2 min.  │
│                                                                  │
│  [Summary text — visible but greyed out]                        │
│                                                                  │
│  Effective date: May 28, 2026 (from NER)  ← NER-filled badge   │
│  Compliance deadline: None required                              │
│                                                                  │
│  [Quick Review ▶]  →  opens review checklist:                   │
│    [ ] Headline is accurate                                      │
│    [ ] What changed is correct                                   │
│    [ ] Why it matters reflects our institution's situation       │
│    [ ] Dates are correct (or correctly null)                     │
│    [Submit Review]  or  [Edit then Submit]                       │
└─────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
NER-FILLED FIELD INDICATOR
─────────────────────────────────────────────────────────────────────

When NER fills a field the LLM returned as null, show a badge:

  Effective date: July 21, 2026  [NER]

This tells Sarah:
  - The AI didn't find this date in its reading
  - A separate pattern-matching system found it in the document
  - She should verify this date against the original before acting

Tooltip: "This date was found by pattern matching, not AI reasoning.
          Verify against the source document before acting."

─────────────────────────────────────────────────────────────────────
REVIEW QUEUE DASHBOARD (Priority Sort)
─────────────────────────────────────────────────────────────────────

Review queue sorted by:
  1. Final Rules (doc_type) — highest urgency
  2. Documents with effective_date < 90 days away — time-sensitive
  3. Documents with compliance_deadline set — action required
  4. Lowest confidence last — informational documents

┌──────────────────────────────────────────────────────────────────┐
│  REVIEW QUEUE — 3 items                                          │
│  ─────────────────────────────────────────────────────────────   │
│  1. Fed Enforcement — 2 employees  [● 75]  [Enforcement]        │
│     Quick review: No action required? [Confirm] [Edit]          │
│                                                                  │
│  2. CFPB Reg B Final Rule          [● 75]  [Final Rule] [!]     │
│     Has compliance deadline — priority review needed             │
│     [Review Now]                                                 │
│                                                                  │
│  3. Discount rate minutes          [● 45]  [Other]              │
│     Very low confidence — original document review recommended   │
│     [View Original]  [Mark Irrelevant]                          │
└──────────────────────────────────────────────────────────────────┘
