# Section-Level Output UX — F3 Policy Impact Mapping
# Version 1 | Day 25 | Per-Section Impact Cards

## Who This Screen Serves

The heatmap (`impact-dashboard-v1.md`, Day 23) answers "where should I
look?" This screen answers "for THIS section, what did RegWatch AI find,
and how confident is it?" — the view Sarah lands on after clicking a
heatmap cell or a policy section in the library.

It's the same data as the Gap Detail View (Day 24), but framed around
one policy section with ALL its matches ranked — not one regulation at
a time. This is the natural "section-level" unit the roadmap calls for.

─────────────────────────────────────────────────────────────────────
SECTION OUTPUT CARD WIREFRAME
─────────────────────────────────────────────────────────────────────

┌──────────────────────────────────────────────────────────────────────┐
│  BSA-AML-Policy §4.2 — Currency Transaction Reporting (CTR)           │
│  Parent: SECTION 4: TRANSACTION MONITORING                            │
│  ────────────────────────────────────────────────────────────────── │
│                                                                        │
│  YOUR POLICY TEXT:                                                    │
│  "The Bank shall file a Currency Transaction Report (CTR) for any     │
│   cash transaction exceeding $10,000..."                              │
│                                                                        │
│  ────────────────────────────────────────────────────────────────── │
│  RANKED REGULATION MATCHES                                            │
│                                                                        │
│  █ HIGH      [FinCEN] CTR threshold update                            │
│              "...threshold for cash-intensive businesses is           │
│               reduced to $5,000..."                                   │
│              dense similarity: 0.61   [View full comparison]          │
│                                                                        │
│  ▓ MEDIUM    [OCC] BSA exam priorities                                 │
│              "...examiners will focus on CTR filing timeliness..."    │
│              dense similarity: 0.48   [View full comparison]          │
│                                                                        │
│  ▒ LOW       [FDIC] Annual compliance bulletin                         │
│              "...general reminder of BSA recordkeeping..."            │
│              dense similarity: 0.38   [View full comparison]          │
│                                                                        │
│  ░ N/A       [FRB] Reserve requirement ratio notice                    │
│              dense similarity: 0.21   (hidden by default)             │
│                                                                        │
│  [Mark §4.2 Reviewed]  [Create Task from HIGH finding]                │
└──────────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
EMPTY / LOW-SIGNAL STATE (Day 24 finding applies here)
─────────────────────────────────────────────────────────────────────

┌──────────────────────────────────────────────────────────────────────┐
│  BSA-AML-Policy §1.1 — Purpose                                         │
│  ────────────────────────────────────────────────────────────────── │
│                                                                        │
│  No High or Medium impact findings for this section.                  │
│                                                                        │
│  5 regulations checked, all below similarity threshold (0.35).        │
│  [Show low-relevance matches anyway]                                   │
└──────────────────────────────────────────────────────────────────────┘

This state is expected and CORRECT for most sections most of the time —
a section only needs Sarah's attention when something actually changed.
Per Day 24's finding, most of the 25 dev-DB documents score below 0.35
against these 3 policies, so most sections currently show this state.
That's the classifier working as designed, not a bug.

─────────────────────────────────────────────────────────────────────
BADGE -> impact_results.json FIELD MAP
─────────────────────────────────────────────────────────────────────

  █ HIGH    -> match.impact_level == "high"     (dense_score >= 0.55)
  ▓ MEDIUM  -> match.impact_level == "medium"   (dense_score >= 0.45)
  ▒ LOW     -> match.impact_level == "low"      (dense_score >= 0.35)
  ░ N/A     -> match.impact_level == "not_applicable" (< 0.35, hidden by default)

  Card header   <- section.policy_name, section.section_id, section.section_title
  Parent line   <- section.parent_section
  Match rows    <- section.matches[], sorted by dense_score (already RRF-ranked)
  Similarity    <- match.dense_score
  Regulation    <- match.regulation_title, match.source_agency
  Excerpt       <- match.matched_chunk_text

─────────────────────────────────────────────────────────────────────
IMPLEMENTATION NOTE
─────────────────────────────────────────────────────────────────────

Day 25 scope: classifier.py (thresholds v1) + this wireframe. Thresholds
(0.55 / 0.45 / 0.35) are a documented starting point, NOT validated
against labeled data — Day 26 builds the 30-pair golden set that will
confirm or recalibrate these numbers against the 80% CI gate target.

If Day 26 finds thresholds need adjustment, only classify_impact()'s
constants change — this UX and the matches.json -> impact_results.json
pipeline stay the same.
