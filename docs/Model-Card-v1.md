# RegWatch AI — Model Card v1 (Day 41, KM #271/#273)

**Date:** 2026-06-14
**Scope:** All AI/ML components in the F1-F5 pipeline.
**Disclaimer:** This is a self-assessment for product/engineering purposes,
written to the structure of SR 11-7 (Federal Reserve model risk management
guidance) and the EU AI Act's risk-tiering framework. It is **not legal
advice** — a real deployment would need sign-off from compliance/legal
counsel, particularly for the EU AI Act classification.

---

## 1. Model Inventory

| Component | Model(s) | Used for |
|---|---|---|
| F1 — Anomaly detection | `IsolationForest` (scikit-learn) | Flags statistically unusual ingestion patterns (e.g. enforcement-action bursts) |
| F2 — Summarisation | `claude-sonnet-4-20250514` (primary), `claude-haiku-4-5-20251001` (offline/mock fallback) | Structured summaries: effective dates, deadlines, affected parties, confidence score, citations |
| F2/F3 — Embeddings | `all-mpnet-base-v2` (sentence-transformers, 110M params) | Dense vector representations of regulation chunks and policy sections |
| F2 — Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Reranks retrieved chunks before they're passed to the summarisation LLM |
| F3 — Impact classification | `claude-sonnet-4-20250514` via hybrid (dense + BM25) retrieval | Classifies regulation-policy section pairs as High/Medium/Low/Not Applicable |
| F4 — Task generation | `claude-sonnet-4-20250514` (LangGraph agent) | Drafts compliance tasks (title, owner, due date) from high/medium-impact findings |

Every LLM call's model name and prompt version (`PROMPT_VERSION` in
`src/f2_summarise/prompts.py`, currently `v3`) are written to `AuditLog`
alongside the inputs — see §3.

---

## 2. Intended Use & Limitations

**Intended use:** Decision-support for compliance officers (Sarah persona)
and risk managers (Mike persona) at US community banks. The system surfaces,
summarises, and prioritizes regulatory changes and their policy impact; it
does **not** autonomously change a bank's policies or file anything with a
regulator.

**Human-in-the-loop by design:**
- F2 summaries below `CONFIDENCE_THRESHOLD` (80) or failing guardrail checks
  (Day 38) are routed to a human review queue — never auto-published.
- F4 tasks are drafts; a human approves/edits before `status` leaves
  `pending` (Day 37's HITL workflow). Override rate is tracked precisely so
  "how much do humans actually change the AI's output" is measurable, not
  assumed.

**Known limitations:**
- F2 RAGAS faithfulness target is ≥0.85 on a 50-example golden set — not
  100%. Summaries can still be wrong; citations exist so a human can verify
  in under a minute.
- F3 impact classification target is ≥80% on a 30-pair labeled set — a
  meaningfully smaller eval set than F2's, reflecting the smaller amount of
  labeled impact data available (see `fixtures/golden/impact_pairs.json`).
- PII redaction (Day 39, `src/f3_impact/pii.py`) is regex-based — no
  name/address NER. Flagged for human spot-check during pilot onboarding.
- Trained/tuned on **public regulatory data only** (Fed/CFPB/OCC/FDIC/FinCEN
  feeds + 3 synthetic policy fixtures). No model has been fine-tuned on any
  real client data.

**Out of scope (do not use for):**
- Final compliance determinations without human review.
- Non-US regulatory regimes (feed sources are US federal agencies only).
- Real-time/sub-second decisioning — the pipeline is batch/async by design.

---

## 3. SR 11-7 Mapping

SR 11-7 organizes model risk management into three pillars. Each is mapped
to a concrete artifact already built, not a future promise:

### 3.1 Model Development
- **Documented design choices:** `docs/ARCHITECTURE.md` records why each
  model/library was chosen (e.g. hybrid dense+BM25 over pure dense search
  for F3, `all-mpnet-base-v2` over OpenAI embeddings for cost/offline
  reasons — see `src/f2_summarise/embeddings.py` docstring).
- **Prompt versioning:** every summarisation/classification prompt has a
  `PROMPT_VERSION` constant, written to every `AuditLog(SUMMARISE)` row
  (`src/f2_summarise/prompts.py`).

### 3.2 Independent Validation
- **F1:** doc classification ≥90% on a 100-doc held-out set.
- **F2:** RAGAS faithfulness ≥0.85 on 50 golden examples; LLM-as-judge
  calibration (`evals/`).
- **F3:** impact classification ≥80% on 30 labeled pairs; section-match
  precision@5 ≥0.75 (`fixtures/golden/impact_pairs.json`).
- **CI gate:** eval thresholds are enforced in CI — a regression below
  target fails the build (see `evals/`).

### 3.3 Ongoing Monitoring
- **Audit trail (Day 36):** every AI decision — ingest, summarise, map,
  task_create, override, pii_redact — is an immutable `AuditLog` row with
  model version, prompt version, and inputs (`docs/Audit-Log-Viewer-UX-v1.md`).
- **Override rate dashboard (Day 37):** tracks the % of summaries/tasks a
  human edits before approval — a live drift signal independent of the
  static eval sets (`scripts/override_rate_report.py`).
- **Guardrails (Day 38):** citation-forcing checks run on every summary;
  any failure forces `needs_review=True` regardless of the router's
  decision, and is counted in the weekly compliance report
  (`scripts/weekly_compliance_report.py`).
- **LangSmith tracing (Day 37):** every LLM call has a `langsmith_trace_id`
  linking the audit row to the full prompt/response trace for incident
  investigation (`docs/RCA-Hallucinated-Deadline-v1.md` is a worked example).

---

## 4. EU AI Act — Self-Assessed Risk Classification

**Self-assessed tier: Limited Risk, with transparency obligations** —
*not* High-Risk, under the following reasoning:

- The EU AI Act's high-risk Annex III categories most relevant to financial
  services concern **creditworthiness/credit-scoring decisions about
  individuals**. RegWatch AI does not score individuals — it summarises
  regulatory text and maps it to a bank's *internal policy documents*. No
  natural person is the subject of an automated decision.
- All outputs that lead to an action (a task, a flagged review) require
  human approval — there is no automated decisioning loop that affects a
  person's access to a financial product.
- Transparency obligations that **do** apply: users (Sarah, Mike) must be
  informed they are interacting with an AI system, and that summaries and
  impact classifications are AI-generated and may be incorrect — this is
  why every summary card shows a confidence score and citations, and every
  F3 finding shows its impact level explicitly rather than silently.

**Caveat:** if a future feature used RegWatch's outputs to directly gate a
*customer-facing* decision (e.g., auto-approving/denying a loan based on a
policy-impact finding), that feature would need to be re-assessed — likely
pushing it toward High-Risk (Annex III, creditworthiness). No such feature
exists in F1-F5.

---

## 5. Change Log

| Date | Change |
|---|---|
| 2026-06-14 | v1 — initial model card, Day 41 |
