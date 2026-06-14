# Day 14B — Data Sourcing: Golden Eval Set + Synthetic Policy Documents

**Date:** 2026-06-02
**Feature:** F2 (golden set) + F3 (policy PDFs)
**KM:** Data sourcing discipline — golden sets must exist before eval week
**Status:** Complete — 50 golden examples + 3 policy documents committed

---

## What Was Built

| File | Size | Purpose |
|------|------|---------|
| `fixtures/golden/summaries.json` | 50 entries | Ground truth for RAGAS F2 evaluation |
| `fixtures/policies/BSA-AML-Policy.txt` | 8.8KB, 10 sections | Synthetic BSA/AML compliance policy for F3 testing |
| `fixtures/policies/Fair-Lending-ECOA-Policy.txt` | 8.5KB, 9 sections | Synthetic fair lending / ECOA policy for F3 testing |
| `fixtures/policies/TRID-Mortgage-Disclosure-Policy.txt` | 9.7KB, 9 sections | Synthetic TRID disclosure policy for F3 testing |

---

## Golden Set Composition (50 entries)

### By agency
| Agency | Count | Rationale |
|--------|-------|-----------|
| fed | 24 | Most documents ingested from Fed; covers broadest range of types |
| cfpb | 9 | Highest-impact consumer compliance agency for community banks |
| fincen | 6 | BSA/AML compliance is a top exam priority |
| fdic | 5 | FDIC-specific guidance and enforcement |
| occ | 3 | OCC preemption and guidance for national banks |
| federal_register | 3 | Administrative notices and joint-agency rules |

### By doc type
| Type | Count | Notes |
|------|-------|-------|
| other | 33 | Includes meeting minutes, announcements, administrative notices |
| enforcement | 6 | Individual and institutional enforcement actions |
| proposed_rule | 4 | Comment opportunities and ANPRs |
| final_rule | 3 | Highest-urgency documents with compliance deadlines |
| guidance | 3 | Supervisory expectations without legal deadlines |
| faq | 1 | Clarification documents |

### By expected routing
| Decision | Count | % |
|----------|-------|---|
| dismiss | 27 | 54% — informational, no action required |
| review | 17 | 34% — needs human check before acting |
| approved | 3 | 6% — high confidence, ready to act |
| escalate | 3 | 6% — low confidence or NER conflict |

### By difficulty
| Level | Count | What it tests |
|-------|-------|---------------|
| easy | 22 | Clear documents, obvious routing, no edge cases |
| medium | 15 | Ambiguous scope, asset thresholds, mixed signals |
| hard | 13 | Long complex rules, conflicting signals, nuanced institution scope |

---

## Why These Three Policy Documents?

**BSA/AML Policy** — covers FinCEN's BSA requirements including:
- CDD/KYC requirements (Section 3) → F3 should flag FinCEN CDD rules as impacting §3
- CTR and SAR requirements (Section 4) → F3 should flag FinCEN SAR threshold changes as impacting §4
- Beneficial ownership (Section 3.3) → F3 should flag FinCEN beneficial ownership rules as impacting §3.3

**Fair Lending / ECOA Policy** — covers CFPB Regulation B including:
- Section 2 (prohibited bases) → F3 should flag CFPB disparate impact amendments as impacting §2
- Section 3 (credit underwriting, SPCPs) → F3 should flag CFPB SPCP amendments as impacting §3
- Section 6 (Section 1071 placeholder) → F3 should flag small business lending rules as impacting §6

**TRID Policy** — covers CFPB Regulation Z mortgage disclosures including:
- Section 2 (Loan Estimate) → F3 should flag TRID amendments as impacting §2
- Section 3 (Closing Disclosure) → F3 should flag Closing Disclosure changes as impacting §3
- Section 7 (Tolerance cures) → F3 should flag tolerance changes as impacting §7

These three policies represent the highest-risk compliance areas for community banks and will produce meaningful F3 mapping results.

---

## What Makes a Good Golden Set Entry?

Each entry has:
- `key_facts`: 3-5 specific facts MUST appear in a faithful summary
- `must_not_contain`: Hallucinated claims that would indicate unfaithfulness
- `expected_effective_date`: Correct date (or null) for date extraction testing
- `expected_institution_types`: Correct scope — neither too broad nor too narrow
- `routing_expected`: The correct routing decision
- `no_action_required`: True/False — critical for "No immediate action required" testing
- `difficulty`: Easy/medium/hard — allows weighted eval scoring

The `must_not_contain` fields are the most important for catching hallucination. Example:
- Entry 41 (Climate Risk Rule): must NOT contain "all community banks must assess climate risk"
- Entry 25 (GENIUS Act): must NOT contain "all community banks must issue stablecoins"
- Entry 1 (CFPB Reg B): must NOT confuse the SPCP amendments with the Section 1071 lending data rule

---

## Why Hand-Labeling (Not LLM-Generated)?

The golden set is ground truth. If Claude generated the labels and Claude generates the summaries, we measure self-consistency, not accuracy. Two types of Claude errors would be invisible:
1. Systematic misunderstandings (Claude consistently misreads regulatory scope)
2. Common hallucinations (Claude consistently invents the same wrong dates)

Hand-labeling by reading actual documents catches both. The 2+ hours spent today will make Week 3 RAGAS scores meaningful instead of circular.

---

## PM Insight

**The golden set is the product's acceptance test for F2 — permanently.**

Not just for Week 3. Every time the prompt changes (v3, v4, v5...), every time the chunking strategy changes, every time the model changes — the golden set tells us whether quality went up or down.

Building it before Week 3 means we have a stable reference point from Day 1 of F2 evaluation. Teams that build the eval set after the model don't have this — they're always comparing against a moving target.

The 50-entry composition also encodes product judgment:
- 54% dismiss = the product's ability to identify non-actionable documents
- 34% review = the product's ability to flag genuine uncertainty
- Only 6% approved = high-confidence summaries are rare for short Fed press releases (our current corpus)

This distribution will shift as we summarise more structured regulatory rules (CFPB Final Rules, FinCEN rulemakings) where full document text is available and confidence should be higher.

---

## Week 3 Preview — What Uses These Files

| Day | What uses it |
|-----|-------------|
| 15 | Embedding benchmark — F3 will embed BSA/TRID/ECOA policies |
| 18 | RAGAS eval on 30 summaries — uses `summaries.json` entries 1-30 |
| 19 | Complete golden set to 50, CI pipeline — uses full `summaries.json` |
| 22+ | F3 policy upload testing — uses the 3 `.txt` policy files |
