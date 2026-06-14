# Explainability Modal — F2 AI Summarisation
# Version 1 | Day 10 | Source Citations Per Summary Field

## What This Is

When Sarah reads a summary and thinks "how does Claude know this?"
she can click [View citations] to see exactly which part of the
original 400-page document each field came from.

This is a TRUST feature. Without it:
  Sarah: "The effective date is July 21, 2026 — is that right?"
  RegWatch: "The AI said so."

With it:
  Sarah: "The effective date is July 21, 2026 — is that right?"
  RegWatch: "Yes — see Section 7, paragraph 3 of the original document."
  Sarah clicks through, confirms, trusts the tool.

## Trigger

[View citations v] link below each summary card.
Always present. Shows/hides the modal.

─────────────────────────────────────────────────────────────────────
EXPLAINABILITY MODAL WIREFRAME
─────────────────────────────────────────────────────────────────────

┌──────────────────────────────────────────────────────────────────────┐
│  Source Citations — Equal Credit Opportunity Act (Regulation B)      │
│  [x Close]                                                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  How this summary was generated                                      │
│  The AI reviewed 7 of 470 document sections (1.5% of the document). │
│  Model: claude-sonnet-4-20250514  |  Confidence: 75/100             │
│  Chunking: hierarchical  |  Retrieved: 7 chunks                     │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  FIELD CITATIONS                                                     │
│                                                                      │
│  Effective Date: July 21, 2026                                       │
│    Source: Chunk 365  [DATE SECTION]                                 │
│    ┌────────────────────────────────────────────────────────────┐   │
│    │ "...The final rule is effective July 21, 2026. Compliance  │   │
│    │  with the amendments to Sec. 1002.6(b)(6) and 1002.14...  │   │
│    │  [Read more ↗]"                                            │   │
│    └────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  What Changed                                                        │
│    Source: Chunk 370  [Section: III. Final Rule Provisions]          │
│    ┌────────────────────────────────────────────────────────────┐   │
│    │ "The Bureau is amending Regulation B to revise provisions  │   │
│    │  related to disparate impact, discouragement of applicants │   │
│    │  and special purpose credit programs..."  [Read more ↗]   │   │
│    └────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Affected Institutions                                               │
│    Source: Chunk 435  [INSTITUTION SECTION]                          │
│    ┌────────────────────────────────────────────────────────────┐   │
│    │ "Creditors subject to Regulation B — including banks,      │   │
│    │  credit unions, and nonbank lenders — must comply..."      │   │
│    │  [Read more ↗]"                                            │   │
│    └────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Why It Matters                                                      │
│    Source: Chunk 88  [Section: I. Background]                        │
│    ┌────────────────────────────────────────────────────────────┐   │
│    │ "Institutions with special purpose credit programs must    │   │
│    │  review their programs for compliance. State enforcement   │   │
│    │  and private litigation remain available even where..."    │   │
│    │  [Read more ↗]"                                            │   │
│    └────────────────────────────────────────────────────────────┘   │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  [View Full Original Document ↗]    [Mark Summary as Verified]      │
└──────────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
WHY THIS MATTERS FOR SR 11-7 COMPLIANCE
─────────────────────────────────────────────────────────────────────

SR 11-7 (Federal Reserve model risk management guidance) requires that
AI-assisted decisions be explainable and traceable. The explainability
modal provides:

  1. Model identity (which Claude model produced this)
  2. Input traceability (which document sections were used)
  3. Human verification (Sarah can confirm each field)
  4. Audit record (AuditLog captures chunk IDs used)

When an examiner asks "how did you know this rule applied to your bank
by July 21, 2026?" Sarah can show:
  - The RegWatch summary
  - The source citations modal
  - The original document section
  - The audit log entry

This is defensible AI — not a black box.

─────────────────────────────────────────────────────────────────────
IMPLEMENTATION NOTE
─────────────────────────────────────────────────────────────────────

The source_citations field in summary_json already contains chunk
references from Claude's output. Example:

  "source_citations": [
    "Chunk 2 (effective date)",
    "Chunk 365 (effective date and compliance)",
    "Chunk 370 (what changed)",
    "Chunk 435 (affected institutions)",
    "Chunk 88 (compliance implications)"
  ]

To build the modal:
  1. Parse source_citations from summary_json
  2. Match chunk numbers to the stored chunks (requires chunk storage — Day 10 gap)
  3. Display chunk text as expandable previews with "Read more" links to URL

CURRENT GAP: We don't store chunks in the DB — they're generated on-the-fly.
To show chunk text in the modal, we need to either:
  (a) Store chunks in a new `document_chunks` table (Day 10 scope)
  (b) Re-chunk on demand when modal is opened (slower but simpler)

For MVP: option (b) — re-chunk on demand. Store chunks in DB in Week 3
when we build the full eval pipeline.
