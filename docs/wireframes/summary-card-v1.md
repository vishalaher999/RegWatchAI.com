# Summary Card Wireframe — F2 AI Summarisation
# Version 1 | Day 8 | 2-Minute Scan Layout

## Design Principle
Sarah has 15 minutes each morning. Each summary card must tell her
in 2 minutes: what changed, does it affect my bank, what do I do by when.

Information hierarchy (top = highest priority):
  1. HEADLINE — what is this? (3 seconds)
  2. CONFIDENCE + AGENCY + DATE — should I trust it? (5 seconds)
  3. PLAIN ENGLISH SUMMARY — what happened? (30 seconds)
  4. WHAT CHANGED / WHY IT MATTERS — what do I do? (45 seconds)
  5. DATES + INSTITUTIONS — when and who? (15 seconds)
  6. CITATIONS + ORIGINAL — verify if needed (optional)

───────────────────────────────────────────────────────────────────────
SUMMARY CARD WIREFRAME
───────────────────────────────────────────────────────────────────────

┌─────────────────────────────────────────────────────────────────────┐
│  [AGENCY BADGE]  [DOC TYPE BADGE]              [CONFIDENCE: 91/100] │
│                                                                      │
│  HEADLINE                                                            │
│  ─────────────────────────────────────────────────────────────────  │
│  CFPB issues final rule amending Regulation B small business         │
│  lending data collection requirements                                │
│                                                                      │
│  Published: Apr 22, 2026  ·  Source: Federal Register               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PLAIN ENGLISH SUMMARY                                               │
│  The CFPB amended Regulation B to update how lenders collect and     │
│  report small business lending data under Section 1071 of the        │
│  Dodd-Frank Act. Key changes cover which institutions must report,   │
│  how to define a "small business," and which data points are         │
│  required. The Bureau says the changes will streamline the rule      │
│  and improve data quality.                                           │
│                                                                      │
├───────────────────────────┬─────────────────────────────────────────┤
│  WHAT CHANGED             │  WHY IT MATTERS                         │
│  ─────────────────────    │  ─────────────────────────────────────  │
│  • Coverage thresholds    │  Community banks making small business   │
│    for which institutions │  loans must update data collection       │
│    must report updated    │  systems and staff training. Non-        │
│  • "Small business"       │  compliance with ECOA data reporting     │
│    definition revised     │  exposes the institution to regulatory   │
│  • Data points amended    │  action during examination.              │
│  • Compliance date        │                                          │
│    extended               │                                          │
├───────────────────────────┴─────────────────────────────────────────┤
│  EFFECTIVE DATE        COMPLIANCE DEADLINE    AFFECTED INSTITUTIONS  │
│  Apr 22, 2026          [varies by size — ]    Community banks        │
│                        [see original doc]     Credit unions          │
│                                               Small business lenders │
├─────────────────────────────────────────────────────────────────────┤
│  [REVIEW ORIGINAL]  [EDIT SUMMARY]  [CREATE TASK]  [MARK REVIEWED]  │
│                                                                      │
│  Source citations: Chunk 2 (institution scope) · Chunk 5 (dates)    │
│  · Chunk 8 (compliance requirements)           [View citations ▼]   │
└─────────────────────────────────────────────────────────────────────┘

NOTE: [REVIEW QUEUE BANNER] — shown when confidence < 80
┌─────────────────────────────────────────────────────────────────────┐
│  ⚠  LOW CONFIDENCE (67/100) — This summary needs human review       │
│     Possible reason: document excerpt may be incomplete             │
│     [Mark as Reviewed]  [Edit and Publish]  [Flag for Expert]       │
└─────────────────────────────────────────────────────────────────────┘

───────────────────────────────────────────────────────────────────────
CONFIDENCE UI DESIGN (#153 — for non-technical users)
───────────────────────────────────────────────────────────────────────

Problem: "87% confidence" means nothing to a compliance officer.
Solution: Map score ranges to plain-English labels + colour.

  90–100  ●  HIGH CONFIDENCE    Green    "Verified — ready to act on"
  80–89   ●  GOOD CONFIDENCE    Blue     "Reliable — spot-check recommended"
  70–79   ●  MODERATE           Orange   "Review before acting"
  <70     ●  LOW CONFIDENCE     Red      "Human review required"

Display in card header:
  [● HIGH CONFIDENCE 91]   not   [Confidence: 0.91]

───────────────────────────────────────────────────────────────────────
FALLBACK UX — Summary Failed or Very Low Confidence
───────────────────────────────────────────────────────────────────────

When summarisation fails entirely:
┌─────────────────────────────────────────────────────────────────────┐
│  [AGENCY BADGE]  [DOC TYPE BADGE]                  [● NOT PROCESSED]│
│                                                                      │
│  HEADLINE (from document title, unprocessed)                         │
│  ─────────────────────────────────────────────────────────────────  │
│  Final Rule on Capital Requirements for Large Banks                  │
│                                                                      │
│  ⚠ AI summary not available for this document.                       │
│     This may be due to document length or formatting.                │
│                                                                      │
│  [VIEW ORIGINAL DOCUMENT]  [Request Manual Summary]                 │
└─────────────────────────────────────────────────────────────────────┘

───────────────────────────────────────────────────────────────────────
NORTH STAR METRIC — Time-to-Understand per New Rule
───────────────────────────────────────────────────────────────────────

Definition:
  Time from "Sarah opens the summary card" to "Sarah knows:
  (a) what changed, (b) whether it affects her bank, (c) what to do by when"

Baseline (without RegWatch AI): 45–90 minutes per regulation
  (read original PDF, find relevant sections, assess applicability)

Target with F2: ≤ 2 minutes for 80% of regulations

Measurement (Day 14):
  - Time Sarah spends on the summary card before clicking away
  - Whether she clicks "Create Task" (signals she understood the implication)
  - Whether she clicks "Edit Summary" (signals AI output needed correction)

This metric is tracked via user interaction logging — not RAGAS.
RAGAS measures accuracy. North Star measures user value.
