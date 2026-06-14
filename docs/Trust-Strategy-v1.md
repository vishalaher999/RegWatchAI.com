# Trust Strategy v1 — How RegWatch Earns Compliance Trust (Day 29)

**Why this matters:** Sarah's job is to be the person who catches the thing
that gets the bank in trouble. A tool that's wrong confidently is worse than
no tool — it either gets ignored (alert fatigue) or, worse, trusted blindly
on the one finding that mattered. Trust isn't a UI polish item; it's the
precondition for F3-F5 being used at all. This doc lays out the concrete
mechanisms RegWatch already has, and the ones still needed, organized around
how a skeptical compliance officer would actually evaluate an AI tool.

---

## 1. Show the evidence, not just the verdict

Every F3 match carries `matched_chunk_text` — the actual regulation text that
drove the score — alongside `dense_score` and `named_regulation_match`.
Sarah never sees a bare "HIGH impact" label; she sees the label, the score,
and the exact sentence that triggered it. `docs/F3-MVP-Sample-v1.md` is built
this way deliberately: every one of the 10 examples shows its evidence.

**Why this builds trust:** it converts "trust the AI" into "verify the AI's
homework" — a much smaller ask, and the one SR 11-7 effectively requires
anyway (model outputs must be independently checkable).

---

## 2. Disclose limitations as part of the product, not the fine print

`docs/F3-MVP-Sample-v1.md` includes one deliberately-wrong example (#8 —
predicted LOW, true NOT_APPLICABLE) with an explanation of *why* it's wrong.
`fixtures/golden/impact_pairs.json`'s `_metadata` block discloses that the
golden labels themselves are Claude-generated, "PENDING review by a
compliance officer," not yet SME-validated ground truth.

**Why this builds trust:** a tool that says "here's what I get wrong and
why" is the one a careful person starts trusting *more* over time, because
its claims of correctness become falsifiable. A tool that only shows
successes invites the question "what aren't you showing me?"

---

## 3. Make every AI decision attributable and reproducible

Per CLAUDE.md's hard constraints: every AI decision logs model version +
prompt version + inputs. F2's summaries and (eventually) F4's task-generation
agent write this to `AuditLog`. For F3, the equivalent is that
`classify_impact()` is a deterministic threshold function over documented
constants (`HIGH_THRESHOLD`, `NAMED_MATCH_BOOST`, etc.) — given the same
`dense_score` and `named_regulation_match`, it always produces the same
`impact_level`, and the reasoning ("0.57 >= 0.55 -> High because Reg B is in
this policy's own Regulatory Framework section") is one sentence.

**Why this builds trust:** "why did it say HIGH" must have an answer that
doesn't require re-running an LLM or trusting a black box. F3's threshold
classifier is explicitly a placeholder partly *because* it's auditable in
this way (documented in `classifier.py`'s docstring) — any future trained
classifier (KM #17/#20) needs to preserve this property (e.g., via feature
importances / SHAP), not just accuracy.

---

## 4. Human-in-the-loop where the AI is least certain

F2's review queue flags low-confidence summaries for human review before
they're treated as final. The same pattern extends naturally to F3/F4:
MEDIUM-impact findings and any HIGH-impact task (Week 5, Day 32's HITL
approval flow) should require a human "approve" before anything acts on
them. RegWatch's value isn't "fully autonomous compliance" — it's "surface
the right things to the right person fast," with the human keeping the final
call on anything consequential.

**Why this builds trust:** progressive autonomy (Day 30's roadmap item) means
the system *earns* more autonomy over time by being right when a human
checked it — not by being granted trust upfront.

---

## 5. Prove the system doesn't quietly get worse

The Day 27 regression-CI gate (`REGRESSION_BASELINE` in `evals/f3_eval.py`,
enforced by `tests/test_f3_eval.py`) is a trust mechanism as much as an
engineering one: it's a standing, automated commitment that says "today's
accuracy (73.3%) is the floor — any future change that drops below it fails
CI before it ships." Today's contextual-retrieval experiment (Day 29) is the
first real test of this: prepending document context to regulation chunks
measured at 70.0%, exactly at the floor, and was **not shipped** because it
regressed 2 of 3 fixed cases into new ones. Prepending policy/section context
to policy sections measured at 73.3% (neutral) and **was** kept.

**Why this builds trust:** a design partner (or Sarah) can be told "we test
every change against a fixed accuracy floor before it ships" — a concrete,
verifiable claim, not a vibe. The fact that one of today's two experiments
was rejected by this gate is itself evidence the gate works.

---

## 6. Honest framing in design-partner conversations

`docs/Design-Partner-Profiles-v1.md`'s outreach drafts deliberately avoid
citing the 73.3% number as a selling point — per the PM note there, the
strategy is "show the output, let them judge." Slide 4 of
`docs/Executive-Deck-v1.md` defines MVAP as "useful and honest today,"
explicitly not "80% accurate today." A design partner who sees both the
correct HIGH findings AND the one documented LOW/NOT_APPLICABLE error in the
same sample is being treated as a partner, not a prospect.

**Why this builds trust:** in a regulated industry, "we're not done yet, and
here's exactly where" from a vendor is rare enough to be itself a credibility
signal.

---

## What's Missing (honest gaps, for Week 5+)

- **No real audit trail for F3 yet** — F5 (audit trail) is scheduled later in
  the roadmap. Until then, F3's outputs (`impact_results.json`) aren't logged
  with model/prompt version per the CLAUDE.md hard constraint the way F2's
  `AuditLog` entries are. This is a real gap, not yet a contradiction (F3 is
  pre-MVP), but should be closed before any design partner sees live output
  tied to their real policies.
- **Golden set is Claude-labeled, not SME-validated** — disclosed (see #2),
  but until a compliance officer reviews the 30 pairs, "73.3% accuracy" means
  "73.3% agreement with Claude's judgment of what's correct," which is a
  meaningfully weaker claim. This should be the first thing a design partner
  is asked to help with.
- **No mechanism yet for Sarah to give feedback that changes the system** —
  trust is bidirectional. F4's HITL approval flow (Day 32) is a start, but
  there's no current path for "Sarah marked this HIGH finding as wrong" to
  feed back into the golden set or thresholds.
