# SD1 — RegWatch AI System Design

**Day 44 deliverable (KM #239/#258).** A portfolio-oriented system design doc:
all five features, the data flow connecting them, the key design decisions,
and how the system is evaluated and governed. For a file-by-file build log,
see `docs/ARCHITECTURE.md`; for the narrative, see `docs/Case-Study-v1.md`.

---

## 1. Problem and Scope

Community banks must continuously monitor federal regulatory agencies (Fed,
CFPB, OCC, FDIC, FinCEN), understand what changed, map changes to internal
policies, and turn that into tracked remediation work — all auditable for
examiners. RegWatch AI automates this as a five-stage pipeline:

```
Ingest → Summarise → Map Impact → Generate Tasks → Audit Trail
  F1        F2            F3            F4              F5
```

Scope constraints (see CLAUDE.md): public regulatory data only, no secrets in
the repo, every AI decision logs model version + prompt version + inputs
(SR 11-7), and a human approves every task before it's created.

---

## 2. End-to-End Data Flow

```
Agency RSS Feeds / Federal Register API
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ F1 — Ingest  (src/f1_ingest/)                                 │
│  fetch → classify_doc_type → compute_hash → is_duplicate     │
│  → RegulatoryDocument(status=NEW)                             │
│  → AuditLog(INGEST)                                           │
│  Isolation Forest flags anomalous documents for review        │
└─────────────────────────────────────────────────────────────┘
        │ RegulatoryDocument(status=NEW)
        ▼
┌─────────────────────────────────────────────────────────────┐
│ F2 — Summarise  (src/f2_summarise/)                           │
│  chunk → embed/retrieve top chunks → NER cross-validation     │
│  → Claude (claude-sonnet-4-20250514, fallback: haiku-4-5)     │
│  → structured summary JSON (headline, what changed, why it    │
│    matters, effective_date, compliance_deadline, confidence)  │
│  → guardrails + multi-signal router (approve/review/escalate/ │
│    dismiss) → RegulatoryDocument(status=SUMMARISED)           │
│  → AuditLog(SUMMARISE) incl. model, prompt_version, tokens     │
└─────────────────────────────────────────────────────────────┘
        │ RegulatoryDocument(status=SUMMARISED) + policy library (PDF/DOCX)
        ▼
┌─────────────────────────────────────────────────────────────┐
│ F3 — Map Impact  (src/f3_impact/)                             │
│  PII redaction → extract policy sections → dual-index         │
│  Pinecone (policy namespace + regulation namespace)            │
│  → hybrid search (dense + BM25) → cross-encoder rerank        │
│  → threshold-based classifier → impact_level                  │
│    (high / medium / low / not_applicable)                     │
│  → AuditLog(MAP)                                               │
└─────────────────────────────────────────────────────────────┘
        │ HIGH/MEDIUM findings (policy section ↔ regulation chunk)
        ▼
┌─────────────────────────────────────────────────────────────┐
│ F4 — Generate Tasks  (src/f4_tasks/)                          │
│  LangGraph agent drafts a Task from each finding               │
│  → human-in-the-loop interrupt (build_graph / run_with_        │
│    approval / resolve_approval)                                │
│  Approved  → Task(status=open) + AuditLog(TASK_CREATE)         │
│            + notification queued to logs/notifications.jsonl   │
│  Rejected  → no Task row, AuditLog(OVERRIDE) records rejection │
│  Manual edits (owner/due_date/linked_regulations) also write   │
│  AuditLog(OVERRIDE)                                             │
└─────────────────────────────────────────────────────────────┘
        │ Task rows + AuditLog (INGEST/SUMMARISE/MAP/TASK_CREATE/OVERRIDE)
        ▼
┌─────────────────────────────────────────────────────────────┐
│ F5 — Audit Trail  (src/f5_audit/, scripts/)                   │
│  weekly_compliance_report.py  → documents ingested, routing    │
│    breakdown, guardrail warnings, HIGH findings, tasks created │
│  override_rate_report.py      → % of tasks human-edited        │
│  cost_dashboard.py (Day 44)   → $/query from F2 token usage    │
│  export_tasks.py / check_overdue_tasks.py                       │
└─────────────────────────────────────────────────────────────┘
```

All five features read from and write to one `AuditLog` table — it is the
spine that lets F5 reconstruct "what happened and why" for any document or
task without touching F1–F4's code.

---

## 3. Data Model (src/models.py)

| Table | Written by | Key fields |
|---|---|---|
| `Agency` | seed script | name, slug, feed URL |
| `RegulatoryDocument` | F1 (create), F2 (update) | `content_hash` (SHA-256(title+url), dedup key), `status`, `summary_json`, `review_flag`, `is_anomaly` |
| `Task` | F4 | `source_policy_name`, `source_section_id`, `source_regulation_doc_id`/`title`, `source_impact_level`, `linked_regulations_json`, `status`, `due_date`, `owner` |
| `AuditLog` | all 5 features | `action` (INGEST/SUMMARISE/MAP/TASK_CREATE/OVERRIDE), `actor`, `doc_id`/`task_id`, `langsmith_trace_id`, `payload_json` |

`Task` stores `source_regulation_doc_id`/`title` directly rather than only a
foreign key into F3's regenerable `impact_results.json` — a task stays
traceable back to the F3 finding that produced it even after F3's matches are
recomputed.

---

## 4. Key Design Decisions

1. **SHA-256(title+url) for dedup (F1).** Cheap, deterministic, enforced as a
   DB unique constraint — so even a bug in the Python-level check can't insert
   a duplicate.
2. **Dual-index Pinecone, hybrid search (F3).** Policy sections and regulation
   sections live in separate namespaces so a tenant's policy library never
   shares an index with regulation content. Dense (embedding) + BM25
   (keyword) search, then cross-encoder rerank, balances semantic matching
   (paraphrased policy language) with exact term matching (defined terms like
   "Regulation B").
3. **Threshold-based impact classifier, not an LLM call (F3).** Explainable —
   a compliance officer can be told *why* a section was flagged HIGH
   (dense_score ≥ 0.55, ± named-entity adjustment), which matters when this
   feeds an audit trail an examiner might read. Also avoids an LLM call (and
   its cost/latency/non-determinism) per policy-section/regulation-chunk pair.
4. **LangGraph with a hard HITL interrupt (F4).** The agent drafts; it never
   writes a `Task` row without `resolve_approval(approved=True)`. This is the
   current point on `docs/Progressive-Autonomy-Roadmap-v1.md` — autonomy
   increases only as audit-trail data (override rate, guardrail-warning rate)
   demonstrates the system is trustworthy.
5. **One `AuditLog` table for everything.** Every feature writes to the same
   table with the same shape (`action`, `actor`, `doc_id`/`task_id`,
   `payload_json`). F5's reports are pure aggregations over this one table —
   no feature-specific reporting tables were needed.
6. **Outbox, not send, for notifications (F4/Day 42).** `write_to_outbox()`
   appends to `logs/notifications.jsonl`. Per the standing project
   constraint, RegWatch AI does not send email on the user's behalf — the
   outbox is the documented integration seam for a future transactional-email
   provider.
7. **Token usage logged per F2 call (Day 44).** `_call_claude` returns
   `response.usage`, stored on the `AuditLog(SUMMARISE)` payload as
   `input_tokens`/`output_tokens`. `scripts/cost_dashboard.py` turns this into
   $/query using a hardcoded per-model pricing table — no live pricing API
   call, no new dependency.

---

## 5. Evaluation and Governance

| Feature | Eval | Target | Status (Day 44) |
|---|---|---|---|
| F1 | Doc-type classification, 100-doc held-out set | ≥90% | Date-extraction accuracy 90% (Day 18) |
| F2 | RAGAS faithfulness, golden set (`fixtures/golden/summaries.json`, 50 entries) | ≥0.85 (Day 45) | **0.783** — clears the Week 3 interim target (≥0.75) but below the Day 45 target (`evals/final_eval_report.json`) |
| F3 | Impact classification, `fixtures/golden/impact_pairs.json` (30 pairs) | ≥80% | Met (`evals/f3_eval.py`) |
| F3 | Section match precision@5 | ≥0.75 | Tracked in F3 eval |
| F4 | Override rate (% of drafted tasks human-edited) | leading indicator, not a gate | `scripts/override_rate_report.py` |
| All | Audit trail completeness | every AI decision logged | `AuditLog` — enforced by schema, not optional |

**Governance hooks (SR 11-7):**
- Model + prompt version on every `AuditLog(SUMMARISE)` row.
- LangSmith tracing (`langsmith_trace_id`) on F2 calls (Day 37).
- `docs/Model-Card-v1.md` — SR 11-7 pillar mapping + EU AI Act self-assessment
  for every AI/ML component (F1 IsolationForest, F2 Claude + embeddings +
  reranker, F3 classifier, F4 agent).
- `docs/Incident-Response-Plan-v1.md` and `docs/RCA-Hallucinated-Deadline-v1.md`
  — what happens when an eval gate fails or a bad output reaches a user.

---

## 6. Honest Gaps (as of Day 44)

- **F2 faithfulness below the final target** (0.783 vs. 0.85) — the single
  open eval gap, called out in `docs/Case-Study-v1.md` and
  `evals/final_eval_report.json`. Targeted for Day 45.
- **Golden set is 50 entries, not the 100 named in the v2.2 roadmap (KM
  #258)** — expanding requires hand-labeling 50 more documents, not done this
  session.
- **Cost dashboard only covers F2** — F3's reranker and F4's LangGraph agent
  don't currently log token usage; `scripts/cost_dashboard.py` reports $0 for
  those stages.
- **No dedup on overdue-task notifications** (Day 42, still open).
- **No migration tool** — schema changes to existing tables need a manual
  `ALTER TABLE` (see `src/models.py` Day 34 note).

---

## 7. Deployment

`api/main.py` (FastAPI, read-only) + Docker + Render/Railway blueprint —
see `docs/Deployment-Guide-v1.md`. SQLite in dev; `DATABASE_URL` env var
swaps to Postgres with no code change (`src/database.py`).
