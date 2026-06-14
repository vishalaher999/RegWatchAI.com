# Day 13 — F2 Confidence Router + Review Queue

**Date:** 2026-06-02
**Feature:** F2 — AI Summarisation
**KM:** #115 System Prompts + Routing Logic
**Status:** Complete — router live, dashboard has 3 tabs, review queue working

---

## What Was Built

| File | Change |
|------|--------|
| `src/f2_summarise/router.py` | Multi-signal confidence router — 6 routing rules, 4 decisions |
| `src/f2_summarise/summariser.py` | Router wired in, routing decision in AuditLog |
| `dashboard/app.py` | 3-tab layout: Feed / Review Queue / Summaries |
| `dashboard/components.py` | `render_review_card()` + `render_summary_card()` added |

---

## Router Decision Tree

```
Input: summary dict + doc_type + NER delta
                         ↓
Informational doc + "no action" + conf ≥ 70?  → DISMISS (priority 5)
                         ↓ no
NER date conflict?                             → ESCALATE (priority 1)
                         ↓ no
Adjusted confidence < 60?                     → ESCALATE (priority 2)
                         ↓ no
Critical fields missing?                       → ESCALATE/REVIEW (priority 1-2)
                         ↓ no
Adjusted confidence < 80?                     → REVIEW (priority 1-3 by doc type)
                         ↓ no
High confidence                               → APPROVED (priority 5)
```

---

## Live Routing Results (5 documents)

| Document | Conf | Router Decision | Priority | Why |
|----------|------|----------------|----------|-----|
| Kevin Warsh sworn in | 95 | **No Action** | 5 | Informational, "no action required" |
| Resolution plan letters | 85 | **No Action** | 5 | Informational, "no action required" |
| Enforcement (Crystal Moore) | 75 | **Escalate** | 2 | Missing fields for enforcement doc |
| Enforcement (Nakia Logan) | 65 | **Needs Review** | 2 | Low confidence, enforcement |
| Discount rate minutes | 65 | **Needs Review** | 3 | Low confidence, informational |

**Key win:** Kevin Warsh (85-95 conf) was previously in the review queue because 95 > 80 but the "No Action" dismiss rule correctly removes it. The review queue now contains only documents that genuinely need action.

---

## KM Concept: #115 System Prompts + Routing

**System prompt as a cost lever:**
Every document in the review queue costs Sarah ~5 minutes to process. If the prompt is better (fewer low-confidence outputs), the review queue shrinks, and Sarah saves time. The prompt v2 changes on Day 11 directly reduced the review queue by auto-identifying "no action" documents — the router operationalises that in the routing decision.

**Routing as product strategy:**
A well-designed router makes the product feel intelligent. Without routing, Sarah sees 50 documents in the review queue and ignores it. With routing, she sees 3 Escalate items (actual problems) and 5 Review items (quick checks). The queue is manageable, so she uses it.

The target: < 20% of summaries in the review queue. Based on today's run: 3/5 in queue = 60%. High because our current documents are short Fed press releases without formal structure. When we summarise proper CFPB Final Rules (400K chars, explicit structure), confidence will be higher and the queue will shrink.

---

## Dashboard — Now Has 3 Tabs

Tab 1: Feed (all 111 documents, F1 filters)
Tab 2: Review Queue (documents needing human check, sorted by priority)
Tab 3: Summaries (approved AI summaries, ready to act on)

Run: `streamlit run dashboard/app.py`

---

## Tests

90/90 passing (no new tests added — router tested live against real summaries).

---

## PM Insight

**The router is the product's judgment layer.**

Raw AI confidence scores are not actionable. "75/100" tells Sarah nothing. "Escalate — NER and LLM disagree on the compliance deadline" tells her exactly what to check. The router translates a number into an action.

The routing decision also creates audit evidence. Every AuditLog entry now contains: routing_decision, routing_priority, routing_reasons. An examiner can see not just "the AI produced a summary" but "the AI produced a summary, assessed it as needing review because NER found a date conflict, and Sarah reviewed it before acting."

That's the full audit chain SR 11-7 requires: model decision → routing decision → human review → action. The router is the middle link.
