# Day 11 — F2 Prompt Engineering v2 + Officer Edit UX

**Date:** 2026-06-02
**Feature:** F2 — AI Summarisation
**KM:** #88 Abstractive Summary
**Status:** Complete — prompt v2 live, before/after comparison demonstrated

---

## What Was Built

| File | Change |
|------|--------|
| `src/f2_summarise/prompts.py` | Rewritten system prompt v2 — BEFORE/AFTER structure, actionable why_it_matters, stricter null discipline |
| `src/f2_summarise/summariser.py` | Added `reset_for_resummary()`, PROMPT_VERSION in AuditLog, chunk_strategy in AuditLog |
| `docs/wireframes/edit-ux-v1.md` | Officer edit UX — inline editing, change tracking, AuditLog integration |

---

## Before vs After — Prompt v1 vs v2

The most important improvement: **"No immediate action required" is now the correct default for informational documents.**

| Document | v1 why_it_matters | v2 why_it_matters |
|----------|------------------|------------------|
| Kevin Warsh | "New Fed leadership **may signal changes**... could affect..." | "**No immediate action required**. Personnel announcement, no regulatory change." |
| Enforcement action (Logan) | "Banks **should ensure** their compliance programs..." | "**No immediate action required**. Enforcement against an individual at another bank." |
| Resolution plan feedback | "Primarily affects largest organizations..." | "**No immediate action required** for community banks. [Threshold explained]." |
| Discount rate minutes | "Banks **should review** the full minutes..." | "**No immediate action required**. Historical meeting minutes." |

**One document with real action (Reg B)** still correctly says:
> "Community banks and credit unions must evaluate their existing special purpose credit programs for compliance with the amended Regulation B requirements."

v2 is more honest, more specific, and wastes less of Sarah's time.

---

## Key Prompt Changes in v2

### 1. what_changed — forced BEFORE/AFTER structure

**v1 instruction:** "the specific delta from before this rule"
**v2 instruction:** "Use this structure: 'Previously: [old rule]. Now: [new rule].'"

The explicit template forces Claude to think about the delta, not just describe the document.

### 2. why_it_matters — explicit "no action" permission

**v1 instruction:** "business consequence for a community bank or credit union"
**v2 instruction:** "What must Sarah do THIS WEEK, THIS MONTH, or BY [DATE]? If no action required: 'No immediate action required for community banks. [One-sentence reason].'"

The old prompt had no permission to say "nothing to do here." Claude padded every response with generic compliance advice to avoid appearing useless. The new prompt explicitly grants permission to say "no action required" — which is the correct answer for 80% of regulatory publications.

### 3. Confidence score — honest calibration

**v1 instruction:** Generic description
**v2 instruction:** Explicit score mapping (90-100 = all fields populated, 70-79 = incomplete excerpts, etc.)

Kevin Warsh went from 85 (v1, slightly uncertain) to **95** (v2, correctly confident — all facts available in the excerpt).

### 4. Null discipline — explicit severity

**v1:** "If not stated, return null. NEVER infer or guess."
**v2:** "Return null if not explicitly stated. A wrong date is worse than null. Null tells Sarah to check; a wrong date causes a missed deadline."

The stakes are now in the prompt, not just the instruction.

---

## KM Concept: #88 Abstractive Summarisation

**Extractive vs Abstractive:**

| Type | Method | Example |
|------|--------|---------|
| Extractive | Copy important sentences verbatim | "The final rule is effective July 21, 2026." |
| Abstractive | Understand and rewrite | "Community banks have until July 21, 2026 to update their ECOA data collection procedures." |

Claude does abstractive summarisation. The quality of abstraction depends entirely on the prompt:

**Bad abstraction (v1):** "The rule amends Regulation B..."
→ Claude just rephrased the title. No understanding demonstrated.

**Good abstraction (v2):** "Previously: Reg B required X. Now: Reg B requires Y. Banks with SBA programs must update by [date]."
→ Claude understood the delta and translated it into an action.

The prompt is the interface between "what Claude knows" and "what Claude tells Sarah." Better prompt = better translation.

---

## Prompt Versioning for SR 11-7

Every AuditLog entry now contains:
```json
{
  "model": "claude-sonnet-4-20250514",
  "prompt_version": "v2",
  "chunk_strategy": "hierarchical",
  "confidence_score": 95,
  ...
}
```

If we discover prompt v2 systematically fails on a class of documents (e.g., always marks enforcement actions as needing action), we can query AuditLog for `prompt_version = "v2"` and identify all affected summaries for re-run.

This is the model risk management principle from SR 11-7 applied to prompts: version everything, log everything, be able to identify and correct systematic errors.

---

## Officer Edit UX — Why It's a Product Decision, Not Just a Feature

**Without edit:**
Sarah trusts the AI → acts on wrong summary → bank gets examination finding → "RegWatch told me."

**With edit:**
Sarah reviews → corrects if needed → AuditLog records her correction → she is the responsible officer.

The override rate dashboard (target <20% of summaries edited) is also a product quality metric. If Sarah edits 50% of summaries, the prompt is broken and needs a v3. If she edits <5%, the prompt may be producing content that looks right but Sarah isn't actually reading carefully.

The 20% target comes from the roadmap: "Human override rate (summaries): Tracked (target <20%)" in the metrics table.

---

## PM Insight

**Prompt engineering is product specification.**

When you write a prompt, you are specifying the product's behaviour in natural language. Every word matters. "What changed" produces one kind of output. "What changed — use BEFORE/AFTER structure" produces a completely different, better output.

The difference between v1 and v2 is not the model (same Claude Sonnet), not the chunking (same hierarchical), not the retrieval (same keyword scorer). The difference is 200 words of better instructions. That's prompt engineering: the highest-leverage, cheapest improvement available in any LLM product.

The officer edit UX closes the loop: it makes Sarah's corrections visible and logged. Without it, the AI improves in a vacuum. With it, every edit Sarah makes is a labeled training signal for understanding where the prompt still fails.
