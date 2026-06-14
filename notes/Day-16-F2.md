# Day 16 — F2 v2: Hybrid Search (Dense + BM25 via RRF)

**Date:** 2026-06-02
**Feature:** F2 — AI Summarisation v2
**KM:** #158-160 Hybrid + RRF
**Status:** Complete — hybrid retrieval live, quality improvement demonstrated

---

## What Was Built

| File | Change |
|------|--------|
| `src/f2_summarise/retriever.py` | Added `hybrid_retrieve()` — RRF combination of dense + BM25 |
| `src/f2_summarise/summariser.py` | `USE_HYBRID_RETRIEVAL = True`, retrieval_method in AuditLog |
| `docs/Moat-Analysis-v1.md` | 5-moat analysis — F3 switching cost is the strongest |

---

## How Hybrid Retrieval Works

```
Document chunks (470 for CFPB Reg B)
         │
         ├──► BM25 ranking  ──────────────────────────────────────────────┐
         │    (keyword match + TF normalisation)                           │
         │    Best at: "12 CFR Part 1002", "Regulation B § 1002.6"        │
         │                                                                 │
         └──► Dense ranking ──────────────────────────────────────────────┤
              (all-mpnet-base-v2 cosine similarity)                        │
              Best at: semantic equivalents of "effective date"            │
                       even when document says "takes effect on"           │
                                                                           ▼
                                                         RRF combination
                                                  score = 1/(60 + rank_bm25)
                                                        + 1/(60 + rank_dense)
                                                                           │
                                                                           ▼
                                                     Top-k chunks by RRF score
                                             (+ hierarchical priority boosts)
```

---

## Quality Improvement: Keyword vs Hybrid

On CFPB Equal Credit Opportunity Act (Regulation B) — 400,865 chars, 470 chunks:

| Field | Keyword retrieval (Day 13) | Hybrid retrieval (Day 16) |
|-------|--------------------------|--------------------------|
| Chunks retrieved | 7 | 10 |
| Context size | 6,285 chars | 8,120 chars |
| `what_changed` | "Regulation B had certain provisions..." | "Previously: unclear standards for disparate impact. Now: new standards including prohibit basis showing standard" |
| `affected_institution_types` | 1 category | 3 categories (depository, non-depository, credit union) |
| `effective_date` | 2026-07-21 | 2026-07-21 (consistent) |

Hybrid retrieved 3 additional relevant chunks that keyword scoring missed, producing a more specific `what_changed` and broader institution scope.

---

## KM Concept: #158-160 Hybrid Search + RRF

**Why neither method alone is optimal:**

| Method | Strength | Weakness |
|--------|----------|----------|
| Dense (embeddings) | Semantic equivalents ("takes effect" = "effective date") | May miss exact citations ("12 CFR § 1002.6") |
| BM25 (keywords) | Exact term matching | Misses semantic variants ("deadline" vs "must comply by") |
| Hybrid (RRF) | Gets both | Slower (embedding time) |

**RRF mathematics:**
- Chunk ranked #1 by BM25 AND #1 by dense: score = 1/61 + 1/61 = 0.033
- Chunk ranked #1 by BM25 AND #20 by dense: score = 1/61 + 1/80 = 0.029
- Chunk ranked #50 by BM25 AND #50 by dense: score = 1/110 + 1/110 = 0.018
- Consensus between methods = highest score → correct behaviour

**Why k=60?** Prevents the #1 ranked chunk from dominating (1/1 = 1.0 vs 1/100 = 0.01 — too extreme). With k=60, #1 scores 0.016 vs #100 at 0.006 — a meaningful but not overwhelming difference.

---

## Performance Note

For the 400K CFPB Reg B document (470 chunks), hybrid retrieval took 261 seconds because it embeds all 470 chunks with all-mpnet-base-v2. This is slow for production. Solutions:
1. **Chunk limit before embedding:** Only embed top-50 chunks by BM25 score, then rerank with dense (reduces embedding calls from 470 to 50)
2. **Pre-compute and cache embeddings** per document in the DB
3. **Use all-MiniLM for speed** when document is very long (trade quality for speed)

For Week 3 evaluation purposes, 261s is acceptable. Day 17 (cross-encoder reranker) will also address this by working on a smaller candidate set.

---

## Moat Analysis Key Finding

The strongest moat is **F3 switching cost (5/5 strength)**. Once Sarah integrates her policy library and RegWatch AI has mapped regulations to her specific policies:
- Re-uploading costs 2–3 hours
- Re-running all historical mappings costs days
- Losing the institutional knowledge encoded in the mapping = priceless

**Critical implication:** Every week F3 launches later is a week without this moat being built. The roadmap correctly designates F3 as THE CORE (★). F1 and F2 are the on-ramp that gets clients to F3.

---

## Tests

90/90 still passing (no new tests added — hybrid tested live on real documents).

---

## PM Insight

**Hybrid search is a trust feature, not just a quality feature.**

When Sarah asks "why does it say November 15, 2026 when the original regulation says Q4 2026?" — the answer is better with hybrid retrieval. Keyword scoring found "Q4 2026" but missed the paragraph that defined it. Hybrid retrieval found both chunks: the one with "Q4 2026" (BM25) AND the one with "effective November 15" (dense). Claude had both in context and correctly resolved the ambiguity.

The product promise is "the AI read the whole document so you don't have to." Hybrid retrieval makes that promise more truthful by finding more of the relevant content — including regulatory citations that semantic models miss and semantic equivalents that keyword models miss.
