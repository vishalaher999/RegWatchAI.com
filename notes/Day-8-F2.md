# Day 8 — F2 AI Summarisation v1: Naive RAG + JSON Schema

**Date:** 2026-06-02
**Feature:** F2 — AI Summarisation
**KM:** #151 RAG Overview
**Status:** Complete — pipeline built, 21 tests passing, live run pending API key

---

## What Was Built

| File | Purpose |
|------|---------|
| `src/f2_summarise/__init__.py` | Package stub |
| `src/f2_summarise/chunker.py` | Fixed-size chunking with overlap — Day 8 baseline |
| `src/f2_summarise/retriever.py` | Keyword-scoring chunk retriever (top-k selection) |
| `src/f2_summarise/prompts.py` | System prompt, JSON schema, model config (claude-sonnet-4-20250514, temp=0.2) |
| `src/f2_summarise/summariser.py` | Full RAG orchestrator: chunk→retrieve→prompt→Claude→parse→save |
| `src/f2_summarise/run.py` | CLI: `python -m src.f2_summarise.run --limit 5 --agency fed` |
| `tests/test_f2_summariser.py` | 21 unit tests — chunker, retriever, parser, validator |
| `docs/wireframes/summary-card-v1.md` | Summary card 2-minute scan layout + confidence UI + North Star metric |

---

## KM Concept: #151 RAG Overview

**RAG = Retrieval Augmented Generation**

The three steps:
```
Document (400K chars)
    ↓
CHUNK — split into 1,000-char overlapping pieces (400 chunks)
    ↓
RETRIEVE — score each chunk for compliance relevance, keep top 6
    ↓
GENERATE — pass 6 chunks (~6,000 chars) to Claude → structured JSON
```

**Why RAG instead of "just send the whole document"?**

A 400K character document = ~100K tokens. At claude-sonnet-4 pricing, one summary call would cost ~$1.50 and take 60+ seconds. With RAG selecting 6 relevant chunks (~6K chars = ~1.5K tokens), it costs ~$0.015 and takes under 10 seconds.

More importantly: quality is better. Flooding Claude with 400 pages of legal boilerplate buries the compliance deadline in noise. RAG retrieves the sections that contain the compliance deadline, effective date, and institution scope — the three things Sarah needs most.

**Day 8 is "Naive RAG" — simplest possible version:**
- Chunking: fixed-size (1,000 chars) with 150-char overlap
- Retrieval: keyword frequency scoring (no embeddings)
- Day 9: test 5 chunking strategies and benchmark
- Day 15: replace keyword retrieval with dense embeddings

---

## Why Each Decision Was Made

### Why chunk size = 1,000 characters?

Regulatory text has dense, information-rich sentences. Too small (200 chars) and you split sentences. Too large (5,000 chars) and you have too few chunks to be selective — you might as well pass the whole document. 1,000 chars is roughly 2–3 paragraphs, which gives enough context for each chunk to be meaningful on its own.

### Why overlap = 150 characters?

Dates and deadlines often span sentence boundaries. "The rule takes effect... on January 1, 2027" — if "January 1, 2027" is at the start of a new chunk, we need the preceding sentence for context. 150 chars of overlap (about one sentence) ensures important facts at chunk boundaries appear in at least one complete chunk.

### Why keyword scoring instead of embeddings for retrieval?

Embeddings require either a local model or an API call per chunk. For 400 chunks, that's 400 API calls just to retrieve — cost and latency before Claude even runs. Keyword scoring is free and runs in microseconds. Day 15 benchmarks whether embeddings improve quality enough to justify the cost. Until then, keywords are the baseline.

### Why temperature = 0.2?

Temperature controls how "creative" Claude is. At 1.0, the model explores diverse responses. At 0.0, it always produces the same output for the same input. At 0.2, the output is almost deterministic — critical for JSON structure — but the summary text still reads naturally rather than robotically. Roadmap explicitly specifies 0.2 for structured output.

### Why explicit "return null" in the prompt?

From the FP/FN risk matrix: an invented compliance deadline is worse than no deadline. If Claude guesses "December 31, 2026" and Sarah builds a compliance plan around it, she's done wasted work — and when she discovers the hallucination, she loses trust in all AI outputs. The prompt says: "If not explicitly stated, return null. NEVER infer, estimate, or guess a date." The golden set tests this on entries 1 and 3.

### Why a separate `prompts.py` file?

The system prompt and schema are the most frequently changed artifact in F2. As we discover failure modes on Days 9–21, we'll iterate the prompt constantly. Keeping it in its own file means prompt changes don't touch the orchestration logic, and the change history in git shows exactly what prompt changes affected quality.

---

## AI/ML Concept Applied

**Naive RAG vs Full RAG:**

| Component | Day 8 (Naive) | Day 15+ (Full) |
|-----------|--------------|----------------|
| Chunking | Fixed-size | Hierarchical (structure-aware) |
| Retrieval | Keyword scoring | Dense embeddings + BM25 hybrid |
| Reranking | None | Cross-encoder reranker |
| Generation | Claude Sonnet | Claude Sonnet (same) |
| Eval | Manual spot-check | RAGAS faithfulness ≥ 0.75 |

Naive RAG gives us a working baseline today. Full RAG is built in Days 9–17, evaluated in Days 18–21.

**Failure modes to watch:**

1. **Hallucinated dates** — Claude invents an effective date not in the document. Caught by: comparing output to golden set entries 1 and 3.
2. **Wrong institution scope** — Claude says "all banks" when the rule only applies to institutions with > $10B assets. Caught by: RAGAS answer_relevance.
3. **Low confidence but wrong summary** — model is uncertain AND wrong. Worst case. Caught by: human review queue + LLM-as-judge (Day 20).
4. **Retrieval failure** — relevant chunks not selected, key information missing. Caught by: comparing source_citations to known document structure.

---

## How to Run

### Prerequisites
```bash
# Add your Anthropic API key to .env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Run summarisation
```bash
# Summarise 3 Fed documents (fast, good for testing)
python -m src.f2_summarise.run --limit 3 --agency fed

# Summarise up to 20 new documents
python -m src.f2_summarise.run --limit 20

# Show existing summaries
python -m src.f2_summarise.run --show --limit 5

# Summarise one specific document
python -m src.f2_summarise.run --doc-id <uuid-from-db>
```

### Run tests (no API key needed)
```bash
python -m pytest tests/test_f2_summariser.py -v
# 21 tests, ~5 seconds
```

---

## What the Output Looks Like

```json
{
  "headline": "Federal Reserve issues consent prohibition orders against two former bank employees for CARES Act fraud",
  "plain_english_summary": "The Fed permanently barred two former bank employees from working in banking. Crystal Moore (Atlantic Union Bank) committed CARES Act loan fraud; Jesse Romo (Frost Bank) committed embezzlement. Both actions are effective immediately.",
  "what_changed": "Two individuals are now permanently prohibited from participating in any federally insured financial institution.",
  "why_it_matters": "Signals continued Fed enforcement of CARES Act loan program integrity. Banks should review employee conduct monitoring programs and BSA/AML procedures.",
  "effective_date": "2026-05-28",
  "compliance_deadline": null,
  "affected_institution_types": ["all Fed-supervised banks", "FDIC-insured institutions"],
  "confidence_score": 92,
  "source_citations": ["Chunk 1 (effective date, names)", "Chunk 2 (prohibition details)"]
}
```

---

## Summary Card Wireframe

See `docs/wireframes/summary-card-v1.md` for the full ASCII layout.

Key design decisions:
- Confidence shown as plain English ("HIGH CONFIDENCE 91") not "0.91"
- Review queue banner appears for confidence < 80
- 4 action buttons: Review Original, Edit Summary, Create Task, Mark Reviewed
- North Star metric: time-to-understand per new rule (target ≤ 2 minutes)

---

## Current Test Count

| Suite | Tests | Time |
|-------|-------|------|
| F1: classifier | 14 | <1s |
| F1: dedup | 4 | <1s |
| F1: anomaly | 10 | <1s |
| F1: fulltext | 16 | <1s |
| F2: summariser | 21 | ~5s |
| **Total** | **65** | **~8s** |
| F1: integration (slow) | 7 | ~10s |

---

## PM Insight

**RAG is the product's intelligence engine.**

Sarah doesn't care that we use RAG. She cares that the summary is accurate and took 2 minutes to read. But RAG is what makes the accuracy possible.

The alternative — "just send the whole document to Claude" — fails in three ways:
1. Too expensive ($1.50/summary × 111 docs = $167 just for the backlog)
2. Too slow (60+ seconds per summary)
3. Lower quality (noise drowns signal in long documents)

RAG makes it $0.015, 10 seconds, and higher quality. That's why every serious LLM application uses RAG on long documents.

The chunking and retrieval decisions we make on Day 9 will determine F2's quality ceiling. The prompt engineering on Day 11 will determine how well we reach that ceiling. Day 8 gives us a working baseline to measure both against.

---

## Known Limitations

- Live run pending API key in `.env`
- Naive keyword retrieval will miss semantically relevant chunks that don't use exact keywords (e.g. "implementation timeline" for "compliance deadline")
- Fixed-size chunking will split tables and structured lists across chunks — fixed on Day 10 with hierarchical chunking
- No LangSmith tracing yet (Day 15) — AuditLog captures model and confidence but not the full trace
