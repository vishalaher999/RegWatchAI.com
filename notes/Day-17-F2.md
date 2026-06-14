# Day 17 — F2 v2: Cross-Encoder Reranker

**Date:** 2026-06-02
**Feature:** F2 — AI Summarisation v2
**KM:** #162 Reranking
**Status:** Complete — full retrieval stack live: BM25(50) → dense(15) → reranker(8)

---

## What Was Built

| File | Change |
|------|--------|
| `src/f2_summarise/reranker.py` | CrossEncoderReranker class, rerank_chunks() function |
| `src/f2_summarise/retriever.py` | retrieve_for_reranking() — optimised BM25(50)→dense(15) pipeline |
| `src/f2_summarise/summariser.py` | USE_RERANKER=True, full pipeline wired, reranker_used in AuditLog |
| `docs/wireframes/streaming-ux-v1.md` | Streaming summary UX — token-by-token reveal |

---

## The Full Retrieval Stack (Day 17 Final)

```
Document (400K chars, 470 chunks)
    │
    ▼ BM25 pre-filter (free, instant)
    50 keyword-matched candidates
    │
    ▼ Dense embedding (all-mpnet-base-v2)
    Embed 50 chunks → cosine similarity → top-15 by RRF
    │
    ▼ Cross-encoder reranker (ms-marco-MiniLM-L-6-v2)
    Score each (compliance_query, chunk) pair → top-8
    │
    ▼ Claude (claude-sonnet-4-20250514, temp=0.2)
    Structured JSON summary
```

**Key improvements vs Day 8 keyword-only:**
- Chunks retrieved: 6 → 8
- Context quality: keyword exact match → semantic + exact + precise reranking
- Date retrieval P@3: ~32% (estimated) → 84.5% (measured Day 15)

---

## Performance: 261s → 122s

| Day | Method | Time (400K doc) | Chunks embedded |
|-----|--------|-----------------|-----------------|
| 16 | Hybrid (all 470 chunks embedded) | 261s | 470 |
| 17 | BM25(50)→dense(15)→rerank | 122s | 50 |

Speedup: **2.1x** on first run (model loading included). After models cached in memory, subsequent documents take ~20-30 seconds.

Note: 122s includes downloading the cross-encoder model (44s one-time). Future runs will be faster.

---

## Quality Improvement on CFPB Reg B

| Field | Keyword (Day 13) | Hybrid+Reranker (Day 17) |
|-------|----------------|--------------------------|
| institution_types | 1 category | 3 categories with $10B threshold |
| what_changed | Vague delta | Clear BEFORE/AFTER with specific provisions |
| effective_date | 2026-07-21 | 2026-07-21 (consistent) |
| confidence | 75 | 77 (NER confirmed date) |

---

## KM Concept: #162 Cross-Encoder Reranking

**Bi-encoder vs cross-encoder:**

```
Bi-encoder (Days 15-16):
  encode(query) → vector_q          encode(chunk) → vector_c
  score = cosine_similarity(q, c)
  ✓ Fast (pre-compute chunk vectors once)
  ✗ Query and chunk never interact during encoding

Cross-encoder (Day 17):
  encode(query + [SEP] + chunk) → relevance score
  ✓ Full attention over both texts simultaneously
  ✓ "effective date" in query ↔ "takes effect on" in chunk — relationship captured
  ✗ Can't pre-compute — must run fresh for every (query, chunk) pair
  ✗ O(n) in candidates — must pre-filter to small set first
```

**Why MS-MARCO trained model?**
MS-MARCO is Microsoft's dataset of 140 million real search queries + relevant passages. A model trained on it has seen millions of examples of "this query is relevant to this passage." Regulatory queries ("what is the compliance deadline?") are similar to web search queries — the model generalises well.

**The pipeline is the product:**
Each layer fixes a specific failure mode:
- BM25 → finds exact regulatory citations the semantic model misses
- Dense → finds semantic equivalents ("implementation date" = "compliance deadline")
- Reranker → models the query-chunk relationship, final precision filter
- Claude → generates the summary from the best context

No single layer is good enough alone. Together they give us the quality of an expensive large context window at the cost of a small, fast pipeline.

---

## Streaming UX

Streaming requires FastAPI SSE (Week 6). MVP for now: descriptive progress bar in Streamlit with 4 stage labels. Design committed to `docs/wireframes/streaming-ux-v1.md`.

---

## Tests

90/90 still passing. No new tests added — reranker tested live on real documents.
