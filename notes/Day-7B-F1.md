# Day 7B — F1 Feed Dashboard (Streamlit)

**Date:** 2026-06-01  
**Feature:** F1 — Regulatory Feed Monitoring  
**Status:** Complete — Week 1 exit gate met

---

## What Was Built

| File | Purpose |
|------|---------|
| `dashboard/app.py` | Main Streamlit app — loads documents, applies filters, renders cards |
| `dashboard/components.py` | Reusable UI helpers — badges, metric row, document cards, sidebar filters |

---

## Week 1 Exit Gate — NOW MET

> **"Mike (risk manager) can see all 5 agency feeds filtered by doc type within 10 seconds of opening the dashboard."**

- All 6 agency feeds visible ✅
- Filter by agency (multiselect) ✅
- Filter by doc type ✅
- Anomalies flagged and surfaced first ✅
- Document cards expandable with content preview and source link ✅
- `@st.cache_data(ttl=300)` — 5-minute cache means filter changes are instant after first load ✅

---

## Why Each Decision Was Made

### Why Streamlit, not React?

React requires: npm, a build step, a separate dev server, webpack/Vite config, component libraries, and a FastAPI backend wired up with CORS. That's a week of work. Streamlit is pure Python — same language as everything we've built. A browser UI in one file, runs with one command. For a pilot demo with Mike, Streamlit is the right tool. We upgrade to React in Week 6 when the full API layer exists.

### Why `@st.cache_data`?

Streamlit reruns the entire script every time a user interacts with any widget (clicking a filter, expanding a card). Without caching, every interaction triggers a database query. `@st.cache_data(ttl=300)` stores the query result for 5 minutes. The first load hits the database; every subsequent filter change operates on the cached data — making the UI feel instant.

### Why convert SQLModel objects to dicts before caching?

SQLModel objects hold a reference to the database session they were created in. When Streamlit's cache tries to serialise them across reruns, the session reference is stale. Converting to plain Python dicts before caching avoids this entirely — dicts are always safe to serialise.

### Why show anomalies at the top in a separate section?

The product promise to Mike is: "tell me what to pay attention to today." Mixing anomalous documents into the general list defeats that purpose. Surfacing them in a prominent red banner at the top means Mike sees the high-priority items first, every time. This is a product decision, not just a UI one.

---

## How to Run

```bash
# From the project root
streamlit run dashboard/app.py

# Dashboard opens at http://localhost:8501
# Press Ctrl+C to stop
```

---

## What the Dashboard Shows

| UI Element | What It Does |
|-----------|--------------|
| Top KPI row | Total docs, Final Rules count, Proposed Rules count, Enforcement count, Anomalies |
| Sidebar — Agency filter | Show docs from selected agencies only (default: all) |
| Sidebar — Doc Type filter | Show selected doc types only (default: all) |
| Sidebar — Anomalies only | Toggle to show only anomaly-flagged documents |
| Sidebar — Sort | Newest first / Oldest first / By agency / By doc type |
| Red anomaly banner | Appears when anomalies exist — shows flagged docs first |
| Document cards | Expandable — shows type badge, agency, date, content preview, source link |
| F2 placeholder | Cards show "AI summary coming soon" where summary will appear in Week 2 |

---

## PM Insight

**The dashboard makes the data real.**

111 documents in a SQLite file is abstract. 111 document cards in a browser, filterable by agency, with enforcement actions highlighted in purple and anomalies surfaced in red — that's a product. This is the moment RegWatch AI stops being a pipeline and starts being something you'd show to Mike on a pilot call.

Notice what the dashboard also reveals: almost every card says "AI summary coming soon." That creates urgency for F2 in a way that a test result never could. When you look at a FinCEN special measure document (62,000 characters of AML regulation) and the card says "no summary yet," you feel how much F2 matters.

**Week 1 exit gate:** Met. Mike can see all 5 agency feeds filtered by doc type. F1 is done.

---

## Roadmap Comparison — Final Week 1 Status

| Requirement | Status |
|-------------|--------|
| Ingest from all 5 agencies daily | Done |
| Classify document types | Done |
| Dedup (content hash + title similarity) | Done |
| Anomaly detection | Done |
| Feed dashboard UI | Done (Streamlit) |
| Mike acceptance criteria | Done |
| Week 1 exit gate | **MET** |
