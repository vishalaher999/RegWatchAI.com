# RegWatch AI — Executive Deck v1 (Day 28)

5-slide outline. Markdown for now — convert to slides later if needed for an
actual presentation. Written for an audience deciding whether to keep
funding/time-boxing this build (could be the user's own future self, an
advisor, or an early design partner).

---

## Slide 1 — The Problem

**Community banks can't keep up with regulatory change using manual review.**

- Federal Reserve, CFPB, OCC, FDIC, FinCEN each publish rules, notices, and
  guidance on independent schedules — no single feed.
- A compliance officer (Sarah persona) at a $100M-$2B bank typically has no
  dedicated tooling: she reads agency emails/RSS, then manually re-reads
  policy manuals to judge "does this change anything for us?"
- The cost of missing something isn't abstract — it shows up as exam
  findings, consent orders, and (per Day 27's design-partner research) is the
  exact moment a bank becomes most motivated to adopt a tool like this.

---

## Slide 2 — What RegWatch Does (5-Feature Pipeline)

```
F1 Ingest → F2 Summarise → F3 Map Impact → F4 Generate Tasks → F5 Audit Trail
```

- **F1** (done): monitors 5 federal agencies, classifies doc types, flags
  publication anomalies.
- **F2** (done): RAG-based plain-English summaries with confidence scoring
  and a human-review queue (RAGAS-evaluated).
- **F3** (in progress, Week 4): maps each regulatory change against the
  bank's own policy library — by section — and rates impact High/Med/Low/N-A.
- **F4** (Week 5+): auto-generates review tasks from High/Medium findings,
  with human approval gates (LangGraph, SR 11-7 aligned).
- **F5** (later): immutable audit trail — every AI decision logs model
  version, prompt version, and inputs, for exam-readiness.

---

## Slide 3 — F3 MVP: What It Produces Today

See `docs/F3-MVP-Sample-v1.md` for 10 concrete examples. In short, for each
policy section RegWatch now shows:

- The specific regulation it's matched against (with evidence text)
- A similarity score (`dense_score`) and whether the regulation names a law
  the policy itself already cites (`named_regulation_match`)
- An impact level (High/Medium/Low/Not Applicable) with the same threshold
  logic every time — auditable, not a black box

**Eval result (Day 27):** 73.3% (22/30) agreement with hand-labeled ground
truth, up from 40% at the start of the week. Below the 80% target, but the
remaining errors are a single well-understood pattern (generic regulations
over-matching unrelated policies) — not random noise.

---

## Slide 4 — MVAP Definition (Minimum Viable AI Product)

**MVAP** = the smallest version of RegWatch that a real compliance officer
would (a) trust enough to look at regularly, and (b) get genuine time savings
from — even with known, disclosed limitations.

For F3, MVAP means:

1. **Coverage:** at least the 3 core policy areas every community bank has
   (BSA/AML, Fair Lending, TRID/mortgage disclosure) — done via fixtures, real
   policies are the Week 5+ upgrade.
2. **Explainability:** every impact rating shows its evidence and score —
   "trust but verify" rather than a opaque AI verdict. Done.
3. **Honest error disclosure:** known limitation patterns (like #8 in the MVP
   sample) are documented, not hidden — SR 11-7 model risk management
   requires this, and design partners will trust a tool more, not less, for
   showing its seams.
4. **A floor that doesn't regress:** the Day 27 regression-CI gate
   (`REGRESSION_BASELINE`) ensures the MVAP, once it exists, doesn't silently
   get worse.

**MVAP is NOT:** 80% eval accuracy (that's the CI_GATE_THRESHOLD, an
aspirational target), 5+ real policies, or zero false positives. Those are
v2 goals. MVAP is "useful and honest today."

---

## Slide 5 — Where This Goes Next

- **Week 5 (Days 29-35):** F3 precision improvements (contextual retrieval,
  multi-query) + F4 task-generation agent — closing the loop from "here's a
  flagged change" to "here's a task, assigned, with a due date."
- **Design partners:** 5 profiles + 2 outreach drafts ready
  (`docs/Design-Partner-Profiles-v1.md`) — sending these is the next
  Product action once F3's MVP sample (Slide 3 / this deck) is ready to show.
- **The moat:** F3's impact-mapping logic (dual-index + hybrid search +
  named-regulation feature) is the hardest-to-replicate part of the pipeline
  and is now demonstrably working on real regulatory data — Day 26's
  build-vs-buy analysis holds.
