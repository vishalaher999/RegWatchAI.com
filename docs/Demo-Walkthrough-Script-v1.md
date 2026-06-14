# Demo Walkthrough Script v1 (Day 40)

A ~5-minute script for a recorded walkthrough (e.g. Loom) of RegWatch AI,
F1 → F5. Record over this outline — each section names what to show and what
to say. Times are approximate targets, not hard cuts.

---

## 0:00–0:30 — Intro

**Show:** Title slide or `docs/ARCHITECTURE.md` overview section.

**Say:** "RegWatch AI is a compliance intelligence platform for community
banks. It watches federal regulators, summarizes what changed, maps the
impact onto a bank's own policies, generates tasks for compliance staff, and
keeps an audit trail of every AI decision. I'll walk through the five
features end to end."

---

## 0:30–1:30 — F1: Feed monitoring

**Show:** `dashboard/app.py` (Streamlit) — the documents list/table, filter
by agency (Fed/CFPB/OCC/FDIC/FinCEN), and an anomaly-flagged document.

**Say:** "F1 ingests regulatory feeds from five agencies, deduplicates them,
classifies the document type, and flags statistical anomalies — for example
a sudden burst of enforcement actions — using an isolation forest model."

**Also show (optional, via `/docs` Swagger UI from Day 40's API):**
`GET /f1/documents?agency=cfpb` and `GET /f1/documents/{id}` for a single
document's full record including its summary.

---

## 1:30–2:30 — F2: Summarization + review queue

**Show:** A document's structured summary (effective date, compliance
deadline, confidence score, source citations) and the review queue
(`GET /f2/review-queue` or the dashboard's flagged view).

**Say:** "Each document gets a structured summary with a confidence score
and citations back to the source chunks. A router sends low-confidence or
guardrail-failing summaries to a human review queue — for example, Day 38
added a guardrail that forces review if a summary states an effective date
without citing the chunk that supports it."

**Also show:** `GET /f5/audit-log?action=summarise&limit=3` — point out
`guardrail_warnings` in the payload for a flagged document.

---

## 2:30–3:30 — F3: Policy impact mapping

**Show:** `GET /f3/policy-sections` (72 sections from the 3 policy
fixtures — BSA, AML, TRID) and `GET /f3/impact-results?impact_level=high`
(23 sections with at least one high-impact regulatory match).

**Say:** "F3 is the core feature — it embeds a bank's policy sections and
incoming regulation chunks into separate Pinecone indexes, does a hybrid
dense+BM25 search to match them, then classifies the impact as High,
Medium, Low, or Not Applicable. Day 39 added PII redaction on policy text
before it's embedded or stored — account numbers, SSNs, routing numbers,
etc. get replaced with redaction tags, and every redaction is logged to the
audit trail."

---

## 3:30–4:15 — F4: Task generation (HITL)

**Show:** `GET /f4/tasks` and `GET /f4/tasks?status=open` — a generated
task with its source policy section, source regulation, and impact level.

**Say:** "For high and medium-impact findings, a LangGraph agent drafts a
compliance task — what to review, who should own it, and a due date. A
human reviews and can edit before it's marked complete; Day 38's weekly
report tracks how often humans actually change the AI's draft, which is the
override rate."

---

## 4:15–5:00 — F5: Audit trail, compliance report, and the new API

**Show:** `GET /f5/audit-log` (recent rows across all actions —
ingest, summarise, map, task_create, override, pii_redact) and
`GET /f5/compliance-report` (the same numbers as
`docs/Compliance-Report-Template-v1.md`'s weekly report, now available as
JSON).

**Say:** "Every AI decision — ingestion, summarization, impact mapping, task
creation, and now PII redaction — is logged with the model version, prompt
version, and inputs, per SR 11-7 model risk management guidance. Day 40 put
all of this behind a read-only FastAPI layer, so a compliance officer's
dashboard or a bank's own systems can pull this data via a simple HTTP API
instead of querying the database directly. The whole thing is packaged in a
Dockerfile for deployment to Render or Railway."

**Close:** "That's F1 through F5 — ingest, summarize, map impact, generate
tasks, and audit everything, all evaluated against labeled accuracy targets
and now exposed through an API."

---

## Notes for recording

- The Swagger UI at `/docs` (after `uvicorn api.main:app --reload`) is the
  easiest way to demo the API live — each endpoint can be expanded and
  executed with one click, showing real JSON responses.
- If recording before a Docker/Render deploy, run everything against
  `http://127.0.0.1:8000` — the script doesn't depend on a public URL.
