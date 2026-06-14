# Officer Edit UX — F2 AI Summarisation
# Version 1 | Day 11 | Draft + Refine Before Publishing

## Why Edit Capability Is Mandatory

RegWatch AI output is decision support, not legal advice.
Sarah (CCO) retains professional responsibility.
If the AI gets something wrong, she must be able to correct it.

Without edit capability:
  - Wrong summary gets published internally
  - Compliance officer acts on wrong information
  - Liability falls entirely on RegWatch AI ("the tool told me")

With edit capability:
  - Sarah reviews, corrects if needed, publishes
  - Her correction is recorded in the AuditLog
  - Liability is properly shared: "AI produced X, Sarah reviewed and confirmed Y"

This is also required by SR 11-7: human review must be meaningful,
not a rubber stamp. Edit capability makes the review meaningful.

─────────────────────────────────────────────────────────────────────
EDIT FLOW WIREFRAME
─────────────────────────────────────────────────────────────────────

STEP 1: Sarah sees the AI summary card (default: read-only view)

┌────────────────────────────────────────────────────────────────┐
│  [CFPB]  [Final Rule]              [● GOOD CONFIDENCE 85/100] │
│  CFPB amends Regulation B small business lending requirements  │
│                                                                │
│  [Summary text...]                                             │
│                                                                │
│  Effective: Jul 21, 2026  |  Deadline: Jul 21, 2026           │
│  Affects: community banks, credit unions                       │
│                                                                │
│  [Edit Summary]  [Create Task]  [Mark Reviewed]  [Dismiss]    │
└────────────────────────────────────────────────────────────────┘

STEP 2: Sarah clicks [Edit Summary] → inline editing enabled

┌────────────────────────────────────────────────────────────────┐
│  [CFPB]  [Final Rule]   [● EDITING — changes tracked]          │
│                                                                │
│  HEADLINE (editable)                                           │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ CFPB amends Regulation B small business lending...       │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  WHAT CHANGED (editable)                                       │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Previously: Reg B required [X]. Now: Reg B requires [Y]. │ │
│  │                                                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│  AI wrote this. [View original ↓]                              │
│                                                                │
│  WHY IT MATTERS (editable)                                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Community banks with SBA loan programs must update...    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  EFFECTIVE DATE: [2026-07-21     ] (locked — from source)     │
│  DEADLINE:       [2026-07-21     ] (locked — from source)     │
│                                                                │
│  [Save & Publish]  [Discard Changes]  [Request Expert Review] │
└────────────────────────────────────────────────────────────────┘

STEP 3: Sarah saves → AuditLog captures the edit

┌────────────────────────────────────────────────────────────────┐
│  AuditLog entry written:                                       │
│  {                                                             │
│    "action": "override",                                       │
│    "actor": "sarah@bank.com",                                  │
│    "doc_id": "...",                                            │
│    "payload": {                                                │
│      "field": "why_it_matters",                               │
│      "original": "No immediate action required...",            │
│      "corrected": "Community banks with SBA loan programs...", │
│      "reason": "AI missed the SBA program applicability",     │
│      "prompt_version": "v2"                                   │
│    }                                                           │
│  }                                                             │
└────────────────────────────────────────────────────────────────┘

STEP 4: Published summary shows edit provenance

┌────────────────────────────────────────────────────────────────┐
│  [CFPB]  [Final Rule]   [● HIGH CONFIDENCE 85/100] [VERIFIED] │
│                                                                │
│  Why it matters: (edited by Sarah M. on Jun 2, 2026)          │
│  Community banks with SBA loan programs must update their      │
│  disclosures by July 21, 2026...                               │
│                                                                │
│  [View AI original]  [View edit history]                      │
└────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
EDIT RULES
─────────────────────────────────────────────────────────────────────

EDITABLE fields (Sarah's domain):
  - headline
  - plain_english_summary
  - what_changed
  - why_it_matters
  - affected_institution_types

LOCKED fields (sourced from document — editing creates liability):
  - effective_date         (locked to document-stated date)
  - compliance_deadline    (locked to document-stated date)

If Sarah believes a date is wrong:
  - She can flag: [Report incorrect date]
  - System creates a review task
  - Date stays null until a human verifies from the source doc

REASON REQUIRED:
  Every edit requires a one-line reason.
  This populates AuditLog.payload.reason.
  Reason options (dropdown + free text):
    - "AI missed important context"
    - "Institution scope too broad/narrow"
    - "Action urgency incorrect"
    - "Date extracted incorrectly"
    - Other: [free text]

─────────────────────────────────────────────────────────────────────
OVERRIDE RATE DASHBOARD (Mike's view — risk manager)
─────────────────────────────────────────────────────────────────────

Target: < 20% of summaries edited before publishing.
> 20% = systematic prompt problem → trigger prompt review.

┌──────────────────────────────────────────────────────────────┐
│  SUMMARY QUALITY METRICS          Last 30 days               │
│                                                              │
│  Total summaries generated:    47                            │
│  Published without edit:       38  (81%)  [TARGET: >80%] ✓  │
│  Edited before publishing:      9  (19%)  [TARGET: <20%] ✓  │
│  In review queue (conf<80):     6  (13%)                     │
│  Failed (no summary):           0   (0%)                     │
│                                                              │
│  Most edited field: why_it_matters (7 of 9 edits)           │
│  → Indicates: prompt v2 still too vague on action urgency    │
│                                                              │
│  [Download edit log]  [Flag for prompt review]               │
└──────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
IMPLEMENTATION NOTE
─────────────────────────────────────────────────────────────────────

DB changes needed (not in Day 11 scope — Week 6):
  - Add `edited_by` field to RegulatoryDocument
  - Add `edited_at` timestamp
  - Add `edit_reason` field
  - AuditLog already has action=OVERRIDE — use this

For MVP (Streamlit dashboard):
  - Use st.text_area() for editable fields
  - Store edits in session state
  - Write to DB on Save button click
  - Log to AuditLog with action=OVERRIDE
