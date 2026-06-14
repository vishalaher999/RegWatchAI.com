# RAGAS Baseline Report — F2 AI Summarisation
# Day 18 | Week 3 Evaluation

**Date:** 2026-06-02
**Entries evaluated:** 20 of 30 (10 not yet summarised)
**Pipeline:** hierarchical chunking + BM25(50) → dense(15) → cross-encoder rerank(8) → claude-sonnet-4-20250514 + prompt v2 + NER + router

---

## Results vs Targets

| Metric | Score | Target | Status |
|--------|-------|--------|--------|
| **Faithfulness** | **0.685** | ≥ 0.75 | **FAIL** |
| Hallucination rate | 0.100 | < 0.05 | FAIL |
| Answer relevance | 0.769 | — | INFO |
| Date accuracy | 0.900 | — | GOOD |
| Institution accuracy | 0.800 | — | GOOD |
| Routing accuracy | 0.850 | — | GOOD |
| No-action accuracy | 0.950 | — | EXCELLENT |
| What-changed (B/A) | 0.200 | — | WEAK |

**Overall: FAIL — faithfulness 0.685 vs target 0.75**

The good news: we're 0.065 below target. That's a 9.5% gap. Day 21 (fix top 3 failure modes) is designed exactly for this.

---

## What's Failing and Why

### Failure Mode 1: Missing "no compliance requirements" signal (most common)

**Documents:** Entries 9, 15, 16, 18, 19, 20
**Pattern:** Administrative/informational documents (enforcement terminations, personnel announcements, research reports, meeting minutes)
**Missing facts:** "No compliance requirements", "No banking regulatory implications", "Research publication — no compliance requirements"
**Root cause:** Claude correctly routes these as "dismiss" but omits explicitly stating the no-compliance nature in its key facts. The router says "no action" but the summary doesn't always include the specific phrase.
**Fix:** Add a rule to prompt v3: for informational documents, the summary MUST explicitly state "This is [type of document]. No compliance action required for [institution types]."

### Failure Mode 2: Missing specific regulatory program references

**Documents:** Entry 4 (ILSA), Entry 5 (Regulation V / human trafficking)
**Pattern:** Niche regulatory programs that Claude summarises accurately but at the wrong level of specificity
**Missing facts:** "Interstate Land Sales Full Disclosure Act", "Regulation V — human trafficking consumer reporting"
**Root cause:** Claude captures the gist but not the specific regulatory citation. The key_fact check requires exact or near-exact phrase match.
**Fix:** Strengthen prompt v3: "Always name the specific regulation, statute, or program referenced. Do not say 'this regulation'; say 'the Interstate Land Sales Full Disclosure Act (ILSA)'."

### Failure Mode 3: What-changed quality too low (0.200)

**Only 1 of 5 rule-change documents uses BEFORE/AFTER structure**
**Root cause:** The BEFORE/AFTER instruction works well for major rule changes (CFPB Reg B) but Claude reverts to descriptive language for smaller changes ("The Fed issued a notice stating...")
**Fix:** Prompt v3 must make BEFORE/AFTER mandatory for ALL documents, not just obvious rule changes.

### Failure Mode 4: Hallucination rate 0.100 (above 0.05 target)

**Documents:** Entries 4, 5, 17 — Claude added "community banks must" language where not warranted
**Root cause:** Claude over-applies the community bank lens even for documents that don't affect community banks (land developer regulations, state-chartered bank rules)
**Fix:** Prompt v3: "If the document explicitly states it does NOT apply to community banks, your summary must say so. Do not apply community bank implications where the document doesn't mention them."

---

## What's Working Well

### Date accuracy: 0.900 (excellent)
The NER + hierarchical priority retrieval combination successfully finds effective dates buried in long documents. Date accuracy improved from ~32% (keyword-only, Day 8) to 90% (Day 18). This is the single biggest improvement in the F2 pipeline.

### No-action accuracy: 0.950 (excellent)
Prompt v2's explicit "No immediate action required for community banks" permission is working. 95% of informational documents are correctly identified as no-action. The prompt v2 change on Day 11 was the right call.

### Routing accuracy: 0.850 (good)
The multi-signal confidence router correctly handles most documents. Failures are on enforcement terminations — Claude correctly writes them as "no action required" but the router sometimes routes them as REVIEW instead of DISMISS.

### Institution accuracy: 0.800 (good)
The reranker consistently retrieves institution-type-relevant chunks. Asset thresholds ($10B or less) are being captured. The 20% failure is mostly on documents that legitimately have no institution scope (enforcement terminations, personnel notices).

---

## Top 5 Documents to Fix on Day 21

| # | Entry | Faithfulness | Primary failure |
|---|-------|-------------|-----------------|
| 1 | SHED Report | 0.25 | Missing: research publication, no compliance |
| 2 | Enforcement termination | 0.33 | Missing: no new compliance requirements |
| 3 | ILSA comment request | 0.50 | Missing: ILSA citation, affects land developers |
| 4 | Trafficking/Reg V | 0.50 | Missing: Regulation V citation |
| 5 | Payment account proposal | 0.50 | Missing: public comment period, proposed rule |

---

## The Gap Analysis: 0.685 → 0.750

We need +0.065 faithfulness. Based on the failure analysis:

| Fix | Expected improvement | Difficulty |
|-----|---------------------|------------|
| Mandatory "no compliance" statement for informational docs | +0.03 | Easy — prompt change |
| Specific regulatory citation requirement | +0.02 | Easy — prompt change |
| BEFORE/AFTER mandatory for all docs | +0.01 | Easy — prompt change |
| Reduce hallucination (community banks must) | +0.01 | Easy — prompt change |

**Total expected gain: +0.07** → projected faithfulness after Day 21: **0.755 (PASS)**

---

## Automation Rate vs Override Rate

| Metric | Target | Current |
|--------|--------|---------|
| Human override rate | < 20% | ~24% (review queue) |
| Automation rate (DISMISS) | — | 64% |
| APPROVED without review | — | 12% |

The override rate gap (24% vs 20% target) is related to the faithfulness gap — if we improve faithfulness, fewer documents go to the review queue, and the override rate drops.

---

## Week 3 Remaining Schedule

| Day | Plan | Status |
|-----|------|--------|
| 18 | RAGAS eval baseline | **Done today — 0.685 FAIL** |
| 19 | Complete golden set CI pipeline | Next |
| 20 | LLM-as-judge calibration | Next |
| 21 | Fix top 3 failures → RAGAS ≥ 0.75 | Repair day |

The path is clear: 3 prompt changes + re-eval. Day 21 is the fix day.
