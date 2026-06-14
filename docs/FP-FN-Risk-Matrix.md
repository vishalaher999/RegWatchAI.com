# RegWatch AI — FP/FN Risk Matrix

**Feature:** F1 Anomaly Detection + F2 Summarisation  
**Created:** 2026-06-01  
**Owner:** Vishal Aher  

---

## What This Document Is

Every AI classifier makes two types of errors:

| Error Type | What It Means | In RegWatch Context |
|------------|---------------|---------------------|
| **False Negative (FN)** | System misses something real | We don't flag a regulatory publication that was genuinely unusual or important |
| **False Positive (FP)** | System flags something that isn't a problem | We alert Sarah/Mike about a publication that turns out to be routine |

These two errors have **very different costs** in a compliance product. This document quantifies them so we can make principled decisions about thresholds.

---

## F1 Anomaly Detection — FP/FN Analysis

### False Negative: We miss an anomalous publication

**Scenario:** FinCEN publishes an emergency Geographic Targeting Order on a Sunday (off-schedule), with 8 documents in one day (3x their normal volume). Our Z-score threshold of 2.0 doesn't flag it.

**Consequence:**
- Sarah doesn't see the alert until her Monday manual review
- Delayed response to a BSA/AML requirement
- If the GTO has a 48-hour compliance window, the institution may already be in violation
- Regulatory examination finding: potential fine of **$500K–$5M**
- Reputational damage to RegWatch AI: "the system missed it"

**Severity: CRITICAL**  
**Likelihood: LOW** (Z > 2.0 catches top 2.5% of days — genuine spikes will be caught)

---

### False Positive: We flag a routine publication as anomalous

**Scenario:** The Federal Register publishes 25 documents in one day (vs. their average of 17) because of a batch of merger notices. Our system flags this as anomalous. Sarah investigates and finds nothing actionable.

**Consequence:**
- Sarah spends 15–30 minutes investigating a false alarm
- After 3–4 false alarms, Sarah stops trusting the anomaly flag
- She disables notifications or ignores them — defeating the entire feature
- **Trust erosion is the silent killer of compliance tools**

**Severity: MEDIUM** (wastes time, erodes trust)  
**Likelihood: MEDIUM** (Federal Register volumes are noisy)

---

### Threshold Decision: Z-score = 2.0

| Threshold | False Negative Rate | False Positive Rate | Decision |
|-----------|--------------------|--------------------|----------|
| Z > 1.0 | Very low | High (flags 16% of days) | Too noisy — trust erosion |
| Z > 1.5 | Low | Medium (flags 7% of days) | Borderline |
| **Z > 2.0** | **Low** | **Low (flags 2.5% of days)** | **Selected** |
| Z > 2.5 | Medium | Very low | Risks missing real spikes |
| Z > 3.0 | High | Near zero | Too conservative |

**Decision rationale:** In a compliance product, a false negative (missed alert) is more costly than a false positive (wasted 30 minutes). But chronic false positives cause trust erosion, which turns the feature off permanently — making it equivalent to 100% false negatives. Z > 2.0 balances both.

**Tuning trigger:** If Sarah reports >2 false positives per week, raise threshold to 2.5. If she reports a missed spike, lower to 1.8.

---

## F2 Summarisation — FP/FN Analysis

### False Negative: Summary misses critical information

**Scenario:** A Final Rule has a compliance deadline of March 15, 2027. The AI summary says "compliance_deadline: null" because the deadline was buried in section 4.3 of a 400-page document.

**Consequence:**
- Sarah doesn't set up a compliance task
- Institution misses the deadline
- Regulatory examination finding: **$500K–$5M fine**
- RegWatch AI is directly implicated: "your tool didn't tell us"

**Severity: CRITICAL**  
**Likelihood: MEDIUM** (long documents with buried deadlines are common)

**Mitigation:** Confidence score < 0.80 → human review queue. If the model isn't sure about a date, it flags it rather than guessing.

---

### False Positive: Summary invents information (hallucination)

**Scenario:** The AI summary states "effective date: January 1, 2027" for a proposed rule that has no effective date (it's still in comment period). Sarah relies on this date and schedules work around it.

**Consequence:**
- Compliance team does unnecessary work
- When Sarah discovers the error, she loses trust in all AI outputs
- She reverts to manual reading — defeating the product's purpose

**Severity: HIGH**  
**Likelihood: MEDIUM** (LLMs hallucinate dates with high confidence)

**Mitigation:** 
- Prompt instructs: "If not explicitly stated in the document, return null"
- Confidence score < 0.80 → human review
- Golden set eval specifically tests date extraction accuracy

---

## Asymmetry Summary

| Scenario | Cost | Who Bears It |
|----------|------|-------------|
| Miss a regulation (FN) | $500K–$5M fine + exam finding | The client institution |
| False alarm (FP) | 15–30 min wasted per alert | Sarah's time |
| Hallucinated date (FP) | Wrong compliance plan + trust erosion | Sarah's time + RegWatch reputation |
| Missed deadline in summary (FN) | $500K–$5M fine | The client institution |

**The asymmetry is stark:** False negatives cost the client millions. False positives cost minutes. This means:

1. When uncertain, **flag for human review** rather than suppress
2. The confidence threshold (0.80) errs toward flagging, not suppressing
3. "null" is always better than a hallucinated value
4. The human review queue is not a failure state — it's a feature

---

## Design Decisions Driven by This Matrix

| Decision | Driven By |
|----------|-----------|
| Z-score threshold = 2.0 (not 1.0) | FP trust erosion risk |
| Confidence < 0.80 → human review queue | FN cost in F2 |
| `null` preferred over guessed dates | FP hallucination risk |
| Immutable AuditLog | Regulatory accountability for both FP and FN |
| Golden set tests date extraction specifically | FN critical field |
| HITL gate for High-impact tasks (F4) | FN cost — missed high-impact findings |

---

## Review Schedule

This matrix should be reviewed and updated:
- After first pilot client onboarding (real-world FP/FN data)
- After F2 eval results are in (Week 3)
- After any regulatory examination that involves RegWatch AI output

*Last reviewed: 2026-06-01*
