# Build vs. Buy Matrix — F3 Policy Impact Mapping
## Version 1 | Day 26 | Informed by today's eval result (40% vs. 80% target)

---

## Why This Matters Today, Specifically

Day 26's eval just showed the v1 threshold classifier scores **40% (12/30)**
against a hand-labeled golden set — well below the 80% CI gate. Before
sinking more engineering days into calibrating an in-house classifier,
it's worth asking: **is there a commercial component that already solves
this better, and should we buy it instead of building it?**

This matrix evaluates F3 at two levels:
1. **Whole-feature**: buy a RegTech impact-mapping module vs. build F3 in-house
2. **Component-level**: for the parts of F3 we keep building, which pieces
   should be bought (managed services) vs. built (custom code)?

---

## Level 1: Whole-Feature — F3 Policy Impact Mapping

| | **Build (current path)** | **Buy (e.g. Ascent RegTech, Compliance.ai, Wolters Kluwer OneSumX, Thomson Reuters Regulatory Intelligence)** |
|---|---|---|
| **Cost** | ~7 engineer-days so far (Days 22-26), ongoing calibration | $30K-150K+/year licensing, typical for community-bank tier; often bundled with broader GRC suite |
| **Accuracy today** | 40% on 30-pair golden set (v1, unvalidated thresholds) | Vendor-claimed 80-90%+ (not independently verified against OUR policy fixtures) |
| **Customization** | Full — matches our exact policy structure (`SECTION N: N.M Title`), our exact 6 monitored agencies | Limited — vendors map to THEIR policy taxonomy; community banks often have to restructure policies to fit the vendor's model |
| **Time to "good enough"** | Unknown — Day 26 suggests 2-4 more days of calibration work (see Level 2) | Days to weeks for vendor onboarding + policy ingestion, but accuracy on OUR fixtures still unverified |
| **Data residency** | 100% local (no data leaves the bank's environment) — strong selling point for community banks wary of cloud GRC | Varies; most are cloud SaaS, requires uploading policy library to vendor |
| **Moat value** | HIGH — impact mapping calibrated to a specific bank's policy library + its specific regulatory footprint is RegWatch AI's core differentiator (see `Moat-Analysis-v1.md`) | LOW for us — if we buy this, RegWatch AI becomes a thin wrapper around a vendor API, easily replicated by competitors |

### Recommendation: **Build, with eyes open**

Today's 40% is a v1-threshold-tuning problem, not an architectural dead end
(see Level 2 — the fix is likely a few well-chosen features, not a rebuild).
Buying this component would gut RegWatch AI's core moat. The honest risk is
**timeline**, not feasibility — if calibration drags past Week 5, revisit.

---

## Level 2: Component-Level — What to Build vs. Buy/Use-Managed

| Component | Current choice | Buy/managed alternative | Recommendation | Why |
|---|---|---|---|---|
| **Embeddings** | Local `sentence-transformers` (all-mpnet-base-v2) | OpenAI `text-embedding-3`, Cohere Embed, Voyage AI | **Build (keep local)** | Zero marginal cost, no data leaves machine (compliance-sensitive). Day 26's 40% is NOT primarily an embedding-quality problem — see below. |
| **Vector store** | Local numpy+JSON `VectorIndex` | Pinecone (already in CLAUDE.md stack target) | **Buy when scaling** | Fine at 521 chunks. Becomes a real "buy" decision once real client policy libraries (hundreds of pages) + full regulation corpus (thousands of docs) exceed in-memory numpy. One-file swap per `vectorstore.py`'s design. |
| **Hybrid search (dense+BM25+RRF)** | Built in-house (Day 24) | Managed hybrid search (e.g. Pinecone's native hybrid, Elasticsearch) | **Build** | RRF_K=60 and the dense/BM25 split are simple, well-understood, free. No managed service adds enough value here to justify the integration cost. |
| **Impact classifier** | Threshold rule on `dense_score` (Day 25, v1) | Vendor's pre-trained impact/relevance classifier (e.g. as part of a RegTech suite) | **Build, but redesign the features** | This is where Day 26's 40% lives. The fix is NOT "buy a classifier" — it's "the classifier needs better INPUT features than raw cosine similarity." See Day 26 finding below. |
| **Regulatory citation extraction** (e.g. recognizing "Regulation B", "12 CFR 1002") | Not yet built | Vendor regulatory-citation NER/taxonomy services | **Consider buying/using open taxonomy** | Day 26's mismatches are dominated by cases where a regulation's TITLE names a specific law ("Equal Credit Opportunity Act (Regulation B)") that does or doesn't match the POLICY's named regulation. A small open citation taxonomy (e.g. CFR part → topic mapping) could be a cheap, high-leverage feature — cheaper to build than buy at this scale. |

---

## Day 26 Finding That Drives This Matrix

The classifier's false positives cluster around **long, generically-worded
regulations** ("Equal Credit Opportunity Act (Regulation B)", "Agency
Information Collection Activities: Comment Request") scoring 0.44-0.61
dense similarity against policy sections that share only generic
banking-compliance vocabulary, not substance.

The false negatives (Pairs #21, #26, #27) are true ECOA-relevant matches
that scored only 0.47-0.52 — UNDER the high threshold — because the
shared vocabulary between the policy section and the regulation is more
specific/technical than generic, and mpnet's embedding doesn't weight that
specificity enough relative to surface-level topic similarity.

**Implication:** `dense_score` alone is necessary but not sufficient. The
fix is feature engineering (e.g., does the policy's named regulation
appear in the candidate regulation's title? — a cheap BM25-style exact
match on regulation names), not a different vector DB or a vendor API.
This is now buildable with real data — the 30-pair golden set is the first
training signal for KM #17/#20 (LogReg), which Day 27+ can revisit.

---

## Summary

| Decision | Verdict |
|---|---|
| Buy a RegTech impact-mapping suite instead of building F3? | **No** — would eliminate the core moat |
| Switch embeddings to a paid API? | **No** — not the bottleneck, and local keeps data on-prem |
| Move to Pinecone now? | **Not yet** — local store handles current scale; one-file swap when needed |
| Buy a classifier? | **No** — the fix is feature engineering on top of existing free signals (dense_score + named-regulation matching), not a smarter black box |
| Build a "named regulation match" feature for Day 27? | **Yes — highest-leverage next step**, directly targets the Day 26 mismatch pattern |
