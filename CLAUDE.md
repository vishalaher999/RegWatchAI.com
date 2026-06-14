# RegWatch AI

## What this is
Compliance intelligence platform for US community banks.
Monitors federal regulatory agencies, summarises rule changes, maps impact to internal policies, generates action tasks, maintains audit trail.

## Current status
Week 3 complete. F1 (feed monitoring) and F2 (summarisation + eval) are done.
Now starting F3 — Policy Impact Mapping (core feature).

## Stack
- Backend: Python / FastAPI
- LLM: claude-sonnet-4-20250514 (Anthropic API) — key in .env, never commit
- Mock fallback LLM: claude-haiku-4-5-20251001 for offline dev
- Vector DB: Pinecone (multi-tenant, one namespace per client)
- Eval: RAGAS + LLM-as-judge + CI gate
- Observability: LangSmith
- Agent framework: LangGraph (F4 task generation)
- Frontend: React
- Deploy target: Render or Railway (Docker)

## Project structure — focus here
- /backend/pipeline/ — ingestion, chunking, summarisation, impact mapping
- /backend/agents/ — LangGraph task generation agent (F4)
- /backend/api/ — FastAPI routes
- /frontend/src/ — React components
- /fixtures/agencies/ — mock RSS feed JSON fallbacks
- /fixtures/policies/ — 3 synthetic policy PDFs (BSA, AML, TRID)
- /fixtures/golden/ — labeled eval sets (summaries + impact pairs)
- /evals/ — RAGAS pipeline, CI gates, LLM judge

## 5-feature pipeline
F1 Ingest → F2 Summarise → F3 Map impact → F4 Generate tasks → F5 Audit trail

## Features built (Week 1–3)
- F1: RSS ingestor for Fed/CFPB/OCC/FDIC/FinCEN, dedup, doc type classifier, anomaly detection (Isolation Forest)
- F2: RAG pipeline, structured summary schema, confidence scoring, human review queue, RAGAS eval (target ≥0.85 faithfulness)

## Current feature (Week 4 — F3)
Policy impact mapping.
- Upload PDF/DOCX policy library → extract sections
- Embed policy sections + regulation sections separately (dual-index Pinecone)
- Hybrid search (dense + BM25) to match regulation chunks to policy sections
- Impact classifier: High / Medium / Low / Not Applicable
- F3 eval pipeline: CI gate at ≥80% accuracy on 30 labeled pairs
- Golden eval set: /fixtures/golden/impact_pairs.json (30 regulation-policy pairs, human-labeled)

## Eval targets
- F1 doc classification: ≥90% on 100-doc held-out set
- F2 RAGAS faithfulness: ≥0.85 on 50 golden examples
- F3 impact classification: ≥80% on 30 labeled pairs
- F3 section match precision@5: ≥0.75

## Key personas
- Sarah (compliance officer): reads summaries, reviews impact findings, approves high-risk tasks
- Mike (risk manager): monitors feed dashboard, exports weekly compliance reports

## Hard constraints
- Public regulatory data only — no Moody's internal or client data
- No secrets in repo (.env only)
- Every AI decision logs model version + prompt version + inputs
- SR 11-7 model risk management principles applied throughout

## Ignore when reading codebase
- node_modules/, dist/, __pycache__/, .env, *.lock, *.csv raw data files

## Current task
Building dual-index Pinecone setup for F3 policy section embeddings
