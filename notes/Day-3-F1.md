# Day 3 — F1 Anomaly Detection & Feed Inspection

**Date:** 2026-06-01  
**Feature:** F1 — Regulatory Feed Monitoring  
**Status:** Complete — F1 pipeline fully operational with anomaly detection

---

## What Was Built

| File | Purpose |
|------|---------|
| `src/f1_ingest/anomaly.py` | Z-score volume detector + off-schedule day-of-week flag |
| `src/f1_ingest/query.py` | CLI inspection tool — summary, recent docs, anomaly view |
| `tests/test_f1_anomaly.py` | 10 unit tests for statistical helpers and threshold logic |
| `src/f1_ingest/ingest.py` | Updated — anomaly check wired in post-save; summary shows anomaly counts |

---

## Why Each Decision Was Made

### Why Z-score for anomaly detection?

A Z-score measures how many standard deviations a value is from the mean of a distribution. For daily publication counts:

```
Z = (today_count - historical_mean) / historical_std_dev
```

We flag as anomalous if Z > 2.0, which corresponds to the top ~2.5% of all historical days. This adapts automatically to each agency's normal rhythm — FinCEN's baseline is different from the Fed's, and the same count can be anomalous for one and normal for the other.

**The alternative** — a fixed threshold like "more than 5 documents = anomaly" — would constantly false-alarm on the Federal Register and never catch a FinCEN spike. The Z-score solves this without any configuration per agency.

### Why sample standard deviation (n-1), not population std (n)?

Our 30-day rolling window is a *sample* of all possible days, not the complete history. Sample std (dividing by n-1) gives a less biased estimate of the true variability. This is Bessel's correction — a standard statistical practice. It matters most when the window is small (first few days of operation). Our test failed the first time because it expected population std; we corrected it to match the sample std implementation.

### Why off-schedule detection uses 90 days?

Day-of-week patterns need more data than volume patterns. A 30-day window might not include enough examples of each weekday. 90 days gives ~13 occurrences per weekday, which is enough to establish a reliable baseline.

### Why does the query tool output show 104 "other" documents?

The keyword classifier on Day 2 covers the most common regulatory doc types. Federal Register documents use titles like "Formations of, Acquisitions by, and Mergers of Banks" — these are bank merger notices, which don't match any current keywords. They're genuinely "Other" — not rules, guidance, or enforcement. The F2 LLM summariser (Week 2) will reclassify these with full document context.

---

## AI/ML Concept Applied

**Statistical anomaly detection vs. ML anomaly detection:**

There are two broad approaches to detecting anomalies:

1. **Statistical** (what we built): Use a mathematical model of "normal" based on historical data. Z-score, IQR, moving averages. Explainable, fast, requires no training data, works with small samples.

2. **ML-based**: Train a model (autoencoder, isolation forest, LSTM) to learn normal patterns and flag deviations. More powerful for complex, multi-dimensional data. Requires training data, is a black box, overkill for our use case.

**Why we chose statistical:** In a compliance context, Sarah needs to explain to a regulator *why* a publication was flagged. "It published 3x its 30-day average" is a defensible answer. "The model assigned it an anomaly score of 0.87" is not. Explainability > accuracy in regulated industries.

---

## How to Run

```bash
# Full ingestion with anomaly detection
python -m src.f1_ingest.ingest

# Inspect the database
python -m src.f1_ingest.query                    # full summary + 10 recent
python -m src.f1_ingest.query --recent 20        # 20 most recent docs
python -m src.f1_ingest.query --agency fed       # Fed docs only
python -m src.f1_ingest.query --anomalies        # flagged docs only

# Run tests
python -m pytest tests/ -v
```

---

## F1 Feature — Complete Checklist

| Requirement | Status |
|-------------|--------|
| RSS feed ingestion (Fed) | ✅ Done |
| Federal Register API (CFPB, OCC, FDIC, FinCEN) | ✅ Done |
| Document type classification | ✅ Done |
| Deduplication (SHA-256 hash) | ✅ Done |
| Anomaly detection (volume spike) | ✅ Done |
| Off-schedule detection | ✅ Done |
| AuditLog on every ingest | ✅ Done |
| Offline fixture for development | ✅ Done |
| 28 passing tests | ✅ Done |
| Query/inspection CLI | ✅ Done |

---

## Known Limitations

- **Baseline needs history.** Anomaly detection requires at least 7 days of prior data. On Day 1, every agency shows "insufficient history for baseline" — that's correct behaviour, not a bug. After a week of daily runs, baselines become meaningful.
- **Classifier accuracy: 104/111 "other".** Federal Register merge/acquisition notices don't match current keywords. This is acceptable — F2 LLM classification will improve this in Week 2.
- **No scheduling.** The pipeline still runs manually. Daily automation via scheduled job is a Week 6 task.
- **20-doc cap per agency per run.** The FR API fetches 20 documents. In production this would paginate from the last-seen document timestamp. Sufficient for MVP.

---

## PM Insight

**Anomaly detection is the product's nervous system.**

Features F1–F5 turn RegWatch AI from a feed aggregator into an intelligence product. The difference between "here are today's regulatory publications" and "here are the three things you need to pay attention to today" is anomaly detection.

When Sarah opens RegWatch on a Monday morning and sees a ⚠ next to FinCEN showing 8 publications (when their average is 2), she knows something significant happened over the weekend — before she's read a single document. That's the value. The Z-score is invisible to her; the ⚠ is the product.

This is a general pattern in compliance AI: **the AI's job is to change where the human pays attention, not to replace the human's judgement.** Anomaly detection does exactly that.

---

## Current Database State

```
Total documents:  111
Fed:              20   (RSS feed — press releases, board actions)
CFPB:             20   (Federal Register — rules, notices)
OCC:              20   (Federal Register — rules, notices)
FDIC:             14   (overlap with Fed Register catch-all = 6 dupes)
FinCEN:           20   (Federal Register — BSA/AML actions)
Federal Register: 17   (joint-agency rules, 3 dupes from above)

Anomalies:         0   (expected — first-run batch, no historical baseline yet)
Review queue:      0   (F2 not yet built)
```
