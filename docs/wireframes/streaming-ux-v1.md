# Streaming Summary UX — F2 AI Summarisation
# Version 1 | Day 17 | Generate in Real-Time

## The Problem with Batch Summary Cards

Current behaviour (Day 13–17):
  Sarah clicks "Summarise" → waits 10–30 seconds → summary appears fully formed.

Problem: The wait feels like a black box. Sarah doesn't know if the system is:
  - Working on the document
  - Stuck on an API call
  - Failed silently

Result: She checks her email while waiting, loses context, has to re-read
the headline when the summary finally appears.

## What Streaming Solves

With streaming, Claude generates token by token. The UI receives each token
as it's produced and displays it progressively. Sarah sees:
  - The headline appear word by word (signals it's working, ~1 second)
  - The plain English summary fill in (~3-5 seconds)
  - The structured fields appear one by one
  - The process feels like a colleague reading and summarising live

Result: Sarah stays engaged, reads as it fills, often has read the whole
summary by the time it finishes generating.

─────────────────────────────────────────────────────────────────────
STREAMING SEQUENCE WIREFRAME
─────────────────────────────────────────────────────────────────────

T=0s: Click "Generate Summary"
┌─────────────────────────────────────────────────────────────────┐
│  [CFPB]  [Final Rule]                    [● Generating...]      │
│                                                                  │
│  Analysing document... (470 sections reviewed)                  │
│                    ████████░░░░░░░░░░░░ 40%                     │
└─────────────────────────────────────────────────────────────────┘

T=2s: Headline complete, summary streaming
┌─────────────────────────────────────────────────────────────────┐
│  [CFPB]  [Final Rule]                    [● Generating...]      │
│                                                                  │
│  CFPB amends Regulation B provisions on disparate impact        │
│  and special purpose credit programs                            │
│  ──────────────────────────────────────────────────────────── │
│  The CFPB has updated Regulation B to clarify rules around      │
│  disparate impact analysis, discouragement of loan applicants,  │
│  and special purpose credit programs. The changes are           │
│  described as▌                                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

T=8s: Summary complete, structured fields appearing
┌─────────────────────────────────────────────────────────────────┐
│  [CFPB]  [Final Rule]         [● GOOD CONFIDENCE 77/100]        │
│                                                                  │
│  CFPB amends Regulation B provisions on disparate impact...     │
│                                                                  │
│  [Summary text — complete]                                       │
│                                                                  │
│  WHAT CHANGED                                                    │
│  Previously: Regulation B had unclear provisions regarding▌     │
│                                                                  │
│  Effective date: Checking...          Deadline: Checking...      │
│  Affects: Checking...                                            │
└─────────────────────────────────────────────────────────────────┘

T=14s: All fields complete
┌─────────────────────────────────────────────────────────────────┐
│  [CFPB]  [Final Rule]         [● GOOD CONFIDENCE 77/100]        │
│  [REVIEW REQUIRED before acting]                                 │
│  ───────────────────────────────────────────────────────────── │
│  CFPB amends Regulation B on disparate impact and SPCPs         │
│                                                                  │
│  [Full summary, what changed, why it matters — all visible]     │
│                                                                  │
│  Effective: Jul 21, 2026   Deadline: Jul 21, 2026               │
│  Affects: community banks, credit unions with ≤$10B             │
│                                                                  │
│  [Approve]  [Edit]  [Create Task]  [View Original]              │
└─────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
IMPLEMENTATION NOTE (for Week 6 FastAPI)
─────────────────────────────────────────────────────────────────────

Streaming requires:
  1. FastAPI StreamingResponse endpoint
  2. Anthropic SDK streaming: client.messages.stream()
  3. Frontend (React or Streamlit) reading server-sent events (SSE)

Anthropic streaming example:
  with client.messages.stream(
      model=PRIMARY_MODEL,
      messages=[...],
      system=SYSTEM_PROMPT,
  ) as stream:
      for text in stream.text_stream:
          yield text  # Server-sent event to frontend

Current Streamlit doesn't support SSE natively.
Streaming UI ships with React frontend in Week 6.

For MVP (now): show a progress bar with descriptive status messages
while the batch summarisation runs. Gives feedback without requiring SSE.

─────────────────────────────────────────────────────────────────────
PROGRESS BAR DESIGN (MVP — works in Streamlit today)
─────────────────────────────────────────────────────────────────────

Stage 1: "Analysing document structure..."   [████░░░░░░] 40%
Stage 2: "Identifying key sections..."       [████████░░] 75%
Stage 3: "Generating AI summary..."          [██████████] 95%
Stage 4: "Verifying dates with NER..."       [██████████] 100%

Use st.progress() + st.status() in Streamlit for the MVP version.
This can be implemented in the dashboard on Day 21 (F2 wrap-up).
