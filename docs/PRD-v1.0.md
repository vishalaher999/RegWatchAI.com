# RegWatch AI — Product Requirements Document v1.0

**Status:** Active  
**Founder:** Vishal Aher  
**Version:** 1.0 | May 2026 | Confidential  
**Last updated:** 2026-06-01  

---

## 1. Executive Summary

RegWatch AI is an AI-powered regulatory change management platform purpose-built for community banks and credit unions in the United States. It automatically monitors regulatory agency publications, summarizes new requirements, maps them to the institution's internal policy library, and generates actionable compliance tasks — compressing the compliance response cycle from months to days.

| | |
|--|--|
| **Problem** | Compliance officers at community banks manually track 50–100+ regulatory updates per month across Fed, CFPB, OCC, FDIC, and FinCEN. One missed update can result in fines of $500K–$5M. |
| **Solution** | RegWatch AI automates the entire regulatory change workflow — monitoring, summarizing, impact mapping, task generation, and audit trail — in one platform. |
| **Market** | 5,000+ community banks and 4,700+ credit unions in the US. Enterprise vendors like Wolters Kluwer serve large institutions only. The community segment is massively underserved. |
| **Revenue** | $1,000–$3,000/month per institution. Target: 20 clients by Year 1 = $40K–$60K MRR. |

---

## 2. Problem Statement

### 2.1 The Compliance Officer's Daily Reality

A compliance officer at a community bank with $500M in assets wakes up every Monday morning and manually checks 6–8 regulatory agency websites. They download PDFs, read through dense legal language, and try to figure out which internal policies need updating. This process is:

- **Time-consuming** — 15–20 hours per week per officer on regulatory monitoring alone
- **Error-prone** — manual tracking via spreadsheets leads to missed updates
- **Stressful** — a single missed regulation can trigger an exam finding or enforcement action
- **Costly** — hiring additional compliance staff costs $80K–$120K per year per head

### 2.2 Regulatory Agencies Monitored

| Agency | Jurisdiction & Key Areas |
|--------|--------------------------|
| Federal Reserve (Fed) | Bank holding companies, monetary policy, consumer protection |
| CFPB | Consumer lending, mortgages, credit cards, deposit accounts |
| OCC | National banks, federal thrifts, trust companies |
| FDIC | Deposit insurance, community bank safety and soundness |
| FinCEN | Anti-money laundering, Bank Secrecy Act, beneficial ownership |
| State Regulators | State-chartered banks, state-specific consumer protection (Phase 2) |

### 2.3 The Gap in the Market

Enterprise compliance platforms like Wolters Kluwer, Regology, and Refinitiv serve large financial institutions with $10B+ in assets and charge $50K–$200K per year. Community banks and credit unions — with assets between $100M–$5B — cannot afford these solutions and are left using spreadsheets, email alerts, and manual review. This is the gap RegWatch AI fills.

---

## 3. Target Market

### 3.1 Primary Customers

| Segment | Description |
|---------|-------------|
| Community Banks | 5,000+ institutions in the US with $100M–$10B in assets. Typically 1–3 compliance officers. Cannot afford enterprise solutions. |
| Credit Unions | 4,700+ federally insured credit unions. Similar compliance burden. NCUA regulated. |
| Compliance Consultants | Independent consultants serving 5–20 community bank clients each. Channel partners and resellers. |

### 3.2 User Personas

**Persona 1: Sarah — Chief Compliance Officer, Community Bank**

| Attribute | Detail |
|-----------|--------|
| Institution | $500M in assets, 12 branches, 150 employees |
| Team | 2 compliance officers including herself |
| Pain Point | Spends 20 hrs/week on manual regulatory monitoring. Worried about missing something important. |
| Goal | Stay ahead of regulatory changes without hiring additional staff |
| Budget Authority | Yes — can approve tools under $5K/month without board approval |
| Willingness to Pay | $1,500–2,500/month |

**Persona 2: Mike — Compliance Consultant**

| Attribute | Detail |
|-----------|--------|
| Business | Independent compliance consultant, serves 8 community bank clients |
| Pain Point | Manually tracking regulations for 8 clients simultaneously is unsustainable |
| Goal | Scale his practice without hiring; deliver more value to clients |
| Budget Authority | Yes — pays for tools that help him bill more hours or serve more clients |
| Willingness to Pay | $800–1,200/month for a multi-client dashboard |

---

## 4. Product Vision & Goals

> "RegWatch AI makes every community bank compliance team as capable as a team 10x their size."

### 4.1 Product Goals

1. Automate 80% of manual regulatory monitoring for compliance teams
2. Reduce time from regulation published to internal action from weeks to 24 hours
3. Create an auditable, defensible compliance record for regulatory examiners
4. Be the first compliance tool community banks genuinely love using

### 4.2 Success Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| Time to first alert | < 24 hours after agency publishes | Month 3 |
| Policy mapping accuracy | > 85% vs manual review | Month 4 |
| Customer retention | > 90% monthly | Month 6 |
| Time saved per officer | > 10 hours/week | Month 4 |
| First paying client | 1 institution | Month 3 |
| MRR | $10,000/month | Month 9 |

---

## 5. Features in Scope

### F1 — Regulatory Feed Monitoring (Week 1)
- Ingest RSS feeds daily: Federal Reserve, CFPB, OCC, FDIC, FinCEN, Federal Register API
- Classify each document: `Final Rule | Proposed Rule | Guidance | Enforcement | FAQ | Other`
- Deduplicate using SHA-256 content hash + title similarity
- Flag anomalies (unusual publication volume, off-schedule releases)

**Success metric:** Zero missed publications from monitored feeds over a 7-day test window.

### F2 — AI Summarisation (Weeks 2–3)
- Structured JSON summary for every new regulation within 30 seconds
- Fields: `headline`, `plain_english_summary`, `what_changed`, `why_it_matters`, `effective_date`, `compliance_deadline`, `affected_institution_types`, `confidence_score`, `source_citations`
- Primary model: `claude-sonnet-4-20250514`. Fallback: `claude-haiku-4-5-20251001`
- Confidence < 0.80 → human review queue

**Success metric:** RAGAS faithfulness ≥ 0.85, answer relevance ≥ 0.80 on golden eval set.

### F3 — Policy Impact Mapping (Weeks 4–5)
- Accept client-uploaded PDF or DOCX internal policy documents
- Hybrid search (dense embeddings + BM25) + cross-encoder reranking
- Impact classification: `High | Medium | Low | Not Applicable`
- Output: "Your BSA Policy §4.2 needs review" with side-by-side gap view
- Vector DB: Pinecone (per-tenant index isolation)

**Success metric:** Precision@3 ≥ 0.75 on labeled golden set of policy-regulation pairs.

### F4 — Action Task Generation (Week 5)
- Convert each High/Medium impact finding into a structured task
- Fields: `title`, `owner`, `due_date`, `priority`, `status`, `source_regulation`, `source_policy_section`
- High-impact tasks require human approval before creation (HITL gate)
- Status workflow: `Open → In Progress → Completed`
- Built with LangGraph agent + tool calling

**Success metric:** 100% of High-impact findings routed through HITL gate (zero bypass).

### F5 — Audit Trail & Reporting (Week 6)
- Immutable log of every AI action: ingest, summarise, map, task creation, human override
- LangSmith trace IDs linked to every audit record
- Exportable PDF + CSV compliance report
- Monthly executive summary for board reporting
- Aligned to SR 11-7 and EU AI Act Article 13

**Success metric:** Complete audit record for every action — zero gaps in 7-day test window.

---

## 6. Phase 2 Features (Month 3–6)

- Multi-client dashboard for compliance consultants
- State regulatory agency monitoring (expand beyond federal)
- Slack and email digest integration
- Policy auto-draft suggestions based on regulatory changes
- Peer benchmarking: how similar institutions responded to same regulation

## 7. Phase 3 Features (Month 7–12)

- API access for GRC system integration
- Automated policy update drafting with tracked changes
- Regulatory exam preparation assistant
- UK FCA and Australia APRA expansion

---

## 8. Data Model — Core Entities

### RegulatoryDocument

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `source_agency` | Enum | Fed / CFPB / OCC / FDIC / FinCEN / FederalRegister |
| `doc_type` | Enum | FinalRule / ProposedRule / Guidance / Enforcement / FAQ / Other |
| `title` | String | Original title from feed |
| `url` | String | Canonical source URL |
| `published_date` | DateTime | Publication date from feed |
| `fetched_at` | DateTime | When our system fetched it |
| `content_hash` | String | SHA-256 of title+url for dedup |
| `raw_content` | Text | Full text of document |
| `summary_json` | Text | F2 JSON output (null until summarised) |
| `status` | Enum | new / summarised / mapped / reviewed |
| `review_flag` | Boolean | True if F2 confidence < 0.80 |
| `is_anomaly` | Boolean | Flagged by anomaly detector |

### Agency

| Field | Type | Description |
|-------|------|-------------|
| `id` | Int | Primary key |
| `name` | String | "Federal Reserve" |
| `slug` | String | "fed" |
| `feed_url` | String | RSS URL |
| `active` | Boolean | Toggle without deleting |

### AuditLog (INSERT-ONLY — never update or delete)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `timestamp` | DateTime | UTC, set at creation |
| `action` | Enum | ingest / summarise / map / task_create / override |
| `actor` | String | "system" or user identifier |
| `doc_id` | UUID FK | Related document |
| `payload_json` | Text | Before/after state or AI output |
| `langsmith_trace_id` | String | Full LLM trace link |

---

## 9. Technical Architecture

### Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python FastAPI |
| AI / LLM | Claude API (Anthropic) — claude-sonnet-4-20250514 |
| Agent framework | LangGraph (F4 task generation) |
| Tracing | LangSmith |
| Database (dev) | SQLite via SQLModel |
| Database (prod) | PostgreSQL |
| Vector DB | Pinecone (F3 policy search, per-tenant isolation) |
| Document processing | LangChain — PDF parsing, chunking, embedding pipeline |
| Auth | Auth0 (multi-tenant, added Week 6) |
| Infrastructure | Railway / AWS |

### Core AI Workflow

```
Step 1 — Ingest:    Fetch new documents from agency feeds daily
Step 2 — Parse:     Extract text from PDFs, split into semantic chunks
Step 3 — Summarize: LLM generates structured summary
Step 4 — Embed:     Generate vector embeddings for regulation chunks
Step 5 — Map:       Similarity search against client policy embeddings
Step 6 — Score:     LLM scores impact level, generates recommendations
Step 7 — Act:       Auto-generate tasks, notify, update audit log
```

### Multi-Tenancy

Each client institution gets an isolated data environment. Policy documents, impact assessments, and tasks are strictly separated per tenant. Pinecone namespace = tenant ID.

---

## 10. Pricing

| Plan | Price | Includes |
|------|-------|---------|
| Starter | $999/month | 1 institution, 5 agencies, basic reporting, email support |
| Professional | $1,999/month | 1 institution, all agencies, policy mapping, audit trail, priority support |
| Consultant | $2,999/month | Up to 5 institutions, multi-client dashboard, white-label reports |
| Enterprise | Custom | Unlimited institutions, API access, custom integrations, dedicated CSM |

---

## 11. Competitive Landscape

| Competitor | Positioning | Our Advantage |
|------------|-------------|---------------|
| Wolters Kluwer | Large banks ($10B+), $50K–200K/year | Too expensive for community banks |
| Regology | Mid-market, complex onboarding, generic DB | No policy mapping intelligence |
| Manual / Spreadsheets | Most community banks today, zero cost | The real incumbent — we replace spreadsheets |
| **RegWatch AI** | Community banks $100M–$5B, $1K–3K/month | Affordable, intelligent, purpose-built |

### Defensible Moats

1. **Policy library data network** — more policies seen → better mapping accuracy
2. **High switching cost** — once integrated into daily workflow, banks don't switch
3. **Domain credibility** — Moody's background gives founder unique positioning
4. **Relationship moat** — trust with compliance officers is not easily replicated

---

## 12. Go-To-Market Strategy

### Phase 1: Pilot (Month 1–3)
- **Goal:** 2–3 pilot clients (free/discounted) for feedback + testimonial
- **Target:** Compliance consultants first — faster decisions, multiplier effect
- **Outreach:** LinkedIn, NAFCU, CUNA, ABA community groups
- **Success criteria:** At least 1 pilot willing to convert to paid

### Phase 2: First Revenue (Month 3–6)
- Convert pilots to paid at $800–1,500/month
- Launch on Product Hunt + compliance communities
- Content: "How Community Banks Can Automate Regulatory Monitoring"
- Partner with 1–2 compliance consultants as channel resellers

---

## 13. Risk Register

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| AI hallucinations | High | HITL for high-impact assessments; confidence scoring; clear disclaimer |
| Sales cycle too long | High | Target consultants first; free pilots; one client at a time |
| Trust barrier (unknown vendor) | High | Moody's background as anchor; free pilot, no contract |
| SOC2 / security requirements | Medium | Start with consultants; build SOC2 Year 2 |
| Regulatory accuracy liability | Medium | TOS: decision support, not legal advice; compliance officer retains responsibility |
| Enterprise competitor enters community segment | Low | Build fast, get sticky clients, accumulate data moat |

---

## 14. Revenue Projections

| Timeline | Clients | Revenue |
|----------|---------|---------|
| Month 3 | 1–2 | $1,000–3,000 MRR |
| Month 6 | 8–10 | $12,000–20,000 MRR |
| Month 9 | 15 | $25,000–35,000 MRR |
| Month 12 | 20–25 | $40,000–60,000 MRR |

---

## 15. 45-Day Build Schedule

| Week | Days | Feature | Milestone |
|------|------|---------|-----------|
| 1 | 1–7 | F1 — Feed monitoring | All 5 agencies ingested, dedup working |
| 2–3 | 8–21 | F2 — Summarisation | RAGAS eval passing, human review queue live |
| 4–5 | 22–35 | F3 + F4 — Impact mapping + tasks | Policy upload, Pinecone search, LangGraph agent |
| 6–7 | 36–45 | F5 + deploy + GTM | Audit trail, PDF export, Railway deploy, first demo |

---

## 16. Open Questions

| # | Question | Owner | Due |
|---|----------|-------|-----|
| 1 | Embedding model for F3: OpenAI ada-002 vs open-source? | Engineering | Day 22 |
| 2 | PDF extraction: pdfplumber vs pymupdf? | Engineering | Day 22 |
| 3 | LangSmith project naming convention? | Engineering | Day 8 |
| 4 | Postgres migration target: Railway or Render? | Engineering | Day 36 |
| 5 | Pinecone tier for dev (free tier sufficient for MVP)? | Engineering | Day 22 |

---

*This PRD is the source of truth for MVP scope. Changes require an explicit version bump.*  
*Disclaimer: RegWatch AI output is decision support, not legal advice. The compliance officer retains full professional responsibility.*
