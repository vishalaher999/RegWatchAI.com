# RegWatch AI

**Regulatory Change Intelligence for Community Banks & Credit Unions**

RegWatch AI automatically monitors US federal regulatory publications, summarises them in plain English, maps them to your institution's internal policies, and generates actionable compliance tasks — compressing the compliance response cycle from weeks to hours.

> Built for the 5,000+ community banks and 4,700+ credit unions that cannot afford $50K–$200K enterprise compliance platforms.

---

## What It Does

| Feature | Status | Description |
|---------|--------|-------------|
| **F1 — Feed Monitoring** | Complete | Daily ingestion from Fed, CFPB, OCC, FDIC, FinCEN. Dedup, classify, anomaly detection. |
| **F2 — AI Summarisation** | Week 2 | Structured JSON summary of every regulation in <30 seconds using Claude. |
| **F3 — Policy Impact Mapping** | Week 4 | Maps regulations to your uploaded policy library. Flags gaps. |
| **F4 — Task Generation** | Week 5 | Auto-generates remediation tasks with HITL approval for high-impact findings. |
| **F5 — Audit Trail** | Week 6 | Immutable log of every AI action. SR 11-7 aligned. PDF/CSV export. |

---

## Quick Start

### Prerequisites

- Python 3.12+
- An Anthropic API key (required for F2+, not needed for F1)

### Setup

```bash
# 1. Clone / open the project
cd "RegWatch AI/RegWatchAI.com"

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Open .env and add your ANTHROPIC_API_KEY (required for F2+)

# 5. Create the database and seed agencies
python scripts/setup_db.py

# 6. Run first ingestion
python -m src.f1_ingest.ingest
```

### Daily Operation

```bash
# Run the full daily pipeline (health check + ingest + enrich)
python scripts/run_daily.py

# Or let Windows Task Scheduler run it automatically at 7 AM:
python scripts/schedule_daily.py
```

### Inspect What Was Ingested

```bash
python -m src.f1_ingest.query                  # full summary
python -m src.f1_ingest.query --recent 20      # 20 most recent documents
python -m src.f1_ingest.query --agency fed     # Federal Reserve only
python -m src.f1_ingest.query --anomalies      # flagged documents only
```

---

## Project Structure

```
RegWatchAI.com/
├── .env.example            # API key template — copy to .env
├── requirements.txt        # All Python dependencies
├── pytest.ini              # Test configuration
│
├── src/
│   ├── models.py           # Database schema (Agency, RegulatoryDocument, AuditLog)
│   ├── database.py         # DB engine + session management
│   └── f1_ingest/          # F1: Feed monitoring
│       ├── agencies.py     # Agency seed data (6 sources)
│       ├── classifier.py   # Doc type keyword classifier
│       ├── dedup.py        # SHA-256 content hash deduplication
│       ├── fetcher.py      # RSS + Federal Register API fetchers
│       ├── fulltext.py     # Full-text extraction + title similarity dedup
│       ├── anomaly.py      # Z-score volume + off-schedule detection
│       ├── ingest.py       # Orchestrator — runs full pipeline
│       ├── health.py       # Feed reachability + freshness checks
│       └── query.py        # CLI inspection tool
│
├── scripts/
│   ├── setup_db.py         # One-time: create tables + seed agencies
│   ├── run_daily.py        # Daily pipeline entry point (called by Task Scheduler)
│   ├── schedule_daily.py   # Register/remove Windows scheduled task
│   ├── enrich_fulltext.py  # Backfill full text for existing documents
│   ├── daily_validate.py   # Health check + validation report
│   └── db_status.py        # Database statistics
│
├── tests/
│   ├── test_f1_classifier.py   # 14 classifier tests
│   ├── test_f1_dedup.py        # 4 dedup tests
│   ├── test_f1_anomaly.py      # 10 anomaly/statistics tests
│   ├── test_f1_fulltext.py     # 16 extraction + similarity tests
│   └── test_f1_integration.py  # 7 live integration tests (--slow)
│
├── fixtures/
│   ├── agencies/
│   │   └── sample_feed.json    # Offline feed snapshot for dev
│   └── golden/
│       └── f1_golden_set.json  # 10 hand-labeled docs for F2 eval
│
├── docs/
│   ├── PRD-v1.0.md         # Product Requirements Document
│   └── ARCHITECTURE.md     # Living architecture map
│
├── notes/                  # Day-by-day build notes (Day-1 through Day-7)
└── logs/
    └── daily_run.log       # Appended by run_daily.py each morning
```

---

## Data Sources

| Agency | Source | Method |
|--------|--------|--------|
| Federal Reserve | federalreserve.gov/feeds/press_all.xml | RSS feed |
| CFPB | federalregister.gov API | JSON API |
| OCC | federalregister.gov API | JSON API |
| FDIC | federalregister.gov API | JSON API |
| FinCEN | federalregister.gov API | JSON API |
| Federal Register (joint rules) | federalregister.gov API | JSON API |

> **Note:** The Federal Register RSS feeds block automated requests. We use their public JSON API (no key required) which is reliable and well-documented.

---

## Running Tests

```bash
# Fast unit tests (~2 seconds) — run after every code change
python -m pytest tests/

# Include live integration tests (~30 seconds, requires network)
python -m pytest tests/ -m slow -v

# Run all tests including slow
python -m pytest tests/ -m ""
```

**Current test count:** 44 unit tests + 7 integration tests = 51 total

---

## Scheduled Automation (Windows)

```bash
# Register daily run at 7:00 AM
python scripts/schedule_daily.py

# Change the time
python scripts/schedule_daily.py --time 06:30

# Check status
python scripts/schedule_daily.py --status

# Remove
python scripts/schedule_daily.py --remove
```

The scheduled task runs `scripts/run_daily.py` and appends output to `logs/daily_run.log`.

---

## Database

RegWatch AI uses **SQLite** for development (zero configuration, single file: `regwatch.db`).

Production deployment (Week 6) switches to **PostgreSQL** by changing one environment variable:

```bash
# .env
DATABASE_URL=postgresql://user:password@host:5432/regwatch
```

No code changes required.

### Reset the database

```bash
del regwatch.db          # Windows
python scripts/setup_db.py
python -m src.f1_ingest.ingest
```

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | No (defaults to SQLite) | Database connection string |
| `ANTHROPIC_API_KEY` | F2+ | Claude API for summarisation |
| `LANGCHAIN_API_KEY` | F5 | LangSmith tracing |
| `LANGCHAIN_PROJECT` | F5 | LangSmith project name |

---

## F1 Database State (Week 1 Complete)

```
Documents ingested:   111
Agencies monitored:     6
Full text enriched:   111  (100%)
Total regulatory text: ~1.45 million characters
Anomalies detected:     0  (baseline still building — check after 7 days)
Tests passing:         44 unit + 7 integration
```

---

## Compliance Notes

- All AI outputs are logged immutably to `AuditLog` (SR 11-7 aligned — added fully in F5)
- RegWatch AI is **decision support, not legal advice**. The compliance officer retains professional responsibility for all regulatory determinations.
- API keys are stored in `.env` (gitignored). Never commit secrets to version control.

---

## Build Schedule

| Week | Days | Feature | Target |
|------|------|---------|--------|
| 1 | 1–7 | F1 Feed Monitoring | Complete |
| 2–3 | 8–21 | F2 AI Summarisation | RAGAS faithfulness ≥ 0.85 |
| 4–5 | 22–35 | F3 Policy Mapping + F4 Tasks | Precision@3 ≥ 0.75 |
| 6–7 | 36–45 | F5 Audit + Deploy + GTM | First pilot demo |

---

*Built by Vishal Aher | RegWatch AI | Confidential*
