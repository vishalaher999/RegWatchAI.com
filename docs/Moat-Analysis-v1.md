# RegWatch AI — Moat Analysis v1.0

**Author:** Vishal Aher
**Date:** 2026-06-01
**Purpose:** Analyse which aspects of RegWatch AI are defensible against competition.
**Framework:** Each moat is assessed on: strength (1-5), time to develop, and what it would take for a competitor to replicate.

---

## Why Moat Analysis Matters at Week 3

We have a working product. The question is: if a well-funded competitor builds the same thing in 6 months, do we survive?

Moats in AI compliance tools come from three places:
1. **Data** — proprietary data that improves the product the more it's used
2. **Workflow integration** — the product becomes load-bearing in daily operations
3. **Trust** — compliance officers trust specific people/brands, not just products

---

## Moat 1: Policy Library Data Network Effect (F3)

**What it is:**
Every policy document uploaded by a client teaches RegWatch AI what real community bank policies look like. With 50 clients, the impact mapper has seen 50 different BSA policies. With 500 clients, it has seen 500 — each one slightly different, covering different edge cases, using different terminology.

The more policies we've seen, the more accurately we can map new regulations to new clients' policies. A competitor starting today would have zero policies. We'd have our entire client base's libraries.

**Strength: 4/5**

**Time to develop:** 12–18 months of client data

**What it takes to replicate:**
A competitor must acquire clients before they can build this moat — but clients go to the product that already has the moat. Classic cold-start problem. The first mover who survives to 50+ clients wins this moat.

**Current state:** Not yet — F3 (policy impact mapping) starts Week 4. But every client we sign before a competitor builds F3 is a future data point the competitor can never have.

---

## Moat 2: Switching Cost After F3 Integration

**What it is:**
Once Sarah uploads her bank's full policy library and RegWatch AI has mapped 200 regulations to her specific policies (BSA Policy §4.2, TRID Policy §3.1, etc.), switching tools means:
- Re-uploading the entire policy library
- Re-running all historical mappings
- Losing all the institutional knowledge encoded in the mapping results
- Re-training her team on a new tool

This is analogous to Salesforce switching cost — the data is in the tool, and the tool is in the workflow.

**Strength: 5/5 (once F3 is live and used)**

**Time to develop:** Immediate after F3 launches — every mapping creates switching friction

**What it takes to replicate:**
A competitor can't replicate the specific mapping history. They can build the capability, but they can't undo the investment Sarah has made in RegWatch AI's map of her institution.

**Current state:** F3 launches Week 4. Every week of delay before F3 is a week without this moat building.

---

## Moat 3: Domain Credibility (Founder Background)

**What it is:**
Community bank compliance officers are deeply suspicious of technology vendors. They've been burned by overpromised RegTech before. Trust is the first filter — if they don't trust the founder, they won't try the product.

Vishal's Moody's background changes the conversation immediately. "A Moody's alumnus built this to solve the problem I have right now" is a fundamentally different pitch than "a startup founder thinks they understand compliance."

**Strength: 3/5 (durable but not unbeatable)**

**Time to develop:** Years of industry credibility — cannot be replicated quickly

**What it takes to replicate:**
A competitor needs either (a) a founder with equivalent credentials, (b) enterprise sales backing that creates institutional trust, or (c) client references that substitute for founder credibility. Option (c) takes 12-18 months of successful deployments.

**Current state:** Active from Day 1. Used in every sales conversation.

---

## Moat 4: Audit Trail + Compliance-by-Design (F5)

**What it is:**
RegWatch AI is built from Day 1 with SR 11-7 compliance in mind. AuditLog is INSERT-ONLY. Every AI decision is logged with model version, prompt version, confidence score, and human review status. LangSmith traces link every summary to its exact prompt and context.

This is not a feature — it's architecture. A competitor can't add this retroactively without a full rewrite.

**Strength: 3/5 (functional but replicable with 6 months of work)**

**Time to develop:** We built this in Week 1. A competitor starting today needs 3-6 months to get here.

**What it takes to replicate:**
Pure engineering time. Not defensible long-term, but a meaningful head start.

**Current state:** AuditLog built Week 1. LangSmith integration Week 6.

---

## Moat 5: Community Bank Network (GTM Moat)

**What it is:**
Community banks talk to each other through NAFCU, CUNA, ABA community banking groups, state banking associations, and compliance consultant networks. Mike (compliance consultant) serving 8 clients is the perfect distribution point. One positive referral in a banking association meeting reaches dozens of potential clients.

This is a distribution moat — our channel is more valuable than our product for the first 12 months.

**Strength: 2/5 (real but early)**

**Time to develop:** First 3-6 client relationships unlock this

**What it takes to replicate:**
Any competitor with similar credibility and an active community banking network can replicate this. It's an advantage, not a moat.

**Current state:** Outreach hasn't started. Design partner program planned for Week 4.

---

## Competitive Moat Map

```
                 Time to replicate (months)
            0        6        12        18+
Strength
  5/5   |              [F3 Switching Cost] ←────── GROW THIS FASTEST
  4/5   |                      [Policy Library Data]
  3/5   |  [Audit Trail]   [Domain Credibility]
  2/5   |  [Community Network]
  1/5   |
```

**Key insight:** The F3 policy mapping integration creates both the strongest moat (switching cost = 5/5) AND takes the longest for a competitor to replicate (18+ months). This is why the roadmap designates F3 as "THE CORE" (★). Everything else — F1, F2, F4, F5 — exists to get clients to the point where they integrate F3.

---

## What This Means for Product Prioritisation

1. **F3 must launch on time (Week 4).** Every week of delay = one week fewer clients building switching cost.
2. **Client activation > feature completeness.** A client using F2 summaries is fine. A client with F3 policy integration is a retained client.
3. **The audit trail (F5) is a trust accelerator**, not just a compliance checkbox. Show it early in sales demos.
4. **Mike (consultant) is the highest-leverage GTM channel.** One consultant = 5-8 community bank clients. Prioritise consultant relationships over direct bank outreach.

---

## The One-Sentence Moat

*RegWatch AI's policy library network effect means that after 12 months of client data, our impact mapping is more accurate than any competitor starting today — and after a client integrates F3, the cost of switching away exceeds the cost of any competitive product.*

---

*Moat analysis v1.0. Review after first 10 paying clients.*
