# Day 43 — End-to-End Integration Test + Case Study (KM #227, Week 7 Day 1)

**Date:** 2026-06-13/14
**Roadmap:** Week 7 ("Integration + Portfolio"), Day 1 of 7

---

## What Was Built

| Artifact | Type | Status |
|---|---|---|
| `tests/test_e2e_pipeline.py` | NEW | Done — 1 test, passing |
| `docs/ARCHITECTURE.md` | EDIT | Day 43 entry added |
| `docs/Case-Study-v1.md` | NEW | Done — ~2,000-word portfolio case study |
| `notes/Day-43-Integration.md` | NEW | This file |

---

## Roadmap — Day 43 columns

| Column | Content |
|---|---|
| KM reference | #227 — FastAPI end-to-end ("RSS ingest → summary → impact → task → audit report") |
| Engineering | One in-memory-SQLite test exercising F1→F2→F3→F4→F5 in a single run, with only the Anthropic API call (F2's `_call_claude`) mocked |
| Product | Portfolio case study summarizing the Days 1–43 build for an external audience |
| Deliverable | Passing end-to-end test + case study draft |

---

## What Changed and Why

**`tests/test_e2e_pipeline.py`** is the first test that spans all five
features in one run. Every prior test suite (Days 1–42) validated one feature
against its own in-memory DB; nothing previously asserted that the *outputs*
of one feature are valid *inputs* to the next. This test:

1. Writes an `AuditLog(INGEST)` row the way a real F1 ingest run would
   (F1's live HTTP fetch itself stays out of scope — that's
   `tests/test_f1_integration.py`, `@pytest.mark.slow`).
2. Calls the real `summarise_document` (F2, Day 8) with `_get_client` mocked
   to return a canned Claude response — chunking, retrieval, NER, guardrails,
   confidence scoring, and the `AuditLog(SUMMARISE)` write all run for real.
3. Calls the real `classify_matches` / `log_map_decisions` (F3, Day 22) — the
   threshold-based HIGH/MEDIUM/LOW classifier runs unmocked against a section
   with `dense_score=0.9`, which clears `HIGH_THRESHOLD` regardless of the
   named-entity adjustment.
4. Drives the real F4 LangGraph (Days 31–35) — `build_graph` → 
   `run_with_approval` → `resolve_approval(approved=True)` — and confirms
   Day 42's `finalize()` queues a "new task assigned" notification to the
   outbox.
5. Calls `weekly_compliance_report.build_report` (F5, Day 36) and asserts
   `documents_ingested == 1`, `high_findings == 1`, `tasks_created == 1`, and
   that `guardrail_warnings` is present in the report shape.

**Two integration bugs found while writing the test** (both in the test
itself, not production code):

- The test scaffolding initially used a dynamic
  `__import__("sqlmodel").select(...)` pattern left over from an earlier
  draft — replaced with a normal `select` import.
- `RegulatoryDocument.content_hash` is `Field(unique=True, ...)` with no
  default — every *real* document gets one from
  `src.f1_ingest.dedup.compute_hash(title, url)` during ingest, but a
  hand-built test fixture doesn't unless it's set explicitly. Fixed by
  computing it the same way F1 does.
- The hardcoded `now=datetime(2026, 6, 21)` passed to `build_report` was
  outside the 7-day window relative to the *actual* system clock (the AuditLog
  rows get real `datetime.utcnow()` timestamps at test-run time, which can
  differ from the date the assistant believes "today" to be) — replaced with
  `datetime.utcnow()` so the window is always correct relative to when the
  test actually runs.

That **no production code changed** to make this test pass is itself a useful
result — it means the F1→F5 contracts established across Days 1–42 are
internally consistent.

**`docs/ARCHITECTURE.md`** gets one new entry for `tests/test_e2e_pipeline.py`,
following the same "what it does / why it exists / key limitation / run"
format as every other Day 36–42 entry.

**`docs/Case-Study-v1.md`** is a ~2,000-word narrative covering: the problem
RegWatch AI solves, the three design principles set on Day 1 (SR 11-7
throughout, eval gates not vibes, human-in-the-loop not full autonomy), a
walkthrough of F1–F5, the "Week 6 = making it legible" theme, today's
end-to-end test, and an honest results table — including the one metric that's
**below target** (F2 RAGAS faithfulness: 0.783 vs. 0.85 target, per
`docs/Product-Roadmap-3-6-12.md`), reported rather than hidden, consistent
with the project's eval-gate philosophy.

---

## Result

```
$ python -m pytest tests/test_e2e_pipeline.py -v
1 passed

$ python -m pytest tests/ -q
191 passed, 11 deselected, 80 warnings
```

(190 from Day 42 + 1 new end-to-end test. No regressions.)

---

## v1 Limitations

1. **Single scenario** — the e2e test covers one CFPB final rule mapped to
   one HIGH-impact policy section, approved on the first pass. It doesn't
   cover MEDIUM/LOW findings, rejected drafts, or multi-document runs.
2. **F1's live fetch stays mocked** — the `AuditLog(INGEST)` row is
   hand-written to match what a real ingest produces, rather than driving
   `src/f1_ingest/ingest.py` itself (that's the slower, network-dependent
   `test_f1_integration.py`).
3. **F2 faithfulness gap is not closed** — the case study reports 0.783 vs.
   the 0.85 target as an open item; Day 43 doesn't attempt to fix F2's
   retrieval/prompting to close it (that's a Day 45 target per the roadmap).

---

## PM Insight

Day 43's most useful finding wasn't a bug — it was the *absence* of one.
Five features built independently across 42 days, each with its own test
suite and its own in-memory DB, turned out to compose correctly on the first
end-to-end run; the only failures were in the test fixture's own setup
(a missing dedup hash, a stale import, a hardcoded date), not in how F1's
output shape met F2's input expectations, or F3's findings met F4's draft
schema, or F4's created task met F5's report aggregation. That's a strong
signal that the per-feature eval-gate discipline from Weeks 1–5 — get each
feature's contract right and tested in isolation before moving on — paid off
at integration time, which is exactly the bet that discipline was making.

---

**Next: Day 44 (Week 7 — Integration + Portfolio, continued)** — do not start
without explicit "next".
