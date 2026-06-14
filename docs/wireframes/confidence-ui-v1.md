# Confidence UI Design — F2 AI Summarisation
# Version 1 | Day 9 | How to Show 87% to a Non-Technical User

## The Problem

"87% confidence" is meaningless to Sarah (CCO, $500M community bank).
She doesn't know if 87% is good or bad. She doesn't know what the
AI was uncertain about. She doesn't know what to do with the number.

"GOOD CONFIDENCE — spot-check recommended" tells her exactly what to do.

## Design Principle

Never show raw numbers to non-technical users.
Map every score to: (1) a plain-English label, (2) a colour, (3) an action.

─────────────────────────────────────────────────────────────────────
CONFIDENCE SCALE
─────────────────────────────────────────────────────────────────────

Score     Label                  Colour    Action for Sarah
───────   ────────────────────   ───────   ──────────────────────────────
90–100    HIGH CONFIDENCE        Green     "Act on this — verified"
80–89     GOOD CONFIDENCE        Blue      "Reliable — spot-check dates"
70–79     MODERATE CONFIDENCE    Orange    "Review before acting"
60–69     LOW CONFIDENCE         Red       "Human review required"
<60       VERY LOW               Dark Red  "Do not act without review"

─────────────────────────────────────────────────────────────────────
IN-CARD DISPLAY (summary card header)
─────────────────────────────────────────────────────────────────────

HIGH CONFIDENCE (90+):
┌─────────────────────────────────────────────────────────────────┐
│  [CFPB]  [Final Rule]                    [● HIGH  92/100]       │
│  CFPB issues final rule amending Regulation B...                │
└─────────────────────────────────────────────────────────────────┘

GOOD CONFIDENCE (80-89):
┌─────────────────────────────────────────────────────────────────┐
│  [FED]   [Other]                         [● GOOD  85/100]       │
│  Kevin Warsh takes oath as Federal Reserve Chairman...          │
└─────────────────────────────────────────────────────────────────┘

REVIEW REQUIRED (<80):
┌─────────────────────────────────────────────────────────────────┐
│  [FED]   [Other]              [● REVIEW REQUIRED  75/100]       │
│  Federal agencies publish resolution plan feedback letters...   │
│  ─────────────────────────────────────────────────────────────  │
│  [!] This summary needs review before acting.                   │
│      Reason: Document excerpt may be incomplete.                │
│      [Mark Reviewed]  [Edit Summary]  [Flag for Expert]         │
└─────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
CONFIDENCE TOOLTIP (on hover)
─────────────────────────────────────────────────────────────────────

When Sarah hovers over the confidence badge:

┌──────────────────────────────────────────────────────┐
│  About this confidence score                         │
│  ─────────────────────────────────────────────────   │
│  Score: 85/100 (GOOD CONFIDENCE)                     │
│                                                      │
│  The AI reviewed 6 of 72 document sections.          │
│  It is confident about:                              │
│    ✓ Headline and summary                            │
│    ✓ Effective date (May 22, 2026)                   │
│  It is less certain about:                           │
│    ? Compliance deadline (not found in excerpt)      │
│    ? Full list of affected institution types         │
│                                                      │
│  Source: claude-sonnet-4-20250514                    │
│  [View source citations]  [See full document]        │
└──────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
DASHBOARD AGGREGATE VIEW (Mike's risk manager view)
─────────────────────────────────────────────────────────────────────

KPI row (top of dashboard, F1 view updated with F2 data):

┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  Total   │ │Summarised│ │   High   │ │  Review  │ │Anomalies │
│   111    │ │    3     │ │Confidence│ │  Queue   │ │    0     │
│documents │ │          │ │    1     │ │    2     │ │          │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘

Review Queue panel (appears when queue > 0):
┌─────────────────────────────────────────────────────────────────┐
│  [!] 2 summaries need review before they can be used            │
│                                                                 │
│  1. Fed discount rate minutes        [● 25/100]  [Review Now]  │
│  2. Resolution plan feedback         [● 75/100]  [Review Now]  │
└─────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
NORTH STAR: TIME-TO-UNDERSTAND
─────────────────────────────────────────────────────────────────────

Target: Sarah understands a new regulation in ≤ 2 minutes.

With HIGH/GOOD confidence summary:
  0:00 — Sarah opens summary card
  0:10 — Reads headline
  0:40 — Reads plain English summary (3-5 sentences)
  1:10 — Reads what changed + why it matters
  1:30 — Checks effective date and compliance deadline
  1:50 — Checks affected institution types
  2:00 — Decision: Create task / No action / Flag for review
  TOTAL: ~2 minutes ✓

With REVIEW REQUIRED summary:
  Sarah sees the review banner immediately.
  She knows NOT to act without checking.
  She clicks "Review Now" → reads original doc → marks reviewed.
  TOTAL: 5-15 minutes (but she knows it needs extra time)

With NO summary (Day 8 state):
  Sarah must open original document.
  Find the relevant sections herself.
  Assess applicability to her bank.
  TOTAL: 45-90 minutes per regulation ✗
