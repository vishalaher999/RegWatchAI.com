# RegWatch AI — Architecture

**Last updated:** 2026-06-01 (Day 1)

This document is the living map of the codebase. Updated every day a new file is created.

---

## High-Level Flow

```
Agency RSS Feeds
      │
      ▼
[F1] src/f1_ingest/     ← fetch, parse, deduplicate, classify
      │
      ▼ RegulatoryDocument (status: NEW)
      │
      ▼
[F2] src/f2_summarise/  ← LLM summarisation → summary_json
      │
      ▼ RegulatoryDocument (status: SUMMARISED)
      │
      ▼
[F3] src/f3_impact/     ← hybrid search against uploaded policies
      │
      ▼ ImpactMapping records
      │
      ▼
[F4] src/f4_tasks/      ← LangGraph agent → Task records (HITL gate)
      │
      ▼
[F5] src/f5_audit/      ← immutable AuditLog + report export
```

All features read from and write to a single SQLite database (dev) or Postgres (prod).

---

## Files

### `src/models.py`
**What it does:** Defines all database tables as SQLModel classes.  
**Tables:** `Agency`, `RegulatoryDocument`, `Task`, `AuditLog`  
**Why it exists:** Single source of truth for data shape. Used by all five features.  
**Key design decision:** `content_hash = SHA-256(title + url)` is the deduplication key — prevents the same regulation from being processed twice if it appears in multiple feeds.
**Day 31 — `Task` / `TaskStatus`:** `Task` (status: `open`/`in_progress`/`completed`) is F4's output — one row per AI-drafted compliance task. `source_policy_name`, `source_section_id`, `source_regulation_doc_id`, `source_regulation_title`, `source_impact_level` are stored on the row itself (not just a foreign key into `impact_results.json`, which is a regenerable file) so a `Task` stays traceable back to its originating F3 finding even after F3's matches are regenerated.
**Day 33 — `Task.linked_regulations_json`:** Optional JSON list of `{"regulation_doc_id", "regulation_title"}`, appended to by the `link_regulation` tool. Separate from `source_regulation_*` (the one finding that originally produced the task) — a task can turn out to be relevant to additional regulations discovered later.
**Migration note (found Day 34):** `create_db_and_tables()` only runs `SQLModel.metadata.create_all()`, which does NOT add columns to existing tables. Adding `linked_regulations_json` to the `Task` model required a manual `ALTER TABLE task ADD COLUMN linked_regulations_json TEXT` on the existing `regwatch.db` (run once, non-destructive). No migration tool (e.g. Alembic) is in place yet — future model field additions to existing tables need the same manual step until one is added.

### `src/database.py`
**What it does:** Creates the DB engine, exposes `create_db_and_tables()` and `get_session()`.  
**Why it exists:** Separates connection management from model definitions. Allows models to be imported in tests without creating a live DB connection.  
**Key design decision:** `DATABASE_URL` read from `.env` — swapping SQLite → Postgres requires only an env var change, no code change.

### `docs/PRD-v1.0.md`
**What it does:** Product Requirements Document — defines scope, users, success metrics, and data model rationale.  
**Why it exists:** Schema decisions need written rationale or they look arbitrary six weeks later.

---

## Database Schema (Day 1)

```
Agency
  id          INTEGER PK
  name        TEXT
  slug        TEXT UNIQUE
  feed_url    TEXT
  active      BOOLEAN

RegulatoryDocument
  id              TEXT PK (UUID)
  agency_id       INTEGER FK → Agency
  source_agency   TEXT (enum)
  doc_type        TEXT (enum)
  title           TEXT
  url             TEXT UNIQUE
  published_date  DATETIME
  fetched_at      DATETIME
  content_hash    TEXT UNIQUE  ← deduplication key
  raw_content     TEXT
  summary_json    TEXT         ← F2 output (JSON string)
  status          TEXT (enum)
  review_flag     BOOLEAN
  is_anomaly      BOOLEAN

AuditLog
  id                  TEXT PK (UUID)
  timestamp           DATETIME
  action              TEXT (enum)
  actor               TEXT
  doc_id              TEXT FK → RegulatoryDocument
  payload_json        TEXT
  langsmith_trace_id  TEXT
```

### `src/f1_ingest/agencies.py`
**What it does:** Defines `AGENCY_SEEDS` (the 6 monitored sources) and `seed_agencies()` which writes them to the DB idempotently.  
**Why it exists:** Single source of truth for which feeds we monitor. Adding a new agency = one dict entry + re-run setup.  
**Key constant:** `FR_API_SLUGS` — tells the orchestrator which agencies use the JSON API vs RSS.

### `src/f1_ingest/classifier.py`
**What it does:** Keyword-matches a document title to return a `DocType` enum value.  
**Why it exists:** Classifying doc type on ingest is free and fast. LLM classification (F2) will refine this later.  
**Key design:** Rules are ordered — more specific phrases (`advance notice of proposed rulemaking`) before broader ones (`proposed rule`). First match wins.

### `src/f1_ingest/dedup.py`
**What it does:** Computes `SHA-256(title + url)` and checks if that hash exists in the DB.  
**Why it exists:** Joint rules appear in multiple agency feeds simultaneously. Dedup prevents the same regulation from being processed twice.

### `src/f1_ingest/fetcher.py`
**What it does:** Two fetchers — `fetch_feed()` for RSS (Federal Reserve), `fetch_fr_api()` for the Federal Register JSON API (CFPB, OCC, FDIC, FinCEN).  
**Why two fetchers?** The FR RSS feeds block automated requests and return an HTML gate page. The JSON API is public and stable.  
**Key decision:** `fetch_feed()` uses feedparser to normalize inconsistent RSS formats. `fetch_fr_api()` parses the `results` JSON array.

### `dashboard/app.py`
**What it does:** Streamlit browser dashboard. Loads all documents, applies agency/doc-type/anomaly filters, renders document cards with expandable content previews.  
**Run:** `streamlit run dashboard/app.py` → http://localhost:8501  
**Key pattern:** `@st.cache_data(ttl=300)` — caches DB query for 5 minutes so filter interactions are instant. Documents converted to plain dicts before caching (SQLModel session references can't be serialised).

### `dashboard/components.py`
**What it does:** Reusable display helpers — `render_metric_row()`, `render_document_card()`, `render_sidebar_filters()`, colour-coded doc type badges.  
**Why separate:** When React replaces Streamlit in Week 6, only this file changes — the data queries in `app.py` stay the same.

### `src/f1_ingest/fulltext.py`
**What it does:** Fetches full document text. Two strategies: FR API `raw_text_url` for Federal Register agencies (plain text, no parsing needed); BeautifulSoup HTML extraction for Fed press releases.  
**Key functions:** `enrich_document(doc)` — fetches one doc. `run_fulltext_enrichment(limit)` — batch enriches documents with short/missing `raw_content`. `find_near_duplicates(docs)` — title similarity dedup using `SequenceMatcher`.  
**Rate limit:** 1-second delay between HTTP requests.  
**Threshold:** `MIN_CONTENT_LENGTH = 500` chars — docs shorter than this are re-fetched. `SIMILARITY_THRESHOLD = 0.85` for near-duplicate titles.

### `scripts/enrich_fulltext.py`
**What it does:** One-time backfill + ongoing enrichment script. `--limit N` controls how many docs to process per run.  
**Usage:** `python scripts/enrich_fulltext.py --limit 20`

### `src/f1_ingest/health.py`
**What it does:** Two checks per agency — reachability (can we reach the feed and get ≥1 entry?) and freshness (do we have DB documents from this agency within 3 days?).  
**Why it exists:** Silent failure is more dangerous than a crash. A feed returning 200 with empty content would pass a reachability-only check while quietly missing all documents.  
**Returns:** `list[AgencyHealth]` with `.healthy`, `.status_label`, `.last_doc_date` per agency.

### `scripts/daily_validate.py`
**What it does:** The single daily command — health check → ingest → validation report. Exit code 0=pass, 1=fail.  
**Usage:** `python scripts/daily_validate.py` or `python scripts/daily_validate.py --skip-ingest`  
**Why exit code:** Standard Unix convention — monitoring tools watch for non-zero exit to trigger alerts.

### `tests/test_f1_integration.py`
**What it does:** 7 live integration tests against real government feeds. Includes `test_zero_missed_publications_metric` which directly verifies the F1 success criterion.  
**Run with:** `pytest tests/ -m slow`  Excluded by default (see `pytest.ini`).

### `pytest.ini`
**What it does:** Configures `slow` marker. Fast unit tests run by default; integration tests opt-in with `-m slow`.

### `src/f1_ingest/anomaly.py`
**What it does:** Two anomaly signals — volume Z-score (is today's count statistically unusual?) and off-schedule detection (is this an unusual publication day for this agency?).  
**Why Z-score:** Adapts to each agency's individual baseline. A fixed threshold would false-alarm on high-volume agencies and miss spikes in low-volume ones.  
**Thresholds:** `VOLUME_Z_THRESHOLD = 2.0` (top ~2.5%), `OFF_SCHEDULE_MIN_PCT = 0.10` (less than 10% historical frequency for that weekday).

### `src/f1_ingest/query.py`
**What it does:** CLI inspection tool. `--recent N`, `--agency slug`, `--anomalies` flags. Shows document counts by agency and type, plus anomaly/review queue counts.  
**Why it exists:** Development visibility and demo tool before F5 UI is built. Run `python -m src.f1_ingest.query` to see current DB state.

### `src/f1_ingest/ingest.py`
**What it does:** Orchestrator — loads active agencies, routes to correct fetcher, deduplicates, saves new docs, writes AuditLog. `log_document_ingest(session, doc, agency_slug)` (Day 36, KM #242) writes one `AuditLog(INGEST, doc_id=doc.id)` per newly-saved document, in addition to the existing per-agency-run summary log.
**Why it exists:** Separates coordination (ingest.py) from data fetching (fetcher.py) so each can be tested and changed independently.
**Day 36 change:** Before Day 36, `INGEST` was only logged once per agency run with no `doc_id` — an ingest event couldn't be traced to a specific `RegulatoryDocument` (gap #2 in `docs/F4-Audit-Report-v1.md` Section 7). `log_document_ingest` is the per-document entry `get_task_audit_trail` now surfaces as the first entry in a Task's trail (for documents ingested after Day 36 — historical pre-Day-36 documents have no per-doc `INGEST` row).
**Tests:** `tests/test_f1_audit.py` — 1 test verifying `log_document_ingest` writes a doc-scoped `AuditLog(INGEST)` with the expected payload.

### `scripts/setup_db.py`
**What it does:** Creates all tables and seeds agency records. Safe to run multiple times.  
**Usage:** `python scripts/setup_db.py`

### `fixtures/agencies/sample_feed.json`
**What it does:** Offline snapshot of a real-shaped feed with 4 entries covering all doc types.  
**Why it exists:** Enables offline development and testing without hitting live agency feeds.

### `tests/test_f1_classifier.py` + `tests/test_f1_dedup.py`
**What they do:** 18 tests covering classifier accuracy and dedup correctness. Use in-memory SQLite — no file created.

### `src/f2_summarise/summariser.py`
**Day 37 addition (KM #241 LangSmith):** `_call_claude()` is now wrapped in `@traceable(name="f2_summarise_call", run_type="llm")` and returns `(text, trace_id)` instead of just `text` — `trace_id` comes from `get_current_run_tree().id` read immediately after the API call, wrapped in try/except so a missing/invalid `LANGCHAIN_API_KEY` leaves `trace_id=None` without affecting the summary. `summarise_document()` passes this into the existing `AuditLog(SUMMARISE).langsmith_trace_id` field (defined in `src/models.py` since early in the project but never populated before now).
**Tests:** `tests/test_f2_tracing.py` — 3 tests on `_call_claude` (trace_id captured when a run tree exists, `None` when it doesn't, `None` when `get_current_run_tree()` raises).

**Day 38 addition (KM #263 Citations + #269 Guardrails):** new `_apply_guardrails(summary, num_chunks)` (alongside `_validate_summary`) runs three post-hoc safety checks independent of `confidence_score`/the router: (1) if `effective_date`/`compliance_deadline` is set, a `source_citations` entry must reference that field name — closes the gap `docs/RCA-Hallucinated-Deadline-v1.md` identified (no field-level evidence trail for dates); (2) `confidence_score >= CONFIDENCE_THRESHOLD` with empty `source_citations` warns; (3) a citation referencing `Chunk N` outside `1..num_chunks` (the 1-indexed range from `format_chunks_for_prompt`) warns. `summarise_document()` combines these with `_validate_summary`'s warnings, logs them as `payload["guardrail_warnings"]` on the `SUMMARISE` `AuditLog` row, and forces `needs_review = True` if any guardrail warning fires — overriding an otherwise-APPROVED/DISMISS routing decision.
**Tests:** `tests/test_f2_guardrails.py` — 5 tests (uncited date field, properly-cited date field, high confidence with no citations, out-of-range chunk citation, clean summary with zero warnings).

### `src/f3_impact/extractor.py`
**What it does:** Parses bank policy text into `PolicySection` objects — one per `N.M` numbered subsection (e.g. "4.2 Currency Transaction Reporting (CTR)"), tagged with its parent `SECTION N: TITLE` header.
**Why it exists:** F3's output must point Sarah to a specific policy section ("BSA Policy §4.2 needs review"). The `N.M` subsection is the smallest unit that's both meaningful to a compliance officer and small enough for accurate embedding/matching in Day 23-24.
**Key design decision:** Regex-based parsing (`SECTION N:` / `N.M Title`) rather than an LLM call — the 3 synthetic policy fixtures follow a consistent structure, and a deterministic parser is free, instant, and testable. LLM-based extraction is a fallback to revisit if real client policies don't follow this pattern (flagged via the "0 sections found" case in `docs/wireframes/policy-library-ux-v1.md`).
**Run:** `python -m src.f3_impact.extractor` — prints section counts/previews for all policies in `fixtures/policies/`.
**Tests:** `tests/test_f3_extractor.py` — verifies parsing on a synthetic sample and on all 3 real fixtures (72 sections total).

**Day 39 addition (KM #267/268 PII):** `extract_policy_sections()` now redacts each section's body text via `redact_text()` (`src/f3_impact/pii.py`) before constructing `PolicySection`. New field `PolicySection.pii_findings: dict[str, int]` (e.g. `{"SSN": 1}`, empty if none) records what was redacted in that section, for `build_indexes.py`'s audit logging. The 3 fixture policies are PII-free, so `pii_findings == {}` for all 72 sections — verified live.

### `src/f3_impact/pii.py` (NEW — Day 39, KM #267/268)
**What it does:** `redact_text(text) -> (redacted_text, findings)`. Regex patterns for SSN, EIN, 16-digit card numbers, emails, phone numbers, and labeled account/routing numbers (digits following "Account Number:"/"Routing Number:" — bare digit runs elsewhere, e.g. regulatory citations, are left alone). Matches are replaced with `[REDACTED-<TYPE>]`; `findings` is a count-by-type dict.
**Why it exists:** A real client's policy library will contain account numbers, SSNs, and emails in example text. Per CLAUDE.md's "Public regulatory data only — no Moody's internal or client data" constraint, nothing reaches the multi-tenant Pinecone index or an LLM prompt unredacted.
**Key limitation (documented, not fixed):** v1 is regex-only — structured PII only. Free-text PII (names, addresses) needs NER and is a documented v2 gap. See `docs/Enterprise-Pilot-Program-v1.md`.
**Tests:** `tests/test_f3_pii.py` — 8 tests: one per PII type, a clean-text-passthrough case, and two `extract_policy_sections()` integration tests (PII redacted + `pii_findings` populated; clean text → empty `pii_findings`).

### `src/f3_impact/vectorstore.py`
**What it does:** `VectorIndex` class — a local, numpy + JSON backed vector store with `upsert_batch()`, `query()`, `save()`, `load()`. Cosine similarity search over normalized embeddings (dot product).
**Why it exists:** F3 needs a dual-index vector store (policy sections + regulation chunks) per CLAUDE.md, but `.env` has no `PINECONE_API_KEY`. F2 already established local `sentence-transformers` embeddings as the project default (zero cost, no data leaves the machine). This class gives the same `upsert`/`query` interface a Pinecone index would, so swapping to real Pinecone later is a one-file change — same pattern as `DATABASE_URL` for SQLite → Postgres.
**Key design decision:** Vectors are normalized on embed (handled by `EmbeddingModel` in `src/f2_summarise/embeddings.py`), so cosine similarity reduces to a single matrix-vector dot product (`self.vectors @ query_vector`) — fast even for thousands of items on CPU.

### `src/f3_impact/build_indexes.py`
**What it does:** Builds and saves two `VectorIndex` collections to `data/f3_indexes/` (gitignored, regenerable):
  - `policy_sections` — all 72 `PolicySection`s from `fixtures/policies/*.txt` (via `extractor.py`)
  - `regulation_chunks` — hierarchical chunks (`chunk_hierarchical` from F2) of every `RegulatoryDocument` with `status=SUMMARISED`
**Why it exists:** This is the "dual-index" deliverable for Day 23 — Day 24's similarity matcher searches `regulation_chunks` for each entry in `policy_sections`.
**Run:** `python -m src.f3_impact.build_indexes` (re-run any time policies or summarised documents change). Verified: 72 policy sections + 521 regulation chunks indexed from 25 summarised docs.
**Tests:** `tests/test_f3_vectorstore.py` — 5 tests against a fake embedding model (no model download needed for CI speed).
**Day 29 — contextual retrieval (KM #167):** `build_policy_index()` now embeds `"{policy_name} — {parent_section}\n{section_title}\n{text}"` (was `"{section_title}\n{text}"`) — policy/section hierarchy as embedding context. Measured neutral (73.3%, same as before). A second experiment — prepending `"Document: {title}\nSource: {agency}\nSection: {header}"` to each regulation chunk before embedding — measured 70.0% (a regression, right at `REGRESSION_BASELINE`) and was NOT applied; see the `build_regulation_index()` docstring and `notes/Day-29-F3.md` for the before/after. In both cases `metadata["text"]` stays the raw text used for BM25 and evidence display — only the embedding input changed.
**Day 39 addition (KM #267/268 PII):** `build_policy_index()` calls `_log_pii_redactions(sections)` after `extract_policy_library()`. It aggregates each `PolicySection.pii_findings` by `policy_name` and writes one `AuditLog(PII_REDACT, doc_id=None)` row per policy file with `>=1` redaction, payload `{"policy_name", "redaction_counts"}`. `doc_id=None` because policy files aren't `RegulatoryDocument` rows. No-op (no rows written) when no PII is found — verified against the 3 PII-free fixtures.

### `src/f3_impact/matcher.py`
**What it does:** `HybridMatcher` — for a policy section's text, finds the top regulation chunks via dense search (`VectorIndex.query`) + BM25 keyword search, combines rankings with RRF, then collapses chunk-level hits to one row per regulation document (max score, best chunk kept as evidence). `build_matches()` runs this for all 72 policy sections and writes `data/f3_indexes/matches.json`.
**Why it exists:** This is the "moat's connective tissue" — `matches.json` is the candidate set Day 25's impact classifier scores (High/Med/Low/N/A) and what Day 26's eval set labels for precision@5.
**Key design decision:** Hybrid (dense + BM25 + RRF), not dense-only — same justification as F2's Day 16 hybrid search. Dense embeddings catch semantic matches ("cash transaction... $10,000" -> CTR section) but can miss exact regulatory citations ("Regulation B", "12 CFR 1002.6") that BM25 catches directly. `RRF_K=60` reuses F2's validated constant.
**Run:** `python -m src.f3_impact.matcher` (requires `build_indexes.py` to have run first).
**Tests:** `tests/test_f3_matcher.py` — 7 tests covering RRF combination logic, end-to-end matching against a fake index, the Day 30 chunk-merge helper, and multi-query fallback/extension behavior.
**Day 30 — multi-query retrieval (KM #164):** `match_section_multi_query(query_text, policy_name)` issues one query per regulation the policy itself names (via `citations.py`'s `get_named_regulations()`), in addition to the original section-text query — targeting policy sections that reference multiple regulatory frameworks in one (diluted) embedding. `_merge_chunk_matches()` combines all queries' chunk results, keeping the best `rrf_score`/`dense_score` per chunk before collapsing to per-document matches. `build_matches()` now calls this instead of `match_section()`. Policies with no named regulations fall back to exactly one query (identical to the old behavior). Measured **76.7% (23/30)** — up from 73.3%, the first accuracy gain since Day 27 — kept.

### `src/f3_impact/citations.py`
**What it does:** `extract_named_regulations(policy_text)` regex-extracts the regulations a policy fixture explicitly cites ("... Act", "Regulation X", "(ABBR)"). `get_named_regulations(policy_name)` loads/caches this set from `fixtures/policies/<policy_name>.txt`. `is_named_regulation_match(policy_name, regulation_title)` returns True if a candidate regulation's title names a law the policy itself cites.
**Why it exists:** Day 26's eval (40%) found the classifier's errors split cleanly on this signal — generic regulations (e.g. "Equal Credit Opportunity Act (Regulation B)") over-match unrelated policies (false positives) while under-scoring in the policy they actually govern (false negatives). Whether the policy itself names the regulation is a free, cheap signal `dense_score` alone can't see.
**Key limitation (documented, not fixed):** only catches "... Act", "Regulation <Letter>", and "(ABBR)" citation styles — good enough for the 3 current fixtures.

### `src/f3_impact/classifier.py`
**What it does:** `classify_impact(dense_score, named_regulation_match=False) -> ImpactLevel` (HIGH/MEDIUM/LOW/NOT_APPLICABLE). Adjusts `dense_score` by `NAMED_MATCH_BOOST` (+0.10) or `NO_MATCH_PENALTY` (-0.20) before applying the same fixed thresholds (0.55/0.45/0.35). `classify_matches()` computes `named_regulation_match` (via `citations.py`) for every match in `matches.json` and applies this, writing `data/f3_indexes/impact_results.json`.
**Why it exists:** This is F3's actual output — `impact_level` per (policy section, regulation) pair, the input to the heatmap and section-output UX.
**Key design decision:** Threshold rule, not a trained LogReg/XGBoost (the roadmap's KM #17/#20) — no labeled data exists yet (Day 26 builds it). Thresholds are explainable (SR 11-7: auditable "0.566 ≥ 0.55 → High") and documented as a v1 baseline. Uses `dense_score` (cosine similarity, real dynamic range) rather than the RRF `score` (clusters near a ~0.03 floor, Day 24 finding). Day 27 added the `named_regulation_match` boost/penalty — same thresholds, same explainability ("0.47 + 0.10 = 0.57 ≥ 0.55 → High, because Reg B is in this policy's own Regulatory Framework section").
**Run:** `python -m src.f3_impact.classifier` (requires `matcher.py` to have run first).
**Tests:** `tests/test_f3_classifier.py` — 4 tests covering threshold boundaries (with/without named match) and end-to-end classification.
**Day 36 addition:** `log_map_decisions(results)` (KM #242 Compliance logging) writes one `AuditLog(MAP, doc_id=regulation_doc_id)` entry per classified match — payload includes `policy_name`, `section_id`, `dense_score`, `named_regulation_match`, `impact_level`, and the three thresholds. Closes gap #1 in `docs/F4-Audit-Report-v1.md` Section 7 (F3 previously wrote no audit record at all). Called from `main()` after `impact_results.json` is written. Re-running the classifier writes new rows each time — same "each run is its own audit event" pattern as F2's repeated `SUMMARISE` entries.
**Tests:** `tests/test_f3_audit.py` — 2 tests: one entry per match with correct payload (including thresholds), and zero entries for a section with no matches.

### `fixtures/golden/impact_pairs.json`
**What it does:** 30 hand-labeled (policy section, regulation) pairs with `true_impact_level` and a one-line rationale per pair, stratified to cover true positives, true negatives, and the Day 25 "generic-language over-match" pattern.
**Why it exists:** This is F3's golden eval set (named in CLAUDE.md). It's the ground truth `evals/f3_eval.py` checks the classifier against.
**Key caveat:** Labeled by Claude (v1), not a compliance SME — flagged in the file's `_metadata` for human review before being treated as production ground truth (SR 11-7).

### `evals/f3_eval.py`
**What it does:** Runs `classify_impact(dense_score, named_regulation_match)` against the 30 golden pairs (re-looking up current `dense_score` from `matches.json` and computing `named_regulation_match` via `citations.py`), computes accuracy + a confusion matrix, and exits non-zero if accuracy < 80% (`CI_GATE_THRESHOLD`). Also defines `REGRESSION_BASELINE` (0.70) — a separate, lower bar that `tests/test_f3_eval.py` enforces every run so a future change can't silently drop accuracy below the current measured level (KM #258 Regression CI).
**Why it exists:** F3's eval-first checkpoint. Day 26 result: 40% (12/30). Day 27, after adding `named_regulation_match`: 73.3% (22/30) — still below the 80% gate, but the false-positive pattern (generic regulations over-matching unrelated policies) and false-negative pattern (true ECOA matches scoring just under HIGH) are both largely fixed. Day 30, after multi-query retrieval (KM #164): **76.7% (23/30)** — `REGRESSION_BASELINE` ratcheted up to 23/30. Remaining mismatches (7/30) are mostly BSA/TRID sections vs "Equal Credit Opportunity Act (Regulation B)" / "Agency Information Collection Activities" scoring LOW where NOT_APPLICABLE was expected, plus one MEDIUM under-scored as LOW.
**Run:** `python -m evals.f3_eval` (requires `matcher.py` and `classifier.py` outputs to exist).
**Tests:** `tests/test_f3_eval.py` — 4 tests: real golden set, a controlled fake dataset (BSA-AML-Policy with non-matching "Reg A"/"Reg B" titles), the 80% CI gate constant, and the regression-baseline test.

### `docs/Build-vs-Buy-Matrix-v1.md`
**What it does:** Product analysis of build vs. buy for F3, at both the whole-feature level (buy a RegTech impact-mapping suite?) and component level (embeddings, vector store, hybrid search, classifier).
**Why it exists:** Day 26 roadmap deliverable, directly informed by the 40% eval result — concludes the fix is feature engineering (e.g. named-regulation matching), not buying a smarter black-box classifier or vector DB.

### `docs/Design-Partner-Profiles-v1.md`
**What it does:** 5 candidate community bank/credit union profiles (with criteria and how to find them) plus 2 outreach email drafts (cold and warm/referral).
**Why it exists:** Day 27 Product deliverable — drafts only, not sent. F3's 73.3% eval result is far enough along to demo for early feedback on whether the impact-mapping output is useful to a real compliance officer.

### `docs/F3-MVP-Sample-v1.md`
**What it does:** 10 real (policy section, regulation) pairs pulled from `data/f3_indexes/impact_results.json` — real ingested F1/F2 regulations matched against the 3 synthetic policy fixtures — spanning all 4 impact levels, each with evidence text and rationale. Deliberately includes one of Day 27's 8 known mismatches (BSA §5.1 vs. a generic CFPB comment-request notice, predicted LOW vs. true NOT_APPLICABLE).
**Why it exists:** Day 28 (Week 4 exit/review) Engineering deliverable — "F3 MVP: impact on 10 pairs". Shows what Sarah would actually see, including a documented limitation, not just best-case output.

### `docs/Executive-Deck-v1.md`
**What it does:** 5-slide outline (markdown) — the problem, the 5-feature pipeline, F3's current MVP output, a definition of "MVAP" (Minimum Viable AI Product), and next steps.
**Why it exists:** Day 28 Product deliverable. Defines MVAP (not in the original roadmap) as "useful and honest today" — explicitly distinct from the 80% `CI_GATE_THRESHOLD`, 5+ policies, or zero false positives, which are v2 goals.

### `docs/Trust-Strategy-v1.md`
**What it does:** 6 concrete trust mechanisms RegWatch already has (evidence-backed verdicts, disclosed limitations, auditable threshold logic, human-in-the-loop, regression-CI as a standing accuracy floor, honest design-partner framing) plus 3 honest gaps for Week 5+ (no F3 audit trail yet, golden set not SME-validated, no feedback loop from Sarah back into the system).
**Why it exists:** Day 29 Product deliverable ("Trust strategy — how RegWatch earns compliance trust"). Uses Day 29's own contextual-retrieval experiment (one change kept, one rejected by the regression-CI gate) as a live example of mechanism #5.

### `docs/Progressive-Autonomy-Roadmap-v1.md`
**What it does:** Defines a staged path from "Sarah reviews everything" (Stage 0, current) toward limited automation, where each stage's eligibility is gated by that prediction class's measured PRECISION on the golden set (e.g. Day 30: HIGH 90.9%, NOT_APPLICABLE 88.9%, LOW 50.0%, MEDIUM unmeasured) — not by a calendar or a target accuracy. Stage 3 is deliberately left aspirational/undesigned pending real approval data from Stage 2.
**Why it exists:** Day 30 Product deliverable ("Progressive autonomy roadmap — HITL → gradual automation"). Gives F4 (Day 32+, HITL approval flow) a data model to design toward from day one, and extends Trust-Strategy-v1.md's mechanism #4 (HITL where least certain) into a graduated, eval-driven schedule.

### `src/f4_tasks/prompts.py`
**What it does:** F4's prompt constants — `PROMPT_VERSION = "v2"`, `PRIMARY_MODEL`/`FALLBACK_MODEL` (same as F2: `claude-sonnet-4-20250514` / `claude-haiku-4-5-20251001`), and `SYSTEM_PROMPT` for the ReAct task-drafting agent.
**Why it exists:** SR 11-7 prompt versioning — same rationale as `src/f2_summarise/prompts.py`. `SYSTEM_PROMPT` requires the agent to call both lookup tools before drafting, cite the policy section + regulation title in the task title, quote a verbatim evidence excerpt, always set `owner="Sarah"` (v1 limitation, unchanged in v2), and ground `due_date` in `get_regulation_deadline`'s result or fall back to a documented 30-day default SLA.
**Day 33 — v2:** the agent's final action is now a `create_task` tool call (validated by Pydantic `args_schema`) instead of a bare JSON text response. v1's drafting logic (lookup order, content requirements, owner/due_date rules) is unchanged — only the output mechanism changed.

### `src/f4_tasks/tools.py`
**What it does:** LangChain `@tool`-decorated functions for the F4 agent and task management.
- Lookup tools (Day 31): `get_regulation_deadline(regulation_doc_id)` reads `RegulatoryDocument.summary_json` (written by F2's NER step) and returns `effective_date`/`compliance_deadline`; `get_policy_section_text(policy_name, section_id)` reads the matching `PolicySection.text` via F3's `extract_policy_file()`. Each wraps a plain `_lookup_*` function that returns a dict, unit-tested without any LLM.
- `create_task` (Day 33, `args_schema=CreateTaskArgs`): the agent's final action — `title`, `description`, `owner: Literal["Sarah","Mike"]`, `due_date` (validated as ISO via `field_validator`). Returns an echo of its args; `generate_task_for_finding` reads the validated args directly from the tool call, not this return value.
- `assign_owner(task_id, owner)`, `set_due_date(task_id, due_date)`, `link_regulation(task_id, regulation_doc_id, regulation_title)` (Day 33): DB-backed task-management tools. Each loads the `Task`, applies the change, writes an `AuditLog(OVERRIDE)` row with before/after values, and commits.
**Why it exists:** Gives the agent grounded access to F2's extracted deadline data and F3's policy fixture text instead of letting it hallucinate dates or policy wording (lookup tools); validates the agent's draft output and records human edits to existing tasks with a full audit trail (Day 33 tools).
**Key design decision (Day 33):** Pydantic validates `owner`/`due_date` AT THE TOOL CALL boundary. An invalid `create_task(owner="Bob", ...)` call raises `ValidationError` before any application code runs; LangGraph's `ToolNode` feeds that error back to the model as a `ToolMessage`, so the model retries with a corrected value — self-correcting, instead of only being caught by `evals/f4_eval.py` after the fact (v1's failure mode).
**Tests:** `tests/test_f4_tools.py` — 22 tests: the original 6 lookup tests against real fixture/DB data, plus `create_task`/`assign_owner`/`set_due_date`/`link_regulation` schema-validation and in-memory-SQLite DB tests.

### `src/f4_tasks/agent.py`
**What it does:** `load_high_findings()` flattens `data/f3_indexes/impact_results.json` into one dict per (policy section, regulation) pair where `impact_level == "high"` (27 total as of Day 30). `build_agent()` builds a LangGraph `create_react_agent` (`ChatAnthropic(claude-sonnet-4-20250514)` + the 2 lookup tools + `create_task` + `SYSTEM_PROMPT`). `generate_task_for_finding()` runs the agent on one finding and, via `_extract_create_task_args()`, reads the validated args off the agent's `create_task` tool call (Day 33 — replaces v1's `_parse_agent_output` JSON-text parsing). `run(limit=5)` generates tasks for the first N HIGH findings, writes `Task` rows + `AuditLog` rows (`action=TASK_CREATE`, payload includes model/prompt_version/source finding ids), and writes `data/f4_tasks/tasks.json`.
**Why it exists:** F4's first deliverable (KM #177 ReAct) — turns an F3 HIGH finding into a concrete, evidence-cited compliance task for Sarah.
**Key design decisions:** v1 runs on only 5/27 HIGH findings (Anthropic API cost control). `owner="Sarah"` always (documented limitation — she's the persona CLAUDE.md says "approves high-risk tasks"; Mike's monitoring role doesn't map to task ownership yet). `due_date` is grounded in `compliance_deadline`/`effective_date` when available, else `today + 30 days` with an explicit "(default 30-day SLA...)" note in the description. Day 33 replaced free-JSON output with the validated `create_task` tool call described above; the function's return shape (`source_*` + `title`/`description`/`owner`/`due_date`) is unchanged, so `hitl_agent.py` required no changes.
**Day 37 change (KM #241 LangSmith):** `generate_task_for_finding()` wraps `agent.invoke(...)` in `langchain_core.tracers.context.collect_runs()`. LangGraph/LangChain auto-trace every step when `LANGCHAIN_TRACING_V2=true`, producing one `RunTree` per graph step/tool call plus a root `"LangGraph"` run (`parent_run_id is None`) — that root run's id is returned as `_langsmith_trace_id` and stored on `AuditLog(TASK_CREATE).langsmith_trace_id` in `run()`. Also fixed a pre-existing bug found while verifying this: `run()`'s `with get_session()` block never called `session.commit()`, so `Task`/`AuditLog` rows from `python -m src.f4_tasks.agent` were silently never persisted (only `tasks.json` was written) — added `session.commit()` at the end of the loop.
**Run:** `python -m src.f4_tasks.agent` (makes real Anthropic API calls; requires `data/f3_indexes/impact_results.json` to exist).

### `evals/f4_eval.py`
**What it does:** Structural/traceability validation (no golden "good task" labels exist yet — documented gap). For every task in `data/f4_tasks/tasks.json`: title must reference `source_section_id` and a word from `source_regulation_title`; `owner` must be in `{"Sarah", "Mike"}`; `due_date` must parse as ISO; `description` must share a >=30-char contiguous substring with the source finding's `matched_chunk_text` (via `difflib.SequenceMatcher`, `autojunk=False`). CI gate = 100% pass rate.
**Why it exists:** Eval-first (build rule 7) — Day 31 has no semantic-quality golden set, so this checks the one thing that CAN be checked mechanically: is every generated task traceable and well-formed. Semantic quality (is the due date *right*, is the title *good*) is an explicit future gap, same honest-caveat pattern as F3's Claude-labeled golden set.
**Run:** `python -m evals.f4_eval` (requires `data/f4_tasks/tasks.json` to exist).
**Tests:** `tests/test_f4_eval.py` — 8 tests covering each structural check individually plus an end-to-end run against a fake tasks/impact-results pair.

### `docs/Task-Board-UX-v1.md`
**What it does:** Kanban wireframe (Open / In Progress / Completed, matching `TaskStatus`) showing a generated task card with its full evidence trail (policy section, regulation, impact level, model/prompt version, audit log link) and an `Approve` action.
**Why it exists:** Day 31 Product deliverable — gives F4's `Task` rows and `AuditLog` trail a concrete UI destination, and makes explicit that v1 has no automation beyond drafting: every task still requires Sarah's approval (Progressive Autonomy Roadmap Stage 2).

### `src/f4_tasks/hitl_agent.py`
**What it does:** Day 32, KM #190-191 LangGraph HITL. Wraps Day 31's ReAct agent in a 3-node `StateGraph` (`draft` -> `await_approval` -> `finalize`) compiled with `InMemorySaver`. `draft` runs `generate_task_for_finding()` (or an injected `draft_fn` for testing — no LLM calls needed in tests). `await_approval` calls `interrupt(drafted_task)`, pausing the graph until resumed. `finalize` runs only after `resolve_approval()`: `approved=True` writes `Task(status=open)` + `AuditLog(TASK_CREATE)` (applying `edits` first); `approved=False` writes only `AuditLog(OVERRIDE)` with the rejected draft in `payload_json` — no `Task` row. `run_with_approval(limit=5)` drafts+pauses N findings and returns `(pending, graph)`; `resolve_approval(graph, thread_id, approved, edits)` resumes one.
**Why it exists:** Makes Stage 2 of the Progressive Autonomy Roadmap ("auto-draft HIGH-finding tasks, still require Sarah's approval") a control-flow guarantee instead of a UI convention — a `Task` row literally cannot exist without a human `resolve_approval(approved=True)` call.
**Key design decision:** `InMemorySaver` checkpointer (v1 limitation — pending approvals lost on process restart; `SqliteSaver` would persist across restarts using the same `regwatch.db`). The returned `graph` instance must be reused for `resolve_approval()` since checkpoint state lives on it.
**Day 37 change:** `finalize()` pops `_langsmith_trace_id` off `drafted_task` (added by `generate_task_for_finding()`, see `agent.py`) and stores it on `AuditLog(TASK_CREATE).langsmith_trace_id` when `approved=True` — same trace-linking as `agent.py run()`.
**Tests:** `tests/test_f4_hitl.py` — 4 tests (in-memory SQLite, fake `draft_fn`): pause-without-DB-writes, approve creates Task+AuditLog(TASK_CREATE), reject creates only AuditLog(OVERRIDE) with no Task row, edits applied on approve.

### `scripts/review_pending_tasks.py`
**What it does:** CLI for Sarah — runs `run_with_approval(limit=N)`, then for each pending draft prints title/owner/due date/description and prompts `y` (approve) / `e` (edit due date) / `n` (reject), calling `resolve_approval()` with the decision.
**Why it exists:** Day 32 Product deliverable's working implementation — verified end-to-end on 2 real F3 HIGH findings (1 approved -> Task created + TASK_CREATE log; 1 rejected -> OVERRIDE log only, no Task row).
**Run:** `python -m scripts.review_pending_tasks [N]` (makes real Anthropic API calls for drafting; N defaults to 5).

### `docs/HITL-Approval-Workflow-v1.md`
**What it does:** Documents the Day 32 approval flow (draft -> pause -> human decision -> finalize) as a diagram, walks through a real CLI run, and maps it onto `Task-Board-UX-v1.md`'s "Approve" button (a future "Pending Review" column sourced from `run_with_approval()`'s output, not the `Task` table).
**Why it exists:** Day 32 Product deliverable — turns Task-Board-UX-v1's mockup "Approve" action into a documented real flow with verified results.

### `src/f4_tasks/audit.py`
**What it does:** Day 34, KM #198 Audit trail. `get_task_audit_trail(task_id)` returns a chronological list of `{timestamp, action, actor, summary}` dicts combining: F1 `INGEST` + F2 `SUMMARISE` entries for the task's `source_regulation_doc_id`, F3 `MAP` entries for that `doc_id` further filtered to this task's `source_policy_name`/`source_section_id`, and F4 `TASK_CREATE`/`OVERRIDE` entries whose `payload_json["task_id"]` matches this task (Day 32 approval + Day 33 `assign_owner`/`set_due_date`/`link_regulation` edits). `format_trail()` renders it as plain text.
**Why it exists:** Day 33 made individual edits auditable; nothing assembled them into one story per task. Built alongside `docs/RCA-Hallucinated-Deadline-v1.md` — gives Sarah/an examiner a single place to see every ingestion, summarisation, mapping, and task-level decision/edit for a given task.
**Day 36 change:** Previously `AuditAction.INGEST` was per-agency-run (no `doc_id`) and F3 never wrote `AuditAction.MAP` — the trail couldn't show *when or how* a policy section was matched to a regulation. Day 36's `log_document_ingest` (F1) and `log_map_decisions` (F3) close both gaps; this function was extended to include them. Verified live: `python -m scripts.show_task_audit_trail 67fc89e1-...` now shows 5 SUMMARISE + 1 TASK_CREATE + 2 MAP (no INGEST — that regulation predates Day 36's per-doc logging).
**Day 37 change (KM #241 LangSmith):** new `_trace_suffix(log)` helper appends `" | trace=<id>"` to `SUMMARISE`/`TASK_CREATE` summaries when `AuditLog.langsmith_trace_id` is set (empty string otherwise — additive, not required). Verified live on a freshly-generated task (`b7190a3e-...`): trail's `[task_create]` line ends with `| trace=019ec221-7e22-7190-a95c-ef07b90306e0`.
**Tests:** `tests/test_f4_audit.py` — 8 tests (in-memory SQLite): unknown task, summarise+task_create ordering, langsmith trace_id shown/hidden, INGEST+MAP entries (including that a MAP entry for a different policy section is excluded), overrides scoped to the correct task, chronological sort, `format_trail` empty/non-empty.

### `scripts/show_task_audit_trail.py`
**What it does:** CLI — `python -m scripts.show_task_audit_trail <task_id>` prints the trail via `format_trail(get_task_audit_trail(task_id))`.
**Why it exists:** Day 34 Deliverable's working implementation — verified against the real Task created in Day 32 (`8f57f4a0-...`), showing 5 F2 SUMMARISE runs (confidence rising 75 -> 77 -> 87, `review_flag` flipping `True` -> `False`) followed by the F4 `TASK_CREATE` entry with `approved_by=human:sarah`.
**Day 36 fix:** added `sys.stdout.reconfigure(encoding="utf-8")` (same pattern as `f3_impact/classifier.py main()` and `evals/f4_eval.py main()`) — without it, the `§` character in F3 MAP summaries raised/garbled on Windows' default console codepage.

### `docs/RCA-Hallucinated-Deadline-v1.md`
**What it does:** Day 34 Product deliverable — a proactive 5 Whys RCA on a hypothetical incident where F2's NER extracts the wrong `compliance_deadline`, which flows ungrounded through F3/F4/HITL into an approved `Task` with a wrong `due_date`. Identifies the root cause (no field-level evidence trail for `compliance_deadline`) and a secondary gap (F3 never writes `AuditAction.MAP`, found while building `audit.py`). Lists concrete, undone follow-ups (F3 `MAP` logging, source-sentence grounding for deadlines, a deadline-specific confidence sub-score, re-validation on re-summarisation).
**Why it exists:** Per CLAUDE.md's "every AI decision logs model version + prompt version + inputs" + SR 11-7 — thinking through *how a wrong AI output could reach a human undetected* before it happens, and using that to scope what Day 34's audit trail should (and currently can't) show.

### `scripts/f4_mvp_demo.py`
**What it does:** Day 35 Deliverable — runs the full chain end-to-end for N F3 HIGH findings: `run_with_approval()` drafts via F4's ReAct agent + `create_task` (Day 33), auto-approves via `resolve_approval()` (Day 32), then prints the resulting `Task`'s full audit trail via `get_task_audit_trail`/`format_trail` (Day 34).
**Why it exists:** "F4 MVP: tasks from impact findings" — Days 1-34 built the chain piece by piece (F1-F3 ingest/summarise/map, F4 draft/approve/audit); this is the one script that demonstrates it as a single flow, for design-partner demos.
**Key design decision:** auto-approves every draft (`approved=True` unconditionally) — it's a demo of the chain working, not a substitute for Sarah's real review via `scripts/review_pending_tasks.py`.
**Run:** `python -m scripts.f4_mvp_demo [N]` (real Anthropic API calls; N defaults to 1). Verified on 1 real HIGH finding — printed F3 finding -> F4 draft (`prompt_version=v2`) -> HITL approval -> 6-entry audit trail (5 SUMMARISE runs + 1 TASK_CREATE).

### `docs/Incident-Response-Plan-v1.md`
**What it does:** Day 35 Product deliverable — a v1 process for AI-output incidents: detection layers (confidence/`review_flag`, eval CI gates, Day 33 tool validation, Day 32 HITL, and the "post-approval" gap), SEV-1/2/3 triage, SEV-1 response steps (contain via Day 33's `set_due_date`/`assign_owner`, investigate via Day 34's `show_task_audit_trail`, scope/notify/root-cause/remediate), and a 5 Whys RCA template matching `docs/RCA-Hallucinated-Deadline-v1.md`'s format.
**Why it exists:** Written proactively (no incidents yet) so the team knows what to do when one occurs — operationalizes CLAUDE.md's audit-logging requirement and SR 11-7's "ongoing monitoring + effective challenge" principles.

### `docs/Partner-Outreach-Followup-v1.md`
**What it does:** Day 35 Product deliverable — draft follow-up email templates building on Day 27's `Design-Partner-Profiles-v1.md`, now describing F4 (auto-drafted tasks, HITL approval, audit trail) as concrete new progress. Drafts only — not sent.
**Why it exists:** Week 5 exit gate asks for "at least 1 design partner reply or follow-up sent" — as of Day 35 this is an open item; these templates make sending one a one-step decision for the user rather than something to draft from scratch.

### `docs/F4-Audit-Report-v1.md`
**What it does:** Week 5 exit audit/model-risk report for F4 — same family as `FP-FN-Risk-Matrix.md` (F1/F2) and `RAGAS-Baseline-Report-v1.md` (F2 eval). Covers: model/prompt versions in use (verified live = `prompt_version=v2`), an `AuditLog` coverage table (TASK_CREATE/OVERRIDE captured; F1 INGEST not doc-scoped and F3 MAP never written are documented gaps), `evals/f4_eval.py` results (5/5 structural validity), an F4-specific FP/FN risk analysis (HIGH finding never drafted vs. task drafted with wrong content), SR 11-7 alignment table, and a consolidated list of 6 known follow-ups carried from Days 31-35.
**Why it exists:** F1 and F2 each got a dedicated audit-style doc; F4 built the audit trail mechanism itself (Day 34) but had no equivalent consolidated report. This is the single doc to hand an examiner about F4's risk posture, in the same format as F1/F2's.
**Day 36 note:** gaps #1 (F3 never writes MAP) and #2 (F1 INGEST not doc-scoped) from this report's Section 7 were closed on Day 36 — see `src/f1_ingest/ingest.py` and `src/f3_impact/classifier.py`.

### `docs/Audit-Log-Viewer-UX-v1.md`
**What it does:** Day 36 Product deliverable (KM #242) — wireframe for a filterable audit log viewer (by date range, actor, action), with row-level drill-down into a document's or task's full trail via `get_task_audit_trail`. Reuses `_summarize_entry()` (Day 34) for row text — no new formatting logic.
**Why it exists:** Before Day 36, `ingest`/`map` rows either didn't exist or weren't doc-scoped, so an "action" filter would show mostly blank columns. Day 36's logging changes make all 5 `AuditAction` values meaningful, making this viewer worth designing now.

### `scripts/override_rate_report.py`
**What it does:** Day 37 deliverable (KM #241, "Override rate dashboard"). `compute_override_rate()` queries `AuditLog` for `TASK_CREATE` rows (`payload_json["task_id"]`) and `OVERRIDE` rows (`payload_json["field"]`/`["task_id"]` from `src/f4_tasks/tools.py`, or `["rejected_task"]` from HITL rejections in `hitl_agent.py`), and returns `{total_tasks_created, tasks_edited, override_rate_pct, edits_by_field, rejected_drafts}`. `main()` prints a small report.
**Why it exists:** Turns the override-tracking already written by Day 32 (HITL rejection) and Day 33 (`assign_owner`/`set_due_date`/`link_regulation`) into the single "% of AI output a human had to change" number `docs/RAGAS-Baseline-Report-v1.md` references but never computed.
**Key design decision:** v1 does NOT compute "% summaries human-edited" — `AuditAction.OVERRIDE` is only ever written against `Task` rows, not `RegulatoryDocument.summary_json`, so there's nothing to query yet. Documented as a v2 gap in `docs/Override-Rate-Dashboard-v1.md`.
**Run:** `python -m scripts.override_rate_report`. Verified live: 3 tasks created, 0 edited (0.0% override rate), 1 HITL rejection.
**Tests:** `tests/test_override_rate.py` — 2 tests (in-memory SQLite): no-data zero case, and rate/field-breakdown/rejected-draft counting.

### `docs/Override-Rate-Dashboard-v1.md`
**What it does:** Day 37 Product deliverable (KM #241) — wireframe (created tasks / override rate / HITL rejection rate cards + edits-by-field bars) plus the real output of `scripts/override_rate_report.py`. Also documents Day 37's `langsmith_trace_id` wiring for F2 `SUMMARISE` and F4 `TASK_CREATE` rows and the resulting `| trace=<id>` line in `get_task_audit_trail`.
**Why it exists:** "Observability + override dashboard" deliverable — pairs the new LangSmith trace links with the override-rate metric in one document, same family as `docs/Audit-Log-Viewer-UX-v1.md`.
**Key limitation noted:** `.env`'s `LANGCHAIN_API_KEY` is a placeholder, so trace IDs are generated locally (real UUID7s, useful for DB correlation) but rejected by the LangSmith API (`403 Forbidden`) — they won't open in the LangSmith UI until a real key is configured.

### `scripts/weekly_compliance_report.py`
**What it does:** Day 38 deliverable (KM #263/#269, "compliance report template / weekly PDF export"). `build_report(days=7)` queries `AuditLog` for the trailing window and returns counts: documents ingested (`INGEST`), summaries by `payload["routing_decision"]` plus `payload["guardrail_warnings"]` count (`SUMMARISE`), HIGH-impact findings (`MAP`, `payload["impact_level"] == "high"`), and tasks created/edited/override-rate (reuses Day 37's `compute_override_rate`). `render_markdown()` formats it as a Markdown report; `main()` prints it.
**Why it exists:** Gives Mike/Sarah one weekly document answering "what did RegWatch see and do this week, and how much needed a human" — and surfaces Day 38's new guardrail-warning count as a citation-quality signal separate from the routing decision.
**Run:** `python -m scripts.weekly_compliance_report`. Verified live against current data (see `docs/Compliance-Report-Template-v1.md`).

### `docs/Compliance-Report-Template-v1.md`
**What it does:** Day 38 Product deliverable — documents the weekly report's sections and a real run of `scripts/weekly_compliance_report.py`.
**Key limitation noted:** v1 is Markdown only (no PDF); no email delivery; fixed 7-day window; counts only, no per-document detail.

### `docs/Enterprise-Pilot-Program-v1.md`
**What it does:** Day 39 Product deliverable (KM #267/268) — 90-day community bank pilot structure: onboarding flow (incl. PII redaction step), week-by-week timeline, success metrics (existing F1-F5 eval targets + Day 37 override rate + Day 38 guardrail-warning rate run against real bank data), and v1 out-of-scope items.
**Why it exists:** Days 1-38 ran against public/synthetic data. A pilot is the first time real client policy data (with real PII) enters the system — this doc is the offer document, and explicitly ties "safe to upload your policy library" to Day 39's `src/f3_impact/pii.py`.
**Key limitation noted:** regex-only PII redaction (no name/address NER) — flagged as a human-spot-check item during pilot onboarding, not a blocker.

### `docs/Notification-UX-v1.md`
**What it does:** Day 33 Product deliverable — draft email templates for "new task assigned" (sent when a `Task` is created via `resolve_approval(approved=True)`) and "task overdue" (sent when `due_date` has passed and `status != completed`), including the trigger condition, recipient, and subject/body for each.
**Why it exists:** `Task-Board-UX-v1.md` and `HITL-Approval-Workflow-v1.md` cover what happens up to and including task creation; nothing yet tells Sarah a task exists or is overdue. These are DRAFT templates only — per standing project constraint, RegWatch AI / Claude does not send emails on the user's behalf.

### `api/main.py`
**What it does:** Day 40 deliverable (KM #227 FastAPI). A read-only FastAPI app exposing F1-F5 data over HTTP: `/health`, `/f1/documents[/{id}]`, `/f2/review-queue`, `/f2/summaries`, `/f3/impact-results`, `/f3/policy-sections`, `/f4/tasks`, `/f5/audit-log`, `/f5/compliance-report`. Reads from the existing SQLite DB (via `src/database.get_session`) and `data/f3_indexes/*.json` — no new storage, no write endpoints.
**Why it exists:** Every prior feature's data lived behind direct DB/file access (dashboard, scripts). An API is the integration point for an external frontend, a partner's systems, or the Day 40 Docker/Render deploy — and it's the natural place to demo F1-F5 end to end (`docs/Demo-Walkthrough-Script-v1.md`).
**Key limitation noted:** read-only, no auth — fine for an internal demo, not for handling real client data (see `docs/Deployment-Guide-v1.md`).

### `tests/test_api.py`
**What it does:** Day 40 — 12 tests against `api/main.py` via FastAPI's `TestClient`, run in-process against the real dev DB + `data/f3_indexes/*.json` (read-only, same data the dashboard reads). Covers happy paths, filters, and error paths (404 for missing doc, 400 for unknown audit-log action).
**Run:** `python -m pytest tests/test_api.py -q` → 12 passed.

### `Dockerfile`, `.dockerignore`, `render.yaml`
**What they do:** Day 40 deliverable (KM #229 Docker). `Dockerfile` builds a `python:3.12-slim` image, installs `requirements.txt`, and runs `uvicorn api.main:app`. `.dockerignore` excludes `.git/`, `__pycache__/`, `.env`, logs, etc. `render.yaml` is a Render Blueprint pointing at the Dockerfile, with `ANTHROPIC_API_KEY`/`LANGCHAIN_API_KEY` marked `sync: false` (set manually in Render's dashboard, never committed).
**Why they exist:** CLAUDE.md names Render/Railway as the deploy target. These three files are what `docs/Deployment-Guide-v1.md` walks through to get `api/main.py` running on a public URL.
**Key limitation noted:** the Docker build was **not verified in this session** — no `docker` CLI in this dev environment. `docs/Deployment-Guide-v1.md` documents this and gives the verification steps to run locally. The image is also large (~3-4GB) because `requirements.txt` includes `sentence-transformers`/`torch` for F2/F3, which the API itself never imports.

### `docs/Deployment-Guide-v1.md`
**What it does:** Day 40 Product deliverable — runbook for running `api/main.py` locally with uvicorn, building/running the Docker image, and deploying to Render (blueprint) or Railway (Dockerfile auto-detect). Documents required env vars and the SQLite-on-ephemeral-filesystem caveat.
**Key limitation noted:** Docker build/deploy steps are written but unverified in this session (no Docker available) — framed as the user's next manual step.

### `docs/Demo-Walkthrough-Script-v1.md`
**What it does:** Day 40 Product deliverable — a ~5-minute script outline for an F1→F5 recorded walkthrough (e.g. Loom), section-by-section with what to show (dashboard, Swagger UI at `/docs`, specific endpoints) and what to say.
**Why it exists:** Ties together everything built Weeks 1-6 into a single narrative for demoing to a design partner/pilot prospect, referencing `docs/Enterprise-Pilot-Program-v1.md` and the Day 40 API as the integration story.

### `docs/Model-Card-v1.md`
**What it does:** Day 41 deliverable (KM #271/#273) — model card covering every AI/ML component (F1 IsolationForest, F2 `claude-sonnet-4-20250514`/embeddings/reranker, F3 impact classifier, F4 task agent): intended use, limitations, an SR 11-7 pillar mapping (development/validation/monitoring → existing eval gates, audit trail, override-rate dashboard, guardrails), and a self-assessed EU AI Act risk tier (Limited Risk — HITL design, no automated decisions about individuals).
**Why it exists:** SR 11-7 compliance requires a model card; a bank's vendor-risk team will request one before a pilot. Doubles as both a compliance and sales-enablement artifact.
**Key limitation noted:** EU AI Act classification is a self-assessment, not legal advice — flagged explicitly, with the specific feature change (customer-facing automated decisioning) that would require re-assessment.

### `docs/Pricing-v1.md`
**What it does:** Day 41 Product deliverable (KM #271) — 3-tier pricing (Monitor / Comply / Enterprise) mapped to F1-F5 feature availability, building on `docs/Enterprise-Pilot-Program-v1.md`. Includes the directional reasoning behind the indicative price ranges and an explicit "not priced yet" list (add-ons, discounts, upgrade paths).
**Why it exists:** Answers the Day 41 GTM interview question ("How would you price RegWatch for a community bank pilot?") with a concrete artifact rather than a verbal answer.

### `src/f4_tasks/notifications.py`
**What it does:** Day 42 deliverable (KM "Review" — "email notification system"). Implements the two templates from `docs/Notification-UX-v1.md` as `render_new_task_notification(task)` and `render_overdue_notification(task)`, each returning `{to, subject, body}`. `write_to_outbox(notification, task_id, kind)` appends a JSON line to `logs/notifications.jsonl`.
**Why it exists:** This is the generation + queueing half of "notification system" — per the standing project constraint, RegWatch AI / Claude does not send emails on the user's behalf. The outbox is the seam where a real transactional-email integration would plug in later.

### `src/f4_tasks/hitl_agent.py` (Day 42 edit)
**What changed:** `finalize()`'s approved path now calls `render_new_task_notification` + `write_to_outbox` right after `Task(status=open)` is written, queuing a "new task assigned" notification for the task's owner.

### `scripts/check_overdue_tasks.py`
**What it does:** Day 42 — scans `Task` rows for `due_date < today` and `status != completed`, and queues a "task overdue" notification (`render_overdue_notification`) for each into the outbox.
**Key limitation noted:** no "already notified" dedup — re-running re-queues a notification for every still-overdue task. Acceptable for v1 (outbox only, nothing is actually sent); would need addressing before wiring a real send path.
**Run:** `python -m scripts.check_overdue_tasks`

### `scripts/export_tasks.py`
**What it does:** Day 42 deliverable (KM "Review" — "management task export"). Exports all `Task` rows to `exports/tasks.csv` (stdlib `csv`, gitignored output dir).
**Key limitation noted:** CSV only — PDF would need `reportlab` (currently commented out in `requirements.txt`, not installed), flagged as a v2 add rather than installed speculatively.
**Run:** `python -m scripts.export_tasks [output_path]`

### `tests/test_e2e_pipeline.py`
**What it does:** Day 43 deliverable (KM #227 — FastAPI end-to-end, "RSS ingest → summary → impact → task → audit report"). One in-memory SQLite test exercises the full F1→F2→F3→F4→F5 chain in a single run: writes the F1 `AuditLog(INGEST)` row a real ingest would produce, calls `summarise_document` (Day 8) with only `_call_claude` mocked, runs `classify_matches`/`log_map_decisions` (Day 22) for real, drives the Day 31-35 LangGraph HITL graph through `build_graph`/`run_with_approval`/`resolve_approval`, confirms Day 42's notification outbox gets the "new task assigned" entry, and finishes with `weekly_compliance_report.build_report` (Day 36) asserting `documents_ingested`, `high_findings`, `tasks_created`, and `guardrail_warnings` all reflect the single document processed.
**Why it exists:** Days 2-42 each tested one feature in isolation against an in-memory or real DB. Nothing previously asserted that F1's output is shape-compatible with F2's input, F2's with F3's, etc., end to end — this is the test that would catch a schema or contract drift between features.
**Key limitation noted:** the only mocked boundary is the Anthropic API call inside `_call_claude` (no network, no API cost). F1's actual RSS/HTTP fetch is out of scope here — covered separately by `tests/test_f1_integration.py` (`@pytest.mark.slow`).
**Run:** `python -m pytest tests/test_e2e_pipeline.py -v` → 1 passed.

### `src/f2_summarise/summariser.py` (Day 44 edit)
**What changed:** `_call_claude` now returns a 3-tuple `(text, trace_id, token_usage)`, reading `response.usage.input_tokens`/`output_tokens` (defaulting to 0/0 if absent, e.g. in test doubles). `summarise_document` stores `input_tokens`/`output_tokens` on the `AuditLog(SUMMARISE)` payload alongside the existing `model`/`prompt_version`.
**Why it exists:** Day 44 deliverable (KM #239 — cost dashboard). Token counts are the input to `scripts/cost_dashboard.py`'s $/query calculation. Only the success path logs tokens; the both-models-failed path is unchanged.

### `scripts/cost_dashboard.py`
**What it does:** Day 44 deliverable (KM #239). Reads `AuditLog(SUMMARISE)` rows, sums `input_tokens`/`output_tokens` per model, and converts to USD using a hardcoded `PRICING_PER_MTOK` table (Sonnet 4: $3/$15 per MTok in/out; Haiku 4.5: $1/$5). Reports total cost and cost-per-query, overall and by model.
**Why it exists:** SR 11-7 / production-ops visibility into LLM spend — "what does RegWatch AI cost to run per document summarised."
**Key limitation noted:** v1 only covers F2 (the only feature making per-document Anthropic API calls with usage data). F3's reranker and F4's LangGraph agent don't log token usage, so they report $0. Pre-Day-44 `AuditLog(SUMMARISE)` rows have no token data and are excluded from the cost-per-query average (counted separately as `total_summarise_logs` vs `queries_with_token_data`) rather than counted as $0.
**Run:** `python -m scripts.cost_dashboard`

### `evals/final_eval_report.json`
**What it does:** Day 44 deliverable (KM #258 — final RAGAS eval). Runs `evals/ragas_eval.run_eval` against the full 50-entry golden set (`fixtures/golden/summaries.json`) and saves the result with explicit notes on scope.
**Key limitation noted:** the v2.2 roadmap names a 100-example golden set; the actual hand-labeled golden set has 50 entries, and only 20 of those have a matching `SUMMARISED` document with `summary_json` in the dev DB. Results (faithfulness 0.783) are therefore identical to the Day 18 baseline (`evals/baseline_report.json`) — entries 21-50 all fall in `summaries_missing`. Reported as an open gap rather than re-scoped silently; see `docs/Case-Study-v1.md` and `docs/SD1-System-Design-v1.md` §6.

### `docs/SD1-System-Design-v1.md`
**What it does:** Day 44 deliverable (KM #239/#258 — "SD1: RegWatch architecture, all 5 features + data flow"). Portfolio-oriented system design doc: end-to-end data flow diagram, data model summary, 7 key design decisions with rationale, an eval/governance table, and an explicit "Honest Gaps" section.
**Why it exists:** `docs/ARCHITECTURE.md` is a day-by-day build log (good for "how did this evolve"); SD1 is the synthesized "how does this system work as a whole" doc for an external reader (interviewer, design partner).

### `docs/Portfolio-Page-v1.md`
**What it does:** Day 44 deliverable ("Portfolio page live"). Markdown content for a single public-facing portfolio page — problem statement, pipeline table, "what makes this different," headline metrics, and links to the case study and SD1.
**Key limitation noted:** content only — no frontend/site exists yet to host it (the project's `/frontend/src/` referenced in CLAUDE.md hasn't been built). Framed as page *content*, ready to drop into a site when one exists.

### `tests/test_cost_dashboard.py`
**What it does:** Day 44 — 3 tests for `scripts/cost_dashboard.py` against in-memory SQLite: cost/token aggregation by model, skipping pre-Day-44 rows with no token data, and the no-logs case.
**Run:** `python -m pytest tests/test_cost_dashboard.py -q` → 3 passed.

### v1.0 — Day 45 (Integration + Portfolio, final day of Week 7)
**What happened:** Git repo initialized, `.gitignore` verified to exclude `.env`/`*.db`/`logs/`/`.claude/`, all 221 tracked files committed as the root commit, tagged `v1.0`. `uvicorn api.main:app` run locally on port 8001 as a smoke test against every documented endpoint (`/health`, `/f1/documents`, `/f2/review-queue`, `/f3/impact-results`, `/f4/tasks`, `/f5/compliance-report`) — all returned live data from the dev DB. `docs/Case-Study-v1.md` updated with the real 90-day compliance-report numbers (19 documents ingested, 54 HIGH findings, 3 tasks created, 0% override rate).
**Key limitation noted:** this was a local smoke test, not a public deployment — no live URL exists, and the Render/Railway Docker deploy in `docs/Deployment-Guide-v1.md` remains unverified end-to-end (no Docker CLI in this build environment). See `notes/Day-45-Integration.md`.

---

## Data Flow (Day 2)

```
setup_db.py
    → create_db_and_tables()     creates Agency, RegulatoryDocument, AuditLog tables
    → seed_agencies()            writes 6 Agency rows

ingest.py
    → loads Agency rows from DB
    → for each agency:
        fetch_feed() or fetch_fr_api()
            → HTTP GET feed/API URL
            → parse entries into RegulatoryDocument objects
            → classify_doc_type(title)        keyword → DocType enum
            → compute_hash(title, url)        SHA-256 fingerprint
        is_duplicate(hash)                    DB lookup
        if not duplicate → session.add(doc)   save to RegulatoryDocument table
        AuditLog entry written per agency run
```

---

## Environment Variables

| Variable | Required by | Purpose |
|----------|-------------|---------|
| `DATABASE_URL` | `src/database.py` | DB connection string |
| `ANTHROPIC_API_KEY` | F2 (Day 8) | LLM API access |
| `LANGCHAIN_API_KEY` | F5 (Day 36) | LangSmith tracing |
| `LANGCHAIN_PROJECT` | F5 | LangSmith project name |

---

## Dependency Decisions

| Package | Version | Why this one |
|---------|---------|--------------|
| `sqlmodel` | 0.0.21 | One class = DB table + Pydantic schema. Less code than SQLAlchemy alone. |
| `python-dotenv` | 1.0.1 | Standard env-var loading. Zero risk, widely audited. |
| `feedparser` | 6.0.11 | De-facto standard RSS parser. Handles malformed feeds gracefully. |
| `httpx` | 0.27.0 | Async HTTP. Needed for Federal Register API (async-first, unlike requests). |
| `pytest` | 8.2.2 | Standard Python test runner. |
| `pytest-asyncio` | 0.23.7 | Allows async test functions (needed for httpx-based tests). |
| `fastapi` | 0.136.3 | Day 40 — API layer over F1-F5 data; auto-generates OpenAPI/Swagger docs for the demo. |
| `uvicorn` | 0.49.0 | Day 40 — ASGI server to run `api.main:app`, locally and inside the Docker image. |
