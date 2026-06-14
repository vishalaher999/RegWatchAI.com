# Day 5 — F1 Full-Text Document Fetching

**Date:** 2026-06-01  
**Feature:** F1 — Regulatory Feed Monitoring  
**Status:** Complete — full-text enrichment pipeline working, title similarity dedup added

---

## What Was Built

| File | Purpose |
|------|---------|
| `src/f1_ingest/fulltext.py` | Full-text fetcher (FR API raw text + HTML extraction), title similarity dedup |
| `scripts/enrich_fulltext.py` | One-time backfill script for existing documents |
| `src/f1_ingest/ingest.py` | Updated — full-text enrichment wired in post-save |
| `tests/test_f1_fulltext.py` | 16 tests: HTML cleaning, text extraction, similarity scoring, near-dedup |

---

## Why Each Decision Was Made

### Why two fetching strategies?

Federal Register documents (CFPB, OCC, FDIC, FinCEN) have a dedicated `raw_text_url` from the FR API — plain text with zero HTML noise. Using it is faster and more reliable than HTML parsing. Federal Reserve documents are HTML pages without a clean API; BeautifulSoup extracts the body text after stripping navigation, scripts, and footers.

**Rule of thumb:** When a purpose-built API endpoint exists, use it. Screen-scraping is the last resort.

### Why target semantic HTML containers (`<main>`, `<article>`)?

Government websites vary in HTML structure. A layout built around `<div class="content">` might change to `<div id="main-content">` after a site redesign. Targeting semantic HTML elements that carry meaning (`<main>` = primary content) is more resilient than targeting class names that are arbitrary and change often.

### Why `SequenceMatcher` for title similarity instead of Levenshtein?

`difflib.SequenceMatcher` is built into Python's standard library — no dependency, no install. It computes the longest common subsequence ratio, which handles the real patterns we care about:
- "Final Rule on X" vs "Final Rule on X (Correction)" → high similarity (near-dupe)
- "Final Rule on Capital" vs "Guidance on Interest Rate Risk" → low similarity (different docs)

The accuracy difference between SequenceMatcher and Levenshtein is negligible for title-length strings.

### Why 1-second rate limiting between fetches?

Government websites are public infrastructure, not designed for high-frequency programmatic access. A compliance product that gets IP-blocked by a government site is an embarrassing failure. 1 second between requests is industry-standard courtesy for web scraping. It adds ~20 seconds to a 20-document enrichment run — acceptable.

### Why `limit=20` as the default per run?

Full-text fetching is the slowest step in the pipeline (1 HTTP request per document + 1s rate limit). Fetching all 111 documents would take ~2 minutes. Processing 20 per daily run means the backlog clears in ~6 runs (6 days) without blocking the fast ingest loop.

---

## AI/ML Concept Applied

**Data quality as model performance:**

The quality of F2's summaries is bounded by the quality of F1's content. If `raw_content` is a 1-sentence abstract, the best LLM in the world can't produce a meaningful "what changed" or "compliance deadline" — that information simply isn't in the input.

This is a general principle in ML: **garbage in, garbage out**. In regulated industries, it's even more stark because the compliance officer will check the AI's output against the source document. If the summary says "effective date: unknown" because the abstract didn't mention it, but the full document clearly states a deadline, the product has failed even if the summarisation model is technically excellent.

Full-text fetching is data quality work. It's unglamorous but it's what makes F2's eval numbers meaningful.

---

## How to Run

```bash
# Enrich 5 documents (test/demo)
python scripts/enrich_fulltext.py --limit 5

# Enrich 20 documents (default daily batch)
python scripts/enrich_fulltext.py

# Enrich all documents (full backfill — takes several minutes)
python scripts/enrich_fulltext.py --limit 0

# Full pipeline (ingest + enrich + anomaly check)
python -m src.f1_ingest.ingest

# Tests (44 fast unit tests)
python -m pytest tests/
```

---

## Current State

```
Total documents in DB:   111
Enriched (full text):      5  (first 5 Fed documents)
Remaining (abstract only): 106
```

Run `python scripts/enrich_fulltext.py --limit 0` to backfill all 106 remaining documents.
(Takes ~2 minutes due to rate limiting — run once then daily ingest handles new docs automatically.)

---

## F1 Complete — Full Spec Checklist

| Requirement | Status |
|-------------|--------|
| Ingest RSS feeds daily (Fed) | Done |
| Ingest via Federal Register API (CFPB, OCC, FDIC, FinCEN) | Done |
| Classify: Final Rule / Proposed Rule / Guidance / Enforcement / FAQ | Done |
| Deduplicate — content hash (SHA-256) | Done |
| Deduplicate — title similarity (SequenceMatcher, threshold 0.85) | Done |
| Anomaly detection — unusual volume (Z-score > 2.0) | Done |
| Anomaly detection — off-schedule publication | Done |
| Full-text document content (not just abstracts) | Done |
| AuditLog on every ingest action | Done |
| Feed health check + daily validation script | Done |
| 44 unit tests + 7 integration tests | Done |

---

## PM Insight

**The data pipeline is the product's memory.**

Everything F2–F5 will ever know about a regulation comes from what F1 captured. A summariser with only a 1-sentence abstract produces a 1-sentence summary. A policy mapper with no document text can't find relevant policy sections. A task generator without context produces generic tasks.

Today's work — fetching full document text — is invisible to the end user. Sarah won't see a "full text fetched" badge anywhere. But she'll notice that the summaries are specific rather than generic, that the effective dates are correctly extracted, that the impact mappings point to actual policy sections.

That's the lesson: the quality of the AI features visible to users is entirely determined by the quality of the data pipeline they can't see.
