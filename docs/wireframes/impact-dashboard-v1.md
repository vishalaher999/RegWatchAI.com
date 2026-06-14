# Impact Dashboard — F3 Policy Impact Mapping
# Version 1 | Day 23 | High / Medium / Low / N-A Heatmap

## Who This Dashboard Serves

Sarah (CCO) needs to answer: "Which parts of MY policies does this new
regulation actually touch?" — without reading the full regulation or
re-reading her whole policy library.

The heatmap is the entry point. It shows, at a glance, every policy
section crossed with every recent regulation, colour-coded by impact.
Sarah drills into the cells that matter (High/Medium) and ignores the rest.

This is the screen referenced in the Week 4 exit gate:
"Sarah uploads a BSA policy PDF and within 5 minutes sees which sections
are flagged High/Medium impact against a recent CFPB rule, with a
side-by-side view."

─────────────────────────────────────────────────────────────────────
IMPACT HEATMAP WIREFRAME
─────────────────────────────────────────────────────────────────────

┌──────────────────────────────────────────────────────────────────────┐
│  REGWATCH AI — POLICY IMPACT MAP                                      │
│  ────────────────────────────────────────────────────────────────── │
│                                                                        │
│  Policy: [BSA-AML-Policy v2 ▾]      Regulations: [Last 30 days ▾]    │
│                                                                        │
│         CFPB Final Rule    OCC Guidance    FinCEN Advisory   FRB Notice│
│         "Reg B small biz"  "BSA exam      "CTR threshold     "Reserve │
│                             priorities"     update"           rqmts"  │
│  ───────────────────────────────────────────────────────────────────│
│  §3.1   ░ N/A              ░ N/A          ░ N/A             ░ N/A    │
│  Risk                                                                  │
│  Assess.                                                               │
│  ───────────────────────────────────────────────────────────────────│
│  §4.1   ░ N/A              ▓ MEDIUM       ░ N/A             ░ N/A    │
│  SAR ID                                                                │
│  ───────────────────────────────────────────────────────────────────│
│  §4.2   ░ N/A              ▓ MEDIUM       █ HIGH            ░ N/A    │
│  CTR                                                                   │
│  ───────────────────────────────────────────────────────────────────│
│  §4.3   ░ N/A              ░ N/A          ░ N/A             ░ N/A    │
│  Monitor                                                               │
│  ───────────────────────────────────────────────────────────────────│
│  §7.2   █ HIGH              ░ N/A          ░ N/A             ░ N/A    │
│  CDD/                                                                  │
│  Beneficial                                                            │
│                                                                        │
│  Legend:  █ HIGH   ▓ MEDIUM   ▒ LOW   ░ N/A                          │
│                                                                        │
│  2 sections need review (High/Medium impact)                          │
└──────────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
DRILL-IN: GAP DETAIL VIEW (click a High/Medium cell)
─────────────────────────────────────────────────────────────────────

┌──────────────────────────────────────────────────────────────────────┐
│  BSA-AML-Policy §4.2 — Currency Transaction Reporting (CTR)           │
│  vs. FinCEN Advisory "CTR threshold update"     [█ HIGH IMPACT]       │
│  ────────────────────────────────────────────────────────────────── │
│                                                                        │
│  YOUR POLICY SAYS (§4.2):              │  THE REGULATION SAYS:        │
│  ┌────────────────────────────────────┐│┌──────────────────────────┐│
│  │ The Bank shall file a Currency      │││ Effective Jan 1 2027,    ││
│  │ Transaction Report (CTR) for any    │││ the CTR threshold for    ││
│  │ cash transaction exceeding $10,000. │││ certain cash-intensive   ││
│  │                                      │││ businesses is reduced    ││
│  │                                      │││ to $5,000...             ││
│  └────────────────────────────────────┘│└──────────────────────────┘│
│                                                                        │
│  WHY THIS IS HIGH IMPACT:                                             │
│  Your policy's $10,000 threshold conflicts with the new $5,000        │
│  threshold for cash-intensive businesses. Section 4.2 must be         │
│  updated before the Jan 1 2027 effective date.                        │
│                                                                        │
│  Match confidence: 0.84 (similarity score)                            │
│  Model: claude-sonnet-4-20250514 | Prompt: impact-v1                  │
│                                                                        │
│  [Create Task]  [Mark Reviewed]  [Dismiss — Not Applicable]           │
└──────────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
SUMMARY METRICS ROW (top of dashboard)
─────────────────────────────────────────────────────────────────────

┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│ Policies   │ │ Sections   │ │ Regulations│ │ High/Med   │
│ Mapped     │ │ Indexed    │ │ Checked    │ │ Findings   │
│    3       │ │    72      │ │    25      │ │     2      │
└────────────┘ └────────────┘ └────────────┘ └────────────┘

─────────────────────────────────────────────────────────────────────
IMPLEMENTATION NOTE
─────────────────────────────────────────────────────────────────────

Day 23 scope: dual-index vector store only (src/f3_impact/vectorstore.py,
build_indexes.py). This wireframe describes the target UX once Day 24
(similarity matcher) and Day 25 (impact classifier High/Med/Low/N/A)
produce the data this heatmap needs:

  heatmap cell (policy_section, regulation) -> impact_level

For now, this wireframe sets the target shape:
  - Rows = policy sections (from extractor.py, 72 sections across 3 policies)
  - Columns = recent regulations (from regulation_chunks index, 25 docs)
  - Cell = impact classification (Day 25) derived from similarity score
    (Day 24, powered by the regulation_chunks VectorIndex built today)

─────────────────────────────────────────────────────────────────────
DAY 24 UPDATE: GAP DETAIL VIEW <-> matches.json FIELD MAP
─────────────────────────────────────────────────────────────────────

src/f3_impact/matcher.py now produces data/f3_indexes/matches.json —
one entry per policy section, each with up to 5 regulation matches.
The Gap Detail View fields map directly to this output:

  matches.json field                -> Gap Detail View element
  ─────────────────────────────────────────────────────────────
  policy_name, section_id,
  section_title                     -> "BSA-AML-Policy §4.2 —
                                          Currency Transaction
                                          Reporting (CTR)" header
  matches[i].regulation_title,
  matches[i].source_agency          -> "vs. [Agency] [Title]" subheader
  matches[i].matched_chunk_text     -> "THE REGULATION SAYS:" panel
  (policy section's own text)       -> "YOUR POLICY SAYS:" panel
  matches[i].score                  -> "Match confidence: 0.84"
                                        (RRF score, not yet a 0-1
                                        probability — Day 25 maps
                                        score -> High/Med/Low/N/A)

NOTE on real scores (Day 24 run against live data):
RRF scores for the 25 real summarised documents currently in the DB
are low (~0.03, near the RRF floor of ~0.033 for a top-1/top-1 hit).
None of the 25 fetched documents happen to be about CTR thresholds,
SAR filing, etc. — so §4.2's "top 5" are the *least irrelevant*
matches available, not strong hits. This is a data-coverage gap
(small/random regulation corpus), not a matcher bug: the matcher
correctly returns its best candidates and a low score. Day 25's
classifier must treat low RRF scores as "Low/N/A impact" rather than
forcing every section into a High/Medium bucket. Day 26's 30 labeled
pairs (curated, not random) is what validates precision@5 properly.

Like Day 22's wireframe, this is a design artifact — no UI is built yet.
Streamlit dashboard implementation is Week 6 per CLAUDE.md.
