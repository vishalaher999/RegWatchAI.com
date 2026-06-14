# Portfolio Page — RegWatch AI

**Day 44 deliverable ("Portfolio page live").** Content for a single
portfolio page (e.g. on RegWatchAI.com or a personal site) summarizing the
project for recruiters, design partners, or anyone evaluating this build.
Markdown source — drop into whatever the site's page renderer expects.

---

## RegWatch AI

**Compliance intelligence for community banks — built solo, 44 days,
eval-gated end to end.**

RegWatch AI watches federal regulatory agencies (Fed, CFPB, OCC, FDIC,
FinCEN), turns new rules and guidance into plain-English summaries, maps
those changes to a bank's own policy library, drafts remediation tasks for a
compliance officer to approve, and keeps an audit trail of every AI decision
along the way.

**[Read the full case study →](Case-Study-v1.md)** · **[System design (SD1) →](SD1-System-Design-v1.md)**

---

### The Pipeline

| Stage | What it does |
|---|---|
| **F1 — Ingest** | Polls agency RSS/API feeds, dedupes via content hash, classifies doc type, flags anomalies (Isolation Forest) |
| **F2 — Summarise** | RAG + Claude (`claude-sonnet-4-20250514`) produces a structured summary — what changed, why it matters, effective date, compliance deadline — with confidence scoring and a human review queue |
| **F3 — Map Impact** | Dual-index Pinecone, hybrid search + reranking, matches regulation changes to specific sections of a bank's own policies, classifies impact High/Medium/Low/Not Applicable |
| **F4 — Generate Tasks** | LangGraph agent drafts compliance tasks from HIGH/MEDIUM findings — every task requires human approval before it's created |
| **F5 — Audit Trail** | Every AI decision (model + prompt version + inputs) is logged; weekly compliance reports, override-rate tracking, and a cost dashboard roll up from one audit log |

---

### What Makes This Different

- **Governance-first, not retrofitted.** The audit log, model/prompt
  versioning, and human-approval gate existed from Day 1 — not bolted on
  before a demo.
- **Eval gates, not vibes.** Every feature shipped against a numeric target
  on a hand-labeled golden set. Where a target isn't met (F2 faithfulness:
  0.783 vs. a 0.85 target), it's reported, not hidden — see the
  [final eval report](../evals/final_eval_report.json).
- **191+ tests, including one true end-to-end test** (`tests/test_e2e_pipeline.py`)
  that runs a synthetic document through all five features in a single
  in-memory database — the only mocked boundary is the Anthropic API call.
- **Staged autonomy.** The system drafts, classifies, and summarizes
  autonomously; a human approves every task and every send. The roadmap for
  *how* that boundary should move is itself a written artifact
  (`docs/Progressive-Autonomy-Roadmap-v1.md`).

---

### By the Numbers (Day 44)

- **5** features, **43 days** of build history, fully documented day-by-day
  (`docs/ARCHITECTURE.md`, `notes/Day-*.md`)
- **194** automated tests passing
- **90%** F2 date-extraction accuracy (up from ~32% on Day 8)
- **0.783** F2 RAGAS faithfulness (target 0.85 — open item)
- **≥80%** F3 impact-classification accuracy on a 30-pair labeled set
- Read-only **FastAPI** layer + **Docker** image, deployable to Render/Railway

---

### Try It

- API docs (when running): `/docs` (Swagger UI) via `uvicorn api.main:app --reload`
- Demo walkthrough script: `docs/Demo-Walkthrough-Script-v1.md`
- Deployment guide: `docs/Deployment-Guide-v1.md`

---

### Built With

Python · FastAPI · SQLModel/SQLite · Anthropic Claude (Sonnet 4 + Haiku 4.5)
· Pinecone · LangGraph · LangSmith · RAGAS · scikit-learn (Isolation Forest)
· cross-encoder reranking · React (frontend, planned)

---

*Full write-up: [Case-Study-v1.md](Case-Study-v1.md). Architecture and
day-by-day build log: [ARCHITECTURE.md](ARCHITECTURE.md) and `notes/`.*
