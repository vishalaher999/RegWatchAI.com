# Day 1 — F1 Foundation: Project Structure, Schema, PRD

**Date:** 2026-06-01  
**Feature:** F1 — Regulatory Feed Monitoring (foundation)  
**Status:** Complete

---

## What Was Built

### Files Created

| File | Purpose |
|------|---------|
| `docs/PRD-v1.0.md` | Product Requirements Document — scope, users, metrics, data model |
| `docs/ARCHITECTURE.md` | Living architecture map — updated every day |
| `src/models.py` | All database tables: Agency, RegulatoryDocument, AuditLog |
| `src/database.py` | DB engine, session factory, table creation |
| `requirements.txt` | All dependencies with comments explaining why each exists |
| `.env.example` | Template for secrets (copy to .env and fill in) |
| `.gitignore` | Prevents secrets and build artifacts from reaching git |

### Directory Structure Created

```
regwatch-ai/
├── .env.example
├── .gitignore
├── requirements.txt
├── docs/
│   ├── PRD-v1.0.md
│   └── ARCHITECTURE.md
├── src/
│   ├── __init__.py
│   ├── database.py
│   ├── models.py
│   └── f1_ingest/
│       └── __init__.py
├── fixtures/
│   ├── agencies/
│   ├── policies/
│   └── golden/
├── evals/
├── api/
└── notes/
    └── Day-1-F1.md  ← this file
```

---

## Why Each Decision Was Made

### Why SQLModel?
SQLModel combines SQLAlchemy (the DB engine layer) with Pydantic (the validation layer) into one class. Without it, you'd write a SQLAlchemy model AND a Pydantic schema for every table — two files that can silently drift out of sync. SQLModel eliminates that class of bug.

### Why is `content_hash` the dedup key?
The same regulation often appears in multiple agency feeds simultaneously (e.g., a joint OCC/FDIC rule). SHA-256(title + url) creates a fingerprint that is unique to each document's identity, not its position in a feed. If we tried to deduplicate by title alone, minor wording differences would fool us. URL alone would miss cross-posted duplicates.

### Why store `summary_json` as a string rather than a real JSON column?
SQLite doesn't have a native JSON column type (unlike Postgres). Storing it as a `TEXT` field keeps us compatible with both SQLite (dev) and Postgres (prod). When we read it, we call `json.loads()`. This is a deliberate dev-vs-prod compatibility tradeoff.

### Why is `AuditLog` never updated?
Regulatory audit requirements (SR 11-7) require that AI decision records be immutable — you cannot retroactively change what the AI decided or who approved it. Every new event gets a new row. The only operation on this table is INSERT.

### Why `.env` for secrets?
API keys in source code is a top-10 OWASP vulnerability and would disqualify the product from any enterprise compliance review. `.env` is gitignored and loaded at runtime. In production, these move to a secrets manager (AWS Secrets Manager, etc.).

---

## AI/ML Concept Applied

**Schema as AI contract:** The `summary_json` field in `RegulatoryDocument` is intentionally untyped at the DB level (it's a TEXT column). This is deliberate — the F2 AI summariser will return a JSON structure, and that structure may evolve as we iterate on prompts. Keeping it as a JSON string means we don't have to run DB migrations every time we change the prompt output format. The Pydantic validation of the JSON happens in Python, not in the DB.

---

## How to Run (Day 1 — Schema Validation)

### 1. Set up environment

```bash
# Create and activate a virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install sqlmodel python-dotenv feedparser httpx pytest pytest-asyncio
```

### 3. Copy and configure .env

```bash
copy .env.example .env
# Open .env and add your API keys (not required yet — Day 1 has no LLM calls)
```

### 4. Verify the schema creates successfully

```python
# Run this in a Python shell from the project root:
from src.database import create_db_and_tables
create_db_and_tables()
# Expected: no errors, regwatch.db file appears in project root
```

### 5. Verify the tables exist

```python
from sqlmodel import create_engine, inspect
engine = create_engine("sqlite:///./regwatch.db")
inspector = inspect(engine)
print(inspector.get_table_names())
# Expected: ['agency', 'auditlog', 'regulatorydocument']
```

---

## What the Output Means

Running `create_db_and_tables()` creates a file called `regwatch.db` in the project root. This is the entire database — a single file. You can open it with any SQLite browser (e.g., DB Browser for SQLite) and see three empty tables: `agency`, `regulatorydocument`, `auditlog`.

The tables are empty because Day 1 only defines the schema. Day 2 will populate `agency` with the five agency feed URLs and begin fetching real documents.

---

## Known Limitations

- `summary_json` and `payload_json` are untyped TEXT fields. Type validation happens in Python, not the DB — a malformed JSON string would pass the DB constraint.
- No database migrations tool yet (Alembic). Adding columns in later days will require `SQLModel.metadata.drop_all()` + `create_all()` in dev (destroys data). We add Alembic in Week 6 before any real data matters.
- `content_hash = SHA-256(title + url)` — if an agency updates a document at the same URL with no title change, we would not detect the update. Acceptable for MVP; a `last_modified` check can be added later.

---

## PM Insight

**The schema is the product contract.**

Every feature we build for the next 44 days reads from or writes to `RegulatoryDocument`. The fields we defined today — `doc_type`, `status`, `review_flag`, `is_anomaly`, `summary_json` — are the fields that will appear in the UI, power the audit reports, and determine what the compliance officer sees.

Getting the schema right on Day 1 is disproportionately valuable. A wrong field name costs 5 minutes today. In Week 5, when F4 is querying these fields in a LangGraph agent, a schema refactor would cascade through every feature.

The PRD and schema together represent the product's data model theory. Everything else is implementation.
