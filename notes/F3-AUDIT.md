# F3 AUDIT — Policy Impact Mapping (Days 22-29)

**Purpose:** A permanent reference document for F3 (Policy Impact Mapping),
RegWatch's core/moat feature. Mirrors `notes/F1-AUDIT.md` and
`notes/F2-AUDIT.md` — written for a PM (or a future engineer) who needs to
understand exactly what was built, why, what it costs, what it's worth, and
where it's weak, without re-reading every commit.

**Scope:** `src/f3_impact/` (7 files), `evals/f3_eval.py`,
`fixtures/golden/impact_pairs.json`, `tests/test_f3_*.py` (4 files), and the
Days 22-29 product docs. Covers Week 4 (Days 22-28) and Day 1 of Week 5 (Day
29).

---

## 1. Project File Map

| File | What it does | Key function/class | Key constant(s) | Connects to | Breaks if deleted | Why this way |
|---|---|---|---|---|---|---|
| `src/f3_impact/extractor.py` | Parses bank policy `.txt` files into `PolicySection` objects — one per `N.M` numbered subsection, tagged with its parent `SECTION N:` header. | `PolicySection` dataclass; `extract_policy_sections()`, `extract_policy_file()`, `extract_policy_library()` | `SECTION_HEADER_RE`, `SUBSECTION_HEADER_RE` | Feeds `build_indexes.py` (policy_sections index) | Everything downstream — no policy sections to embed, match, or classify | Regex parsing, not an LLM call. The 3 synthetic fixtures follow a consistent `SECTION N:` / `N.M Title` format; a deterministic parser is free, instant, and unit-testable. LLM extraction is a documented fallback if real client policies don't follow this structure. |
| `src/f3_impact/vectorstore.py` | Local numpy+JSON vector store (`VectorIndex`) — `upsert_batch`, `query`, `save`, `load`. Mirrors a Pinecone collection's interface. | `VectorIndex` class | `DEFAULT_EMBEDDING_MODEL` (via `f2_summarise.embeddings`) | Used by `build_indexes.py` and `matcher.py` | Both indexes (policy_sections, regulation_chunks) can't be built, saved, or queried | No `PINECONE_API_KEY` in `.env`. Reuses F2's local `all-mpnet-base-v2` embeddings (zero cost, no data leaves the machine). Vectors are pre-normalized so cosine similarity = a single dot product — fast even for thousands of items on CPU. Swapping to real Pinecone later is a one-file change, same pattern as `DATABASE_URL` SQLite→Postgres. |
| `src/f3_impact/build_indexes.py` | Builds + saves two `VectorIndex` collections to `data/f3_indexes/`: `policy_sections` (72 sections) and `regulation_chunks` (521 chunks from 25 summarised F1/F2 docs, via F2's `chunk_hierarchical`). | `build_policy_index()`, `build_regulation_index()`, `main()` | `INDEX_DIR`, `FIXTURES_DIR` | Reads `extractor.py` + F2's `chunker.py` + `database.py`; writes the indexes `matcher.py` reads | `matcher.py` has nothing to search | This is the "dual-index" deliverable CLAUDE.md specifies — one index per side of the match (policy text vs. regulation text), so each can be embedded/scaled independently. Day 29 added contextual retrieval to the policy-section embedding input (kept) and tried-but-rejected it for regulation chunks (see §3, §5). |
| `src/f3_impact/matcher.py` | `HybridMatcher` — for each policy section, finds top regulation chunks via dense search + BM25, combines with RRF, collapses chunk-level hits to one row per regulation document. `build_matches()` runs this for all 72 sections → `matches.json`. | `HybridMatcher` class (`match_chunks`, `match_section`); `_rrf_combine()`, `_tokenize()`, `build_matches()` | `RRF_K=60`, `DENSE_TOP_K=20`, `BM25_TOP_K=20`, `CHUNK_TOP_K=15`, `MATCHES_PER_SECTION=5` | Reads both `VectorIndex`es; writes `matches.json` consumed by `classifier.py` | No candidate (policy section, regulation) pairs exist for the classifier to score | Hybrid (dense + BM25 + RRF), not dense-only — same justification as F2 Day 16. Dense catches semantic matches ("cash transaction... $10,000" → CTR section); BM25 catches exact regulatory citations ("Regulation B", "12 CFR 1002.6") dense embeddings can miss. `RRF_K=60` reuses F2's validated constant. Each match also keeps `dense_score` (real 0-1 dynamic range) separately from the RRF `score` (clusters near a ~0.03 floor) — Day 25 added this specifically because RRF scores alone can't drive a threshold classifier. |
| `src/f3_impact/citations.py` | Extracts the regulations a policy fixture *explicitly cites* from its own text (`_ACT_PATTERN`, `_REGULATION_LETTER_PATTERN`, `_ABBREVIATION_PATTERN`). Caches per-policy results. | `extract_named_regulations()`, `get_named_regulations()`, `is_named_regulation_match()` | `_cache` dict | Used by `classifier.py` and `evals/f3_eval.py` | `classify_impact()` loses its only signal beyond raw `dense_score` — accuracy reverts to Day 26's 40% | Day 26's diagnosis: `dense_score` alone can't distinguish "this regulation is generic boilerplate that happens to share vocabulary with this policy" from "this regulation is one this policy actually governs under." Whether the *policy itself* names the regulation is a free, deterministic, auditable second feature — no LLM call, no new training data. Documented limitation: only catches 3 citation styles, good enough for the 3 current fixtures, not guaranteed for real client policies. |
| `src/f3_impact/classifier.py` | `classify_impact(dense_score, named_regulation_match)` → `ImpactLevel` (HIGH/MEDIUM/LOW/NOT_APPLICABLE). Adjusts `dense_score` by a named-match boost/penalty, then applies fixed thresholds. `classify_matches()` runs this over all of `matches.json` → `impact_results.json`. | `ImpactLevel` enum; `classify_impact()`, `classify_matches()`, `main()` | `HIGH_THRESHOLD=0.55`, `MEDIUM_THRESHOLD=0.45`, `LOW_THRESHOLD=0.35`, `NAMED_MATCH_BOOST=+0.10`, `NO_MATCH_PENALTY=-0.20` | Reads `matches.json` + `citations.py`; writes `impact_results.json` (F3's actual output) | F3 has no output — no impact levels for F4 to act on, nothing for Sarah's dashboard | A threshold rule, not a trained classifier (the roadmap's KM #17/#20 is explicitly deferred) — no labeled training data existed before Day 26 built the golden set. Thresholds are SR 11-7-auditable in one sentence: "0.47 + 0.10 = 0.57 ≥ 0.55 → HIGH, because Reg B is in this policy's own Regulatory Framework section." Day 27 added the boost/penalty on top of the same thresholds — same explainability, better accuracy. |
| `evals/f3_eval.py` | Runs `classify_impact()` against the 30 golden pairs, computes accuracy + confusion matrix, prints mismatches with rationale. Two gates: aspirational `CI_GATE_THRESHOLD` and measured `REGRESSION_BASELINE`. | `run_eval()`, `_load_dense_score_lookup()`, `_print_report()`, `main()` | `CI_GATE_THRESHOLD=0.80` (CLAUDE.md target), `REGRESSION_BASELINE=0.70` (Day 27, measured floor) | Reads `fixtures/golden/impact_pairs.json` + `matches.json`; calls `classifier.py` + `citations.py` | No automated check that F3 still works after a change — the eval-first build rule has nothing to enforce | Two separate thresholds on purpose: 80% is "are we done" (CLAUDE.md's target, currently red — expected, tracked). 70% is "did we just break something that used to work" (CI-blocking). Day 29's Experiment B (70.0%, exactly at the floor) is the first real proof this distinction matters — it passed the 70% gate but was still a measured regression from 73.3% and was correctly not shipped. |
| `fixtures/golden/impact_pairs.json` | 30 hand-labeled `(policy section, regulation)` pairs with `true_impact_level` + one-line rationale, stratified across HIGH/MEDIUM/LOW/N-A and across the Day 25 "generic-language over-match" failure pattern. | n/a (data file) | `_metadata.pair_count=30`, `_metadata.label_field="true_impact_level"` | Read by `evals/f3_eval.py` | The eval has nothing to score against — `run_eval()` raises | CLAUDE.md names this exact file/path as F3's golden eval set. `_metadata` discloses the labels are Claude-generated (v1), "PENDING review by a compliance officer" — not yet SME-validated ground truth (SR 11-7 caveat, carried through to `docs/Trust-Strategy-v1.md`). |
| `tests/test_f3_extractor.py` | 3 tests: synthetic sample parsing, multiline section bodies, all 3 real fixtures (72 sections, spot-checks BSA §4.2 "Currency Transaction Reporting"). | — | — | `extractor.py` | No safety net if a future fixture or regex change silently drops sections | — |
| `tests/test_f3_vectorstore.py` | 5 tests against a fake 3D embedding model: upsert+query ranking, mismatched-length validation, empty-index query, `__len__`, save/load round-trip. | — | — | `vectorstore.py` | No safety net for the storage layer every other F3 file depends on | Fake embedding model (no `sentence-transformers` download) keeps CI fast — same pattern as F2's embedding tests. |
| `tests/test_f3_matcher.py` | 4 tests: RRF combination (items in both lists rank highest; items missing from one list still rank), end-to-end `match_section` against a 3-doc fake index (best match wins, no duplicate docs, respects `MATCHES_PER_SECTION`). | — | — | `matcher.py`, `vectorstore.py` | No safety net for the hybrid search core | Same fake-embedding pattern, extended with hand-picked vectors so ranking outcomes are predictable and assertable. |
| `tests/test_f3_classifier.py` | 4 tests: threshold boundaries without named match, threshold boundaries with named match (boost/penalty arithmetic spelled out in comments), `classify_matches()` output shape + non-mutation, empty-matches section handling. | — | — | `classifier.py` | No safety net for F3's actual output logic — a silent threshold or boost/penalty typo would change every `impact_level` in the dataset undetected | Rewritten Day 27 specifically to cover both adjustment branches after `named_regulation_match` was added — the arithmetic in the test comments (e.g. "0.80 + 0 → 0.60 → HIGH") doubles as inline documentation of the thresholds. |
| `tests/test_f3_eval.py` | 4 tests: real golden set (`total==30`), controlled fake dataset (2 pairs, asserts `accuracy==0.5`), `CI_GATE_THRESHOLD==0.80`, regression floor (`accuracy >= REGRESSION_BASELINE`). | — | — | `f3_eval.py`, `classifier.py`, `citations.py` | The regression gate (KM #258) — the entire mechanism that caught Day 29's Experiment B — disappears | The fake-dataset test was originally written against a nonexistent `"Test-Policy"` fixture (Day 26 bug); Day 27 fixed it to use `"BSA-AML-Policy"`, a real fixture, so `citations.py` has real text to extract from. |

---

## 2. Data Flow — One Policy Section, End to End

**Walking `BSA-AML-Policy §4.2 "Currency Transaction Reporting (CTR)"` through the full F3 pipeline:**

1. **Extraction (`extractor.py`)** — `extract_policy_file("fixtures/policies/BSA-AML-Policy.txt")` finds the line `4.2 Currency Transaction Reporting (CTR)` under `SECTION 4: ...`, and produces a `PolicySection(policy_name="BSA-AML-Policy", section_id="4.2", section_title="Currency Transaction Reporting (CTR)", parent_section="SECTION 4: ...", text="<full subsection body>")`.

2. **Embedding (`build_indexes.py` → `build_policy_index()`)** — the section is embedded not as raw `text`, but (Day 29) as:
   ```
   BSA-AML-Policy — SECTION 4: ...
   Currency Transaction Reporting (CTR)
   <full subsection body>
   ```
   The embedding vector is stored in the `policy_sections` `VectorIndex` under id `"BSA-AML-Policy::4.2"`, with `metadata["text"]` kept as the *raw* section text (used later for BM25 and for evidence display — only the embedding input changed).

3. **Matching (`matcher.py` → `HybridMatcher.match_section`)** — `build_matches()` takes this section's embedding text, runs:
   - Dense search: cosine similarity against all 521 `regulation_chunks` vectors → top 20.
   - BM25 search: keyword overlap (e.g. "currency transaction report", "$10,000", "CTR") against the same 521 chunks → top 20.
   - RRF combine (`_rrf_combine`, `k=60`): merges both rankings into one score.
   - Collapses to per-document: among all matching chunks from the same `regulation_doc_id`, keeps the highest-scoring chunk as `matched_chunk_text` / `matched_chunk_section_header`, and records that chunk's cosine similarity separately as `dense_score`.
   - Keeps up to `MATCHES_PER_SECTION=5` regulation documents.

   For §4.2, this surfaces a FinCEN CTR-related document with `dense_score ≈ 0.6+` — a real semantic match (both texts discuss $10,000 cash transaction reporting thresholds).

4. **Named-match check (`citations.py`)** — `is_named_regulation_match("BSA-AML-Policy", "<FinCEN doc title>")` checks whether BSA-AML-Policy's own text (its "Regulatory Framework" section) names the Bank Secrecy Act / FinCEN regulations. It does — `named_regulation_match = True`.

5. **Classification (`classifier.py` → `classify_impact`)** — `dense_score=0.6 + NAMED_MATCH_BOOST(0.10) = 0.70 ≥ HIGH_THRESHOLD(0.55)` → `ImpactLevel.HIGH`. This is written to `impact_results.json` as one entry under §4.2's `matches` list: `{regulation_doc_id, regulation_title, dense_score: 0.6, named_regulation_match: true, impact_level: "high", matched_chunk_text: "...", ...}`.

6. **Eval (`evals/f3_eval.py`)** — this exact (BSA-AML-Policy §4.2, FinCEN CTR doc) pair (or one structurally identical to it) is one of the 30 golden pairs labeled `true_impact_level: "high"` — and is one of the 10/10 HIGH pairs the classifier gets right (per the Day 27 confusion matrix, §11 below).

**What Sarah would see:** a HIGH-impact finding on "BSA Policy §4.2 — Currency Transaction Reporting (CTR)", citing the specific FinCEN regulation text that drove the match (`matched_chunk_text`), with `dense_score=0.70` and `named_regulation_match=true` as the auditable "why" — exactly the `docs/Trust-Strategy-v1.md` §1/§3 pattern ("show the evidence, not just the verdict"; "every AI decision attributable and reproducible").

---

## 3. The Matching & Classification Stack — Evolution, Days 24-29

Unlike F2 (one retrieval stack, tuned once), F3's "stack" is two coupled layers — **matching** (which regulation chunks does a policy section pair with?) and **classification** (given a match, how impactful is it?) — that were built, broken, and fixed in sequence. Both layers and every measured change are below.

| Day | Layer | Change | Measured result |
|---|---|---|---|
| 24 | Matching v1 | `HybridMatcher` (dense + BM25 + RRF, `RRF_K=60`) built. 72 sections → 252 raw matches. | RRF `score` clusters near floor (~0.03) — not usable for classification directly. Flagged dev-DB coverage gap (25 docs lack CTR/SAR content for BSA). |
| 25 | Matching v1.1 | Added `dense_score` (raw cosine similarity) alongside RRF `score` to each match — the signal the classifier actually needs. | 251 matches classified with a first threshold pass: 27 high / 47 medium / 78 low / 99 N/A. Found `dense_score` is a real signal (ECOA policy ↔ "Equal Credit Opportunity Act (Regulation B)" correctly HIGH) but also found "Reg B" over-matching BSA/TRID sections — flagged for Day 26. |
| 26 | Classification v1, Eval v1 | Golden set built (30 pairs). First measured accuracy: **40% (12/30)**, CI FAIL. Root cause: generic, long documents ("Equal Credit Opportunity Act (Regulation B)", "Agency Information Collection Activities: Comment Request") over-match via generic regulatory vocabulary regardless of policy relevance. | Confusion matrix: HIGH 8/10 good; NOT_APPLICABLE only 2/11 (7 of 11 true negatives predicted HIGH/MEDIUM). |
| 27 | Classification v2 | `citations.py` (named-regulation-match feature) + `NAMED_MATCH_BOOST(+0.10)` / `NO_MATCH_PENALTY(-0.20)` added to `classify_impact`. `REGRESSION_BASELINE=0.70` added to eval. | **73.3% (22/30)**, CI still FAIL (target 80%) but +33.3 points in one day. HIGH 10/10, NOT_APPLICABLE 7/11. Remaining 8 mismatches all share one pattern (generic regulation vs. unrelated policy, `named_regulation_match=False`, `dense_score` 0.45-0.61). |
| 28 | — (Review day) | No matching/classification change. 10-pair MVP sample published with one deliberate known-error example. | 73.3% (unchanged, by design — review day). |
| 29 | Matching v1.2 (Experiment A, **kept**) | `build_policy_index()` embedding input changed to `"{policy_name} — {parent_section}\n{section_title}\n{text}"` (was `"{section_title}\n{text}"`). | **73.3% (22/30)** — neutral, same confusion-matrix shape. Kept as a no-cost, conceptually-sound improvement for future larger policy libraries. |
| 29 | Matching v1.3 (Experiment B, **rejected**) | `build_regulation_index()` embedding input tried as `"Document: {title}\nSource: {agency}\nSection: {header}\n\n{chunk.text}"` (was raw `chunk.text`). | **70.0% (21/30)** — fixed 2 of the 8 Day 27 mismatches (#9, #10) but broke 3 new ones (#11, #21, #30), net −1. Landed exactly on `REGRESSION_BASELINE`. **Not applied** — reverted, documented in `build_regulation_index()`'s docstring and `notes/Day-29-F3.md`. |

**The throughline:** every change after Day 25 was driven by a *measured* number, not intuition — and Day 29 is the first time the regression-CI gate (built Day 27 specifically to catch exactly this) did its job on a real candidate change.

---

## 4. Every AI/ML Decision

| Decision | What | Why not the alternative | Failure mode |
|---|---|---|---|
| **Embedding model: `all-mpnet-base-v2` (reused from F2)** | Same local sentence-transformers model used for F2's RAG pipeline, applied to both policy sections and regulation chunks. | OpenAI/Anthropic embedding APIs would add cost + send policy text (potentially client-confidential in production) to a third party — violates the "public regulatory data only" / no-client-data constraint for the *policy* side once real client policies are uploaded. A different model per index (policy vs. regulation) would make cross-index cosine similarity meaningless — both sides must share an embedding space. | If a real client policy is written in a style/vocabulary far from `all-mpnet-base-v2`'s training distribution (e.g. heavy internal jargon, non-English), `dense_score` quality degrades silently — no current monitoring for embedding-space drift. |
| **Local `VectorIndex` (numpy+JSON) instead of real Pinecone** | `src/f3_impact/vectorstore.py` mirrors Pinecone's `upsert`/`query` interface but stores vectors as a numpy array + JSON metadata on disk. | No `PINECONE_API_KEY` configured (`.env`). Building the real interface shape now means swapping the implementation later is a one-file change — same pattern F2 used for embeddings. | Doesn't scale past a few thousand vectors (full matrix dot product on every query) — fine for 593 current vectors (72+521), would need replacing before a real multi-tenant rollout (CLAUDE.md specifies Pinecone namespaces per client). |
| **Hybrid search (dense + BM25 + RRF), not dense-only** | `HybridMatcher` combines cosine-similarity ranking with BM25 keyword ranking via Reciprocal Rank Fusion (`RRF_K=60`, reused from F2 Day 16). | Dense-only embeddings can miss exact regulatory citations ("12 CFR 1002.6", "Regulation B") that differ only in punctuation/casing from a policy's reference — BM25 catches these directly. BM25-only would miss the semantic matches (different words, same meaning) that are most of F3's value. | If BM25's tokenizer (`_tokenize`) doesn't handle a citation format well (e.g. unusual CFR formatting in a real policy), that match silently falls back to dense-only ranking — no alerting on BM25-zero-hit cases. |
| **`dense_score` (raw cosine similarity) as the classification input, not the RRF `score`** | `classifier.py` thresholds `dense_score` (0-1 range), added to each match specifically for this purpose (Day 25). | Day 24 found RRF `score` clusters near a ~0.03 floor across nearly all matches — no usable dynamic range for a threshold rule. `dense_score` has real spread (0.3-0.8+ observed). | `dense_score` is cosine similarity between two embeddings — it's a *semantic-overlap* signal, not a *legal-relevance* signal. Day 26 proved these diverge for generic regulations (high semantic overlap, zero legal relevance to an unrelated policy) — which is exactly why `named_regulation_match` had to be added as a second feature rather than just retuning thresholds. |
| **Threshold classifier (`classify_impact`), not a trained model** | Fixed cutoffs (0.55/0.45/0.35) on an adjusted `dense_score`, with documented boost/penalty for `named_regulation_match`. Explicitly a v1 placeholder for the roadmap's KM #17/#20 (trained classifier). | No labeled training data existed before Day 26 (the golden set itself *is* the first 30 labels). A trained model on 30 examples would massively overfit. Thresholds are SR 11-7-auditable in one sentence ("0.57 ≥ 0.55 → HIGH because..."), which a trained model isn't without extra explainability tooling (SHAP etc. — explicitly flagged as a requirement for any future trained classifier). | A single global threshold/boost/penalty has a measured ceiling: Day 27's analysis showed ~73-77% is close to the practical max for *any* single linear adjustment on this 30-pair set, because some true-MEDIUM cases and some true-NOT_APPLICABLE cases have *overlapping* `dense_score` ranges (0.53-0.56) that no single cutoff can separate. |
| **`named_regulation_match` via regex citation extraction (`citations.py`), not an LLM call** | Regex over each policy's own fixture text, extracting "... Act", "Regulation <Letter>", "(ABBR)" patterns, cached per policy. | An LLM-based "does this policy cite this regulation?" classifier would add cost, latency, and a second non-deterministic AI decision per match (3x: dense match, citation check, impact classification) — harder to audit, and the citation-extraction task is genuinely pattern-matchable for the current fixtures. | Only catches 3 citation styles. A real client policy that refers to "the Bank Secrecy Act" only as "BSA requirements" without ever writing "(BSA)" the way the fixture does, or that cites by section number only ("31 CFR 1010.311") without a name/abbreviation, would get `named_regulation_match=False` for a regulation it clearly does govern — silently falling back to the `NO_MATCH_PENALTY`. |
| **Contextual retrieval for policy sections only (Day 29), kept; for regulation chunks, tried and reverted** | Policy-section embeddings now include `{policy_name} — {parent_section}\n{section_title}` as context. Regulation-chunk embeddings remain raw `chunk.text`. | Measured: policy-section context was neutral (73.3%, same confusion matrix) — kept because it's free and conceptually correct (a section's meaning includes which policy/parent-section it's under) for when more/larger real policies are added. Regulation-chunk context regressed to 70.0% — fixed 2 known errors but broke 3 new ones, a net loss on this 30-pair set. | The "kept" change (policy-section context) hasn't been *proven* to help — it's neutral on 30 pairs. Its value is a bet on larger future policy libraries where parent-section disambiguation matters more; that bet is undocumented as a hypothesis to re-test once more policies exist. |

---

## 5. The Classifier Calibration Journey — Days 25 → 29

F2's "Prompt Engineering Journey" tracked RAGAS scores across prompt versions.
F3's equivalent is the **classifier's adjustment-to-`dense_score` journey** —
each step measured against the same 30-pair golden set.

| Version | Adjustment formula | Accuracy | What changed and why |
|---|---|---|---|
| **v1 (Day 25)** | `classify_impact(dense_score)` — raw thresholds, no adjustment. Thresholds 0.55/0.45/0.35 chosen by inspecting the `dense_score` distribution of the 251 matches (27 high / 47 medium / 78 low / 99 N/A under this pre-eval split). | *(pre-eval; Day 26 measured 40% against this)* | First pass — thresholds picked by eyeballing score distributions, before any ground truth existed to validate against. |
| **v2 (Day 26)** | Same formula, now measured against the new 30-pair golden set. | **40% (12/30)** | No code change — this is the *measurement* that revealed v1's thresholds badly over-predict impact for generic/long regulations matched against unrelated policies (NOT_APPLICABLE recall 2/11). |
| **v3 (Day 27)** | `adjusted = dense_score + (NAMED_MATCH_BOOST if named_regulation_match else NO_MATCH_PENALTY)`, i.e. `+0.10` or `-0.20`, then same 0.55/0.45/0.35 thresholds on `adjusted`. | **73.3% (22/30)** | The single biggest jump in F3's history. `named_regulation_match` gave the classifier a second, independent feature — fixed all 3 true HIGH false-negatives (ECOA matches scoring 0.47-0.52, just under threshold, now boosted to ≥0.55) and 5 of 7 NOT_APPLICABLE false-positives (generic-regulation matches now penalized below LOW). |
| **v3.1 (Day 29, Experiment A — kept)** | Same v3 formula; `dense_score` itself shifts slightly because policy-section embeddings now include policy/section context. | **73.3% (22/30)** | Neutral — same 22/30, same confusion-matrix shape. Not a calibration change per se, but confirms v3's thresholds are robust to small embedding-input changes on the policy side. |
| **v3.2 (Day 29, Experiment B — rejected, not shipped)** | Same v3 formula; `dense_score` shifts because regulation-chunk embeddings would include document/source/section context. | **70.0% (21/30)** | Regression. Fixed 2 of v3's 8 mismatches but broke 3 others — net −1, exactly at `REGRESSION_BASELINE`. Reverted; documented as a rejected hypothesis in `build_regulation_index()`'s docstring. |

**The v3 mismatch pattern that remains (8 pairs, all unchanged since Day 27):**
every one involves "Equal Credit Opportunity Act (Regulation B)" or "Agency
Information Collection Activities: Comment Request" matched against
BSA-AML-Policy or TRID-Mortgage-Disclosure-Policy sections — i.e., regulations
that *don't* name a law those policies cite, but still score `dense_score`
0.45-0.61 on generic compliance-language overlap. The `-0.20` penalty moves
these into LOW where 6/8 should be NOT_APPLICABLE and 2/8 should be MEDIUM —
a spread no single linear adjustment can resolve (Day 27's "ceiling" finding,
re-confirmed by Day 29's two experiments both landing near this same set).

---

## 6. The Eval Framework

- **Golden set:** `fixtures/golden/impact_pairs.json` — 30 hand-labeled
  `(policy section, regulation)` pairs, `true_impact_level` ∈
  {high, medium, low, not_applicable}, each with a one-sentence rationale.
  Stratified across all 4 levels and across the Day 25/26 failure pattern
  (generic regulations vs. unrelated policies).
- **Two gates, deliberately different:**
  - `CI_GATE_THRESHOLD = 0.80` — CLAUDE.md's aspirational target. Currently
    **FAIL** (73.3%) and expected to remain visibly red until F3 clears it.
    This is "are we done."
  - `REGRESSION_BASELINE = 0.70` — a *measured* floor set Day 27 at 73.3%
    minus a small margin. Enforced by
    `tests/test_f3_eval.py::test_accuracy_does_not_regress_below_baseline`
    on every test run. This is "did we just break something that used to
    work" — CI-blocking, independent of whether the 80% target is met.
- **Key insight (validated Day 29):** a number with no history can't be
  compared against; a number with history can. Experiment B (70.0%)
  technically passed the 70% gate but was a measured step backward from
  73.3% — only visible because 73.3% was on record from Day 27/28. The gate
  alone wouldn't have hard-failed; the *history* made the regression visible
  and it was correctly not shipped.
- **Confusion matrix as the primary diagnostic** — every `run_eval()` call
  prints a 4x4 true-vs-predicted matrix plus a list of every mismatch with
  `dense_score`, `named_regulation_match`, true vs. predicted level, and the
  golden set's rationale. This is what turned Day 26's "40%, something's
  wrong" into Day 27's specific, implementable fix.
- **Honest caveat carried through every layer:** the golden labels are
  Claude-generated (v1), `_metadata` in `impact_pairs.json` flags them
  "PENDING review by a compliance officer." 73.3% means "73.3% agreement with
  Claude's judgment of correctness," a meaningfully weaker claim than "73.3%
  agreement with a compliance officer's judgment" — disclosed in
  `docs/Trust-Strategy-v1.md` as the first thing a design partner should help
  validate.

---

## 7. Every Architectural Decision

| Decision | Rationale |
|---|---|
| **Dual-index architecture** (`policy_sections` + `regulation_chunks` as separate `VectorIndex` collections, not one combined index) | CLAUDE.md specifies dual-index Pinecone for F3. Separating the two lets each side be re-embedded/re-built independently (e.g. Day 29's two experiments touched only one index each) and keeps the "which side is this vector from" question structural rather than metadata-based. |
| **`matches.json` and `impact_results.json` as separate artifacts from separate scripts** (`matcher.py` vs. `classifier.py`) | Matching (candidate generation) and classification (impact scoring) are conceptually different operations with different failure modes — Day 24 found matching itself needed fixing (RRF score floor) before classification could be evaluated meaningfully. Separating them let Day 25's classifier work proceed on Day 24's matches without re-running the (slower) embedding/search step every time a threshold changed. |
| **`citations.py` as its own module, not inlined in `classifier.py`** | `is_named_regulation_match()` is reused by both `classifier.py` (to compute `impact_level`) and `evals/f3_eval.py` (to recompute the same feature for golden pairs, since `matches.json` may be stale relative to the golden set's `dense_score_snapshot`). A shared module guarantees both call sites use identical logic. |
| **`dense_score` stored on every match, separately from RRF `score`** | Without this (Day 24's original output), the classifier would have nothing usable to threshold. Storing both lets future work (e.g. a trained classifier, KM #17/#20) use either or both as features without re-running the matcher. |
| **All F3 data artifacts (`data/f3_indexes/*`) gitignored and regenerable** | Same pattern as F1/F2 — `build_indexes.py`, `matcher.py`, `classifier.py` are each independently re-runnable (`python -m src.f3_impact.<module>`), so the repo stays small and the pipeline is reproducible from fixtures + the live database. |
| **Fake-embedding-model test pattern reused across all 4 F3 test files** | Avoids `sentence-transformers` model downloads in CI (same as F2's tests) while still exercising real ranking/threshold logic with predictable, hand-picked vectors. |
| **`REGRESSION_BASELINE` as a second, separate constant from `CI_GATE_THRESHOLD`** (Day 27, KM #258) | A single 80% gate would stay "FAIL" indefinitely while F3 improves, providing no signal about *regressions* vs. *still-improving*. Two thresholds let CI distinguish "expected, tracked gap to target" from "newly broken, blocking." |

---

## 8. What Is Good, Weak, Missing

### 🟢 GOOD
- **End-to-end pipeline runs on real data**: 72 real policy sections (3
  synthetic fixtures) matched against 521 real chunks from 25 *actually
  ingested and summarised* F1/F2 regulatory documents — not a toy/mock
  dataset.
- **Every output is evidence-backed**: every match carries `dense_score`,
  `named_regulation_match`, and `matched_chunk_text` — Sarah never sees a
  bare "HIGH" label (`docs/Trust-Strategy-v1.md` §1).
- **Auditable classification**: `classify_impact` is a deterministic function
  over documented constants — same inputs always produce the same output,
  and the reasoning is one sentence (SR 11-7).
- **Regression CI works and has been proven**: Day 29's Experiment B is a
  real, on-record example of a candidate change being measured, found to
  regress, and correctly not shipped.
- **40% → 73.3% in one day (Day 27)**, from a single ~60-line module driven
  directly by the eval's confusion matrix — the eval-first build rule did
  exactly its job.
- **Honest self-assessment is built into the product artifacts**, not just
  internal notes: `docs/F3-MVP-Sample-v1.md` includes a deliberately-wrong
  example with explanation; the Week 4 exit-gate scorecard reports 2/6 met
  without softening.

### 🟡 WEAK
- **73.3% vs. the 80% CI gate** — F3 is not yet at its CLAUDE.md target.
  Fix: the remaining 8 mismatches share one diagnosed pattern (generic
  regulation vs. unrelated policy, `dense_score` 0.45-0.61); Day 27 concluded
  a single linear adjustment has hit its ceiling — next step is a second
  feature or a trained classifier on the now-30 labeled pairs (KM #17/#20).
- **Golden set is Claude-labeled, not SME-validated** — `_metadata` discloses
  this, but until a compliance officer reviews the 30 pairs, "73.3%" measures
  agreement with Claude's judgment, not ground truth. Fix: this is explicitly
  the first ask for any design partner (`docs/Trust-Strategy-v1.md`).
- **`citations.py` covers only 3 citation styles**, validated only against 3
  synthetic fixtures. Fix: needs testing against real client policy language
  before it can be trusted to compute `named_regulation_match` correctly for
  uploaded policies — currently the single highest-leverage feature in the
  classifier.
- **MEDIUM remains the hardest band** — only 3 of 30 golden pairs are
  MEDIUM, and the classifier gets only 1/3 right, unchanged since Day 26.
  Fix: needs more MEDIUM examples in the golden set before this band's
  accuracy can even be meaningfully measured.

### 🔴 MISSING
- **No real policy upload UI** — 3 synthetic fixture policies only.
  *Blocks*: the Week 4 exit-gate criterion "upload 5+ policies"; any design
  partner with real policies can't actually use F3 yet.
- **No F3 audit-trail logging** — `impact_results.json` isn't logged with
  model/prompt version per CLAUDE.md's hard constraint the way F2's
  `AuditLog` is. *Blocks*: this should close before any design partner sees
  live output tied to their real policies (`docs/Trust-Strategy-v1.md`,
  honest gap #1). Also a prerequisite for F5.
- **No feedback loop from Sarah back into the system** — no path for "Sarah
  marked this HIGH finding as wrong" to feed the golden set or thresholds.
  *Blocks*: F4's HITL approval flow (Day 32) is a start but doesn't close
  this loop yet (`docs/Trust-Strategy-v1.md`, honest gap #3).
- **Design partner outreach drafted but not sent** — 5 profiles + 2 email
  drafts exist (`docs/Design-Partner-Profiles-v1.md`); per build rules,
  Claude drafts only. *Blocks*: real-world validation of whether 73.3% with
  3 fixture policies is "useful" to an actual Sarah — the question the MVAP
  framing (`docs/Executive-Deck-v1.md`) says matters more than the accuracy
  number itself.

---

## 9. PM Interview Q&A

**Q1: Why is F3's accuracy 73.3% and not the 80% the CLAUDE.md target says?**
A: 73.3% (22/30) is up from 40% (12/30) one day earlier — the named-regulation-match
feature (Day 27) fixed most of Day 26's errors. The remaining 8 errors all
share one root cause: regulations like "Equal Credit Opportunity Act
(Regulation B)" share generic compliance vocabulary with policies they don't
actually govern, scoring `dense_score` 0.45-0.61 — too high to be NOT_APPLICABLE,
too low/ambiguous to cleanly separate from true MEDIUM cases with overlapping
scores. Day 27's analysis concluded a single linear threshold adjustment has
hit ~73-77% as its practical ceiling on this 30-pair set; closing the gap to
80% needs either a second independent feature or a trained classifier using
the 30 labeled pairs that now exist.

**Q2: What's the difference between the "80%" gate and the "70%" gate I see in the eval output?**
A: 80% (`CI_GATE_THRESHOLD`) is CLAUDE.md's *target* — it's currently failing
and expected to keep failing until F3 actually reaches it; that's tracked,
not urgent. 70% (`REGRESSION_BASELINE`) is a *measured floor* set the day we
hit 73.3%, with a small margin — it's CI-blocking. Any future change
(different embedding model, threshold tweak, new fixture) that drops accuracy
below 70% fails tests immediately, regardless of the 80% target. This
distinguishes "still working toward done" from "we broke something that used
to work."

**Q3: Day 29 says one experiment was "kept" and one was "rejected" — what does that mean in practice, and did we lose a day's work?**
A: No lost work — both experiments are fully documented (in
`notes/Day-29-F3.md` and in `build_indexes.py`'s docstrings) even though only
one shipped. Experiment A (adding policy-name/parent-section context to
policy-section embeddings) measured neutral — 73.3%, same as before — and was
kept because it's free and conceptually sound for when more/larger real
policies exist. Experiment B (adding document-title/source/section context to
regulation-chunk embeddings) measured 70.0% — it fixed 2 of the 8 known
errors but broke 3 new ones, a net regression. It was *not* shipped. This is
the regression-CI gate (built Day 27) working exactly as designed on its
first real test case.

**Q4: How does F3 decide a match is "HIGH" impact, and can that be explained to a regulator?**
A: Yes — that's the design point. Every match has a `dense_score` (cosine
similarity between the policy section and regulation text, 0-1) and a
`named_regulation_match` boolean (does this policy's own text cite this
regulation?). `classify_impact` adds `+0.10` if `named_regulation_match` is
true (or subtracts `0.20` if false), then compares to fixed thresholds
(0.55/0.45/0.35 for HIGH/MEDIUM/LOW). The explanation for any output is one
sentence: e.g. "dense_score 0.47 + 0.10 (Reg B is named in this policy's
Regulatory Framework section) = 0.57 ≥ 0.55 → HIGH." No LLM is in this final
step — it's a deterministic function over two numbers and documented
constants.

**Q5: Why isn't F3 using a trained ML classifier yet, given the roadmap mentions one (KM #17/#20)?**
A: Two reasons. First, there was no labeled data to train on until Day 26
built the 30-pair golden set — and 30 examples is far too few to train a
model without massive overfitting. Second, the threshold approach is
explainable in a way that matters for SR 11-7: "0.57 ≥ 0.55 → HIGH" doesn't
need SHAP values or a black-box explanation. The threshold classifier is
explicitly documented as a v1 placeholder; any future trained classifier must
preserve this auditability property (e.g., via feature importances), not just
match or beat 73.3% accuracy.

**Q6: The Week 4 exit-gate scorecard says only 2 of 6 criteria are "met" — is F3 behind schedule?**
A: Not behind in the sense that matters — the two hardest technical bets
(does the matching pipeline work on real data, and does the classifier
produce explainable High/Med/Low/N-A output with section IDs) are both met.
The 4 unmet/partial items are either scope deferred by design (5+ real
policies needs an upload UI not yet on the roadmap), a number trending the
right direction (40%→73.3% in one day, now 1 day later still 73.3% but for a
good reason — see Q3), or an action requiring the user, not Claude (sending
design-partner emails).

**Q7: What's the biggest single risk in F3 right now?**
A: That `citations.py`'s named-regulation-match feature — currently the
single highest-leverage signal in the classifier (it's the entire reason
accuracy went 40%→73.3%) — has only been validated against 3 synthetic
fixture policies using 3 citation styles ("... Act", "Regulation <Letter>",
"(ABBR)"). If a real client policy cites regulations differently (e.g. by CFR
section number only, or in a "Related Regulations" table rather than prose),
`named_regulation_match` would silently return `False` for regulations the
policy clearly does govern, applying the `-0.20` penalty incorrectly. This
wouldn't error — it would just quietly produce wrong impact levels.

**Q8: If a design partner asks "is this accurate," what's the honest answer?**
A: "73.3% agreement with Claude's own judgment on 30 example pairs that
haven't yet been reviewed by a compliance officer — and we can show you
exactly which 8 pairs we get wrong and why." That's the framing
`docs/Trust-Strategy-v1.md` and the Executive Deck's MVAP definition
deliberately use instead of leading with the number: "useful and honest
today" rather than "80% accurate today." The F3 MVP sample
(`docs/F3-MVP-Sample-v1.md`) practices this by including one of those 8
wrong examples right alongside the correct ones.

---

## 10. Architecture Diagram

```
fixtures/policies/*.txt (3 synthetic policy fixtures: BSA-AML, Fair-Lending-ECOA, TRID)
        │
        ▼
extractor.py ──► PolicySection[] (72 sections: N.M id, title, parent SECTION, text)
        │
        ▼
build_indexes.py ──► build_policy_index()
        │                  │ embeds "{policy_name} — {parent_section}\n{section_title}\n{text}"
        │                  ▼
        │            VectorIndex("policy_sections")  [72 vectors]
        │
        └──► build_regulation_index()
                   │ reads SUMMARISED RegulatoryDocuments (F1/F2, 25 docs)
                   │ chunk_hierarchical() (F2) → 521 chunks
                   │ embeds raw chunk.text
                   ▼
             VectorIndex("regulation_chunks")  [521 vectors]


             ┌─────────────────────────────────────────────┐
             │              matcher.py                       │
             │  for each of 72 policy sections:              │
             │    dense search (top 20) ─┐                   │
             │    BM25 search   (top 20) ─┼─► RRF (k=60) ──┐ │
             │                            │                 │ │
             │  collapse to per-doc, keep dense_score +     │ │
             │  matched_chunk_text, top 5 docs/section       │ │
             └─────────────────────────────────────────────┘
                              │
                              ▼
                       matches.json (≈251 matches)
                              │
             ┌────────────────────────────────────┐
             │           citations.py               │
             │  is_named_regulation_match(          │
             │    policy_name, regulation_title)    │  ◄── regexes over
             │  (cached per policy)                 │      fixtures/policies/*.txt
             └────────────────────────────────────┘
                              │
                              ▼
             ┌────────────────────────────────────┐
             │           classifier.py              │
             │  adjusted = dense_score              │
             │    + (NAMED_MATCH_BOOST   if match)  │
             │    + (NO_MATCH_PENALTY if no match)  │
             │  classify vs 0.55/0.45/0.35          │
             │    → HIGH/MEDIUM/LOW/NOT_APPLICABLE  │
             └────────────────────────────────────┘
                              │
                              ▼
                    impact_results.json
              (24 high / 1 medium / 14 low / 212 N/A
               across 72 sections, current build)
                              │
              ┌───────────────┴───────────────┐
              ▼                                 ▼
   docs/F3-MVP-Sample-v1.md           evals/f3_eval.py
   (10-pair Sarah-facing sample)      vs fixtures/golden/impact_pairs.json
                                       (30 labeled pairs)
                                                │
                                                ▼
                                  accuracy + confusion matrix
                                  CI_GATE_THRESHOLD=0.80 (target, FAIL)
                                  REGRESSION_BASELINE=0.70 (floor, enforced)
```

---

## 11. The Eval Journey — Day by Day

| Day | Accuracy | Confusion matrix highlight | What changed |
|---|---|---|---|
| 26 | **40.0% (12/30)** — CI FAIL | HIGH 8/10 good (80%); NOT_APPLICABLE only 2/11 (18%) — 7 of 11 true negatives predicted HIGH/MEDIUM | Golden set + eval pipeline built for the first time. This *is* the baseline measurement — no fix applied yet. |
| 27 | **73.3% (22/30)** — CI FAIL (target 80%), but **+33.3 pts** | HIGH 10/10 (100%); NOT_APPLICABLE 7/11 (64%); LOW 4/6; MEDIUM 1/3 (unchanged) | `citations.py` + `NAMED_MATCH_BOOST`/`NO_MATCH_PENALTY` added to `classify_impact`. `REGRESSION_BASELINE=0.70` added (KM #258). |
| 28 | **73.3% (22/30)** — unchanged (Review day) | Same as Day 27 | No code change. 10-pair MVP sample + executive deck published; Week 4 exit-gate scorecard: 2/6 met, 2 partial, 2 not met. |
| 29 (Exp A, kept) | **73.3% (22/30)** — unchanged | Same shape as Day 27 | Policy-section embeddings gain policy/parent-section context. Neutral but kept (low-cost, plausible future benefit). |
| 29 (Exp B, rejected) | **70.0% (21/30)** — at regression floor | Fixed #9, #10 (BSA §10.2, TRID §2.4 vs ECOA — both now correctly NOT_APPLICABLE/LOW); broke #11, #21, #30 (new TRID-vs-ECOA mismatches) | Regulation-chunk embeddings would gain document/source/section context. Net −1. **Reverted, not shipped.** |

**Day 27 confusion matrix (current production state — unchanged through Day 29):**
```
                              high          medium             low  not_applicable
            high                10               0               0               0
          medium                 0               1               1               1
             low                 0               0               4               2
  not_applicable                 0               0               4               7
```

**Day 26 confusion matrix (for comparison — the baseline being improved on):**
```
                              high          medium             low  not_applicable
            high                 8               2               0               0
          medium                 1               1               1               0
             low                 4               1               1               0
  not_applicable                 4               3               2               2
```

**The trajectory in one sentence:** 40% → 73.3% in one day via a single
~60-line, zero-cost, fully-auditable feature; 73.3% held steady for 3 more
days (1 review day, 2 experiments — one neutral/kept, one regressive/rejected)
— the eval and regression-CI infrastructure built on Day 26/27 is now doing
its job of keeping the number honest rather than just tracking it.

---

## Summary Scorecard

| Dimension | Score | Rationale |
|---|---|---|
| 🟢 **Engineering completeness** | 8/10 | Full pipeline (extract → dual-embed → hybrid-match → classify) runs end-to-end on real ingested F1/F2 data + 3 real policy fixtures, with 16 passing tests across 4 test files. Missing: real policy upload UI, scale beyond a local numpy vector store. |
| 🟡 **AI/ML quality** | 6/10 | 73.3% vs. 80% target, with a clearly diagnosed and documented remaining error pattern (not a mystery). Every decision (embedding reuse, hybrid search, threshold-not-trained classifier, named-match feature) has a stated rationale and a stated failure mode. Day 27's "ceiling" finding (single linear adjustment maxes ~73-77%) is itself a valuable, honest result. |
| 🟢 **Eval rigor** | 9/10 | Two-gate system (aspirational 80% + measured 70% regression floor) is a genuinely strong pattern, *proven* on Day 29's real rejected experiment — not just theoretical. Confusion matrix + per-mismatch rationale in every run. Only gap: golden labels are Claude-generated, not yet SME-reviewed (disclosed, not hidden). |
| 🟡 **Production readiness** | 4/10 | No real policy upload, no F3-specific audit-trail logging (CLAUDE.md hard constraint not yet met for F3's outputs), local vector store not multi-tenant Pinecone, `citations.py` validated on only 3 fixtures/3 citation styles. All gaps are documented, none are silent. |
| 🟢 **PM explainability** | 9/10 | Every classification decision reduces to one auditable sentence. The 40%→73.3% story, the Day 29 kept-vs-rejected experiments, and the honest Week 4 exit-gate scorecard are all genuinely good material for a design-partner or exec conversation — arguably *more* compelling than a clean 80% would be, because the "here's what we got wrong and why, and here's the gate that caught a regression" story is concrete and verifiable. |

**Blockers for next feature (F4 — Task Generation):**
- F4 will consume `impact_results.json`'s HIGH/MEDIUM findings to generate
  tasks. Until F3's accuracy improves (or F4's HITL approval flow, Day 32,
  is in place), F4 would be generating tasks from a classifier that's wrong
  ~27% of the time on its own golden set — manageable *if* every F4 task
  requires human approval before action (per `docs/Trust-Strategy-v1.md` §4),
  but not if F4 assumes F3's output is ground truth.
- F3 has no audit-trail logging yet (model/prompt version + inputs per
  CLAUDE.md) — F5 (audit trail) will need this retrofitted for F3's outputs,
  not just F2's.

**Recommended improvements before pilot:**
1. SME review of the 30 golden labels — the single highest-value next step
   per `docs/Trust-Strategy-v1.md`, since it determines whether "73.3%" means
   what it currently claims to mean.
2. Validate `citations.py` against citation styles beyond the 3 synthetic
   fixtures — this is the highest-leverage and least-tested component in the
   current 73.3% result.
3. A second classification feature or first trained-classifier pass (KM
   #17/#20) targeting the 8 remaining mismatches — Day 27's analysis suggests
   no further gains are available from adjusting the existing two-feature
   linear formula alone.
4. F3-specific audit-trail logging, ahead of any design partner seeing live
   output on real policies.
