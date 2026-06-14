# Day 23 — Dual-Index Vector Store

**Date:** 2026-06-13
**Feature:** F3 — Policy Impact Mapping (Week 4, Day 2 of 7)
**KM:** #157 Dense retrieval
**Status:** Dual-index vector store built and verified end-to-end.

---

## What Was Built

| File | Change |
|------|--------|
| `src/f3_impact/vectorstore.py` | `VectorIndex` — local numpy + JSON vector store (upsert/query/save/load) |
| `src/f3_impact/build_indexes.py` | Builds `policy_sections` and `regulation_chunks` indexes |
| `tests/test_f3_vectorstore.py` | 5 tests against a fake embedding model |
| `docs/wireframes/impact-dashboard-v1.md` | Product: High/Med/Low/N/A heatmap + gap detail view |
| `data/f3_indexes/` | Generated indexes (gitignored) |
| `.gitignore` | Added `data/f3_indexes/` |
| `docs/ARCHITECTURE.md` | New entries for both files |

---

## Roadmap v2.2 — Day 23 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | #157 Dense retrieval | Applied directly — `VectorIndex.query()` is dense retrieval via cosine similarity on normalized mpnet embeddings |
| Engineering | Embed policy sections + regulation sections separately | `build_indexes.py` — two `VectorIndex` collections, `policy_sections` and `regulation_chunks` |
| Product | Impact dashboard wireframe: High/Med/Low/N/A heatmap | `docs/wireframes/impact-dashboard-v1.md` — heatmap + drill-in gap detail view |
| Deliverable | Dual-index vector store | Built and saved to `data/f3_indexes/` — 72 policy sections, 521 regulation chunks |

---

## A Scope Decision: Local Index, Not Real Pinecone

CLAUDE.md lists Pinecone as the target vector DB. But `.env` has no `PINECONE_API_KEY` — and F2 already established (Day 15) that local `sentence-transformers` embeddings are the project default: zero cost, no API rate limits, and compliance document content never leaves the machine during dev.

**Decision:** Built `VectorIndex` with the same shape a Pinecone-backed index would have — `upsert_batch()`, `query()`, persisted collection. The interface is the contract; the backend (local numpy vs. real Pinecone) is an implementation detail that can change later without touching any calling code. Same pattern as `DATABASE_URL` (SQLite dev → Postgres prod).

If/when a real Pinecone account exists (multi-tenant namespaces become relevant once there are multiple bank clients), only `vectorstore.py` changes.

---

## Verified Results

```
Building policy_sections index...
  [loaded]  all-mpnet-base-v2 (768d) in 8.8s
  72 sections indexed
Building regulation_chunks index...
  [loaded]  all-mpnet-base-v2 (768d) in 6.6s
  521 chunks indexed

Saved to data/f3_indexes/
```

**Smoke test** — query `policy_sections` for "cash transaction reporting threshold over ten thousand dollars":

```
0.566  BSA-AML-Policy §4.2 - Currency Transaction Reporting (CTR)
0.418  TRID-Mortgage-Disclosure-Policy §2.4 - Good Faith Tolerance Standards
0.417  BSA-AML-Policy §4.4 - Suspicious Activity Reports (SAR)
```

Top result is exactly right — confirms the embedding model correctly maps a plain-English description to the matching BSA section, even though "ten thousand dollars" never appears as digits in the query and the policy text says "$10,000".

All 8 F3 tests pass (3 extractor + 5 vectorstore).

---

## Why 521 Chunks From 25 Documents?

`chunk_hierarchical` (F2's Day 10 winner) splits on structural headers, then sentence-chunks prose between them — averaging ~21 chunks per document. This is the same chunker F2 uses for retrieval during summarisation, reused here so regulation text is split the same way regardless of which feature is matching against it.

---

## PM Insight: The Interface Is the Deliverable

Today's visible artifact is two `.npz`/`.json` files in `data/f3_indexes/` — not glamorous. But the real deliverable is `VectorIndex.query()` returning `[{"id", "score", "metadata"}, ...]`. Day 24's similarity matcher is now a thin loop:

```
for policy_section in policy_sections_index:
    matches = regulation_chunks_index.query(policy_section.text, top_k=5)
```

If that interface is solid (tested, verified against real data), Day 24 is straightforward. If it weren't, Day 24 would start with a vectorstore refactor instead of a matcher.

---

## Next: Day 24 (when user says "next")

Per roadmap v2.2: KM #159-160 Hybrid search | Eng: Semantic similarity — regulation chunk ↔ policy section matching | Product: Gap detail view | Deliverable: Similarity matcher v1.

Note: the gap detail view (drill-in UX) is already drafted in `impact-dashboard-v1.md` — Day 24's product work may be refining that rather than starting fresh.
