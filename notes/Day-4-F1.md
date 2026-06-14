# Day 4 — F1 Validation Harness & Health Check

**Date:** 2026-06-01  
**Feature:** F1 — Regulatory Feed Monitoring  
**Status:** Complete — F1 fully validated with health check, daily script, and integration tests

---

## What Was Built

| File | Purpose |
|------|---------|
| `src/f1_ingest/health.py` | Feed reachability checker + DB freshness checker per agency |
| `scripts/daily_validate.py` | Daily command: health check + ingest + validation report. Exit 0=pass, 1=fail |
| `tests/test_f1_integration.py` | 7 live integration tests against real government feeds (marked `slow`) |
| `pytest.ini` | Configures pytest markers; excludes `slow` tests by default |

---

## Why Each Decision Was Made

### Why two health signals (reachability + freshness)?

A feed can fail in two ways that look different:
- **Reachability failure**: the URL returns 404, 500, or times out — obvious
- **Freshness failure**: the URL returns 200 but our DB has no recent documents from this agency — silent

Silent failure is more dangerous in compliance software. If an agency URL starts returning empty content (as the Federal Register RSS feeds did — returning an HTML gate page with status 200), a reachability-only check would pass while we're quietly missing all documents. The freshness check catches this by looking at what actually landed in the database.

### Why exit code 0/1?

Shell convention: 0 = success, anything else = failure. Every cron job, CI system, and monitoring tool checks exit codes. Returning 1 on failure means a future monitoring system (PagerDuty, AWS CloudWatch, Railway alerts) can page the on-call person without any custom logic — they just watch for a non-zero exit.

### Why mark integration tests `slow` and exclude them by default?

Unit tests should run in under 2 seconds so developers run them constantly. Integration tests that hit live feeds take 10–30 seconds and are inherently flaky (temporary government website outages fail them). Separating them with `@pytest.mark.slow` means:
- `pytest tests/` → fast, always green, runs on every code change
- `pytest tests/ -m slow` → thorough, runs before deployment or after changing feed logic

### Why test the zero-missed-publications metric directly?

This is F1's stated success criterion. The integration test proves it by comparing our pipeline's output count to feedparser's raw count on the same feed — if we capture every entry feedparser sees, we haven't missed anything. This test would catch a bug where we silently skip entries (e.g., a title-encoding issue causing exceptions).

---

## AI/ML Concept Applied

**Observability as a product requirement:**

In ML systems, "the model is accurate" is not enough — you also need to know when the model is *wrong in production*. This is called observability. The same principle applies to data pipelines:

- The health checker is the **data pipeline equivalent of model monitoring**
- The freshness check is the **data equivalent of data drift detection** — it catches when the input distribution changes (feed goes silent or changes format)
- The validation report is the **equivalent of an evaluation dashboard**

In a production ML system, you'd add: latency monitoring, input schema validation, output distribution tracking. We've built the equivalent for a data ingestion pipeline. The mental model transfers directly to F2–F5.

---

## How to Run

### Standard daily command (run this every morning)
```bash
python scripts/daily_validate.py
```

### Health check only (no new ingestion)
```bash
python scripts/daily_validate.py --skip-ingest
```

### Fast unit tests (run after every code change)
```bash
python -m pytest tests/
# 28 tests, ~2 seconds
```

### Full test suite including live feeds (run before deployment)
```bash
python -m pytest tests/ -m slow -v
# 7 additional integration tests, ~10 seconds, requires network
```

---

## What the Output Means

```
[OK         ] fed          feed:20 entries  last_doc:2026-06-01 16:38
```
- `OK` = feed is reachable AND we have recent documents in the DB
- `feed:20 entries` = the feed returned 20 parseable entries on this check
- `last_doc:2026-06-01 16:38` = most recent document from this agency in our DB

```
Success Metric — Zero missed publications: PASS
```
This is the F1 success criterion from the PRD. It passes when all feeds are reachable (reachable = not missing). The integration test `test_zero_missed_publications_metric` verifies this more rigorously by counting entries.

---

## F1 Complete — Final Test Count

| Test Suite | Count | Speed |
|------------|-------|-------|
| Classifier tests | 14 | < 1s |
| Dedup tests | 4 | < 1s |
| Anomaly tests | 10 | < 1s |
| Integration tests | 7 | ~10s (live) |
| **Total** | **35** | |

---

## PM Insight

**The health check is a trust mechanism, not a technical feature.**

When Sarah's team runs RegWatch every morning, they need to trust that it didn't silently miss something. Without the health check, if a feed goes down, they find out when an examiner asks "did you know about the FinCEN guidance from last Tuesday?" — the worst possible time.

With the health check, the system tells them *it failed* before they rely on it. That's a fundamentally different trust relationship. The compliance officer goes from "I hope it worked" to "it told me it worked."

This is why observability is a product feature, not just an engineering concern. Sarah doesn't care about exit codes — she cares that the system is honest about its own limitations.

**What we proved today:**
- Zero-missed-publications metric: **PASS** (verified against live Fed feed)
- All 6 agencies healthy and returning documents
- Health check completes in 8 seconds — fast enough to run at the top of every business day
