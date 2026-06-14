# Day 9 — F2 Chunking Benchmark: 5 Strategies Tested

**Date:** 2026-06-02
**Feature:** F2 — AI Summarisation
**KM:** #153 Chunking
**Status:** Complete — sentence chunking selected as winner, wired into pipeline

---

## What Was Built

| File | Purpose |
|------|---------|
| `src/f2_summarise/chunker.py` | Extended with 4 new strategies: sentence, paragraph, recursive, regulatory |
| `scripts/benchmark_chunking.py` | Benchmark runner — tests all 5 strategies on 20 real docs, scores on 4 metrics |
| `docs/wireframes/confidence-ui-v1.md` | Confidence UI design — score → label → colour → action |
| `src/f2_summarise/summariser.py` | Updated — now uses sentence chunking (DEFAULT_CHUNK_STRATEGY = "sentence") |

---

## Benchmark Results

Tested on 20 real regulatory documents (8K–400K chars).

| Strategy | Date | Inst | Coher | Effic | SCORE | AvgChunks | AvgSize |
|----------|------|------|-------|-------|-------|-----------|---------|
| **sentence** | **1.000** | 0.500 | **0.953** | 0.680 | **0.802** | 72.9 | 856 |
| recursive | 1.000 | 0.517 | 0.876 | 0.710 | 0.796 | 81.2 | 787 |
| regulatory | 1.000 | 0.517 | 0.876 | 0.710 | 0.796 | 81.2 | 787 |
| fixed_size | 1.000 | 0.483 | 0.110 | 0.725 | 0.638 | 75.3 | 977 |
| paragraph | 1.000 | 0.133 | 0.000 | 0.000 | 0.383 | 1.0 | 2000 |

**Winner: sentence chunking (0.802 composite score)**

---

## Why Each Strategy Won/Lost

### Sentence wins (0.802)
Date coverage perfect (1.000) — all 20 docs had retrievable dates. Coherence 95% — almost no mid-sentence cuts. The key advantage: every chunk starts at a sentence boundary, so dates like "The rule takes effect January 1, 2027" are never split across chunks.

### Recursive and regulatory tied (0.796)
Nearly identical to sentence. Slightly better institution coverage (3 more unique terms found) but lower coherence (more mid-sentence fragments from the fixed-size fallback paths). On our 20-doc sample, most documents don't have enough § section markers to give regulatory a meaningful advantage over recursive.

### Fixed-size crashes on coherence (0.638)
11% coherence = 89% of chunks start mid-sentence. The retriever selects chunks like "...tion Regulation B requires community banks to collect data on..." — grammatically correct but missing the setup sentence. Dates that span sentence boundaries ("...deadline. January 1, 2027 is the...") get cut and neither chunk contains the full date phrase.

### Paragraph catastrophic (0.383)
Federal Reserve press releases use single newlines (`\n`), not double newlines (`\n\n`). With no paragraph markers to split on, the entire document becomes one chunk (avg 2,000 chars). The retriever can't select — it gets the whole document or nothing. Institution coverage drops to 0.133 because the one giant chunk drowns relevant terms.

---

## KM Concept: #153 Chunking

**The three properties of a good chunk:**

1. **Coherent** — starts and ends at a natural boundary (sentence, paragraph, section). Not mid-word, not mid-date, not mid-sentence.

2. **Self-contained** — a reader could understand the chunk without having read the previous one. "The effective date is January 1, 2027" is self-contained. "...1, 2027 as stated above..." is not.

3. **Information-dense** — contains the kind of content the retriever is looking for (dates, institution types, compliance requirements). A chunk of 20 "whereas" clauses from the preamble scores low; a chunk from the "Effective Dates" section scores high.

**Why sentence chunking wins on regulatory text:**

Regulatory documents use formal, complete sentences. Every sentence is a complete legal statement. Sentence boundaries are the smallest natural unit of regulatory meaning — splitting within a sentence loses meaning, but splitting between sentences loses nothing.

**When sentence chunking would fail:**
- Documents with very long sentences (legal definitions that run 500+ words)
- Tables and structured data (sentence splitter treats table cells as "sentences")
- This is why Day 10 builds hierarchical chunking — it handles tables and definitions specially.

---

## Scoring Methodology

```
composite = (date_coverage × 0.35) + (institution_coverage × 0.25)
          + (coherence × 0.20) + (retrieval_efficiency × 0.20)
```

**Why date coverage weighted 35%?**
From the FP/FN risk matrix: a missed compliance deadline costs $500K–$5M. It's the single most critical field in the summary. Any chunking strategy that reliably surfaces dates scores higher, all else equal.

**Why institution coverage weighted 25%?**
Sarah's first question is always "does this apply to my bank?" If the retrieved chunks don't mention institution types, Claude defaults to "all institutions" — creating false urgency for rules that only affect large banks.

**Why coherence weighted 20%?**
Incoherent chunks (mid-sentence fragments) confuse Claude and produce lower-quality summaries. A chunk starting with "...tion rates shall not exceed..." forces Claude to infer context that should be explicit.

**Why retrieval efficiency weighted 20%?**
If the retriever picks up 80% of the document (poor selectivity), we might as well not use RAG — just pass the whole document. High efficiency = small % of document, high signal density.

---

## How to Run

```bash
# Run the full benchmark (20 docs, all 5 strategies)
python scripts/benchmark_chunking.py

# Run on fewer docs (faster)
python scripts/benchmark_chunking.py --docs 5

# Run a summary with the winning strategy
python -m src.f2_summarise.run --limit 3 --agency fed
```

---

## What Changed in the Pipeline

Before Day 9:
```
raw_content → chunk_fixed_size() → retrieve → Claude
Coherence: 11%
```

After Day 9:
```
raw_content → chunk_sentences() → retrieve → Claude
Coherence: 95%
```

Same retriever, same prompt, same model. Only the chunker changed.
Coherence improved from 11% to 95% — the retrieved chunks now make grammatical sense, which means Claude receives coherent context instead of sentence fragments.

---

## Current Test Count

| Suite | Tests |
|-------|-------|
| F1: classifier | 14 |
| F1: dedup | 4 |
| F1: anomaly | 10 |
| F1: fulltext | 16 |
| F2: summariser | 22 |
| **Total (fast)** | **66** |
| F1: integration (slow) | 7 |

---

## PM Insight

**Chunking is an invisible product decision.**

Sarah will never know that sentence chunking replaced fixed-size chunking. She'll just notice that the summaries are more accurate — effective dates are less likely to be null, institution types are more completely captured.

This is a pattern in AI product development: the decisions that most affect quality are often invisible to the user. The model gets all the credit; the chunking strategy gets none. But as a PM, you need to understand that the chunking decision — made in 20 lines of Python, taking 30 minutes to benchmark — had more impact on summary quality than any single prompt change could.

The benchmark also teaches a product lesson: **domain-specific beats general**. The sentence chunker wins not because it's the most sophisticated algorithm, but because it matches the structure of regulatory text. Regulatory writing uses complete, formal sentences. A chunker that respects sentence boundaries respects the domain.
