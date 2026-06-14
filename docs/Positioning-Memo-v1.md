# RegWatch AI — Competitive Positioning Memo v1.0

**Author:** Vishal Aher  
**Date:** 2026-06-01  
**Purpose:** Define RegWatch AI's market position relative to existing solutions.  
**Audience:** Early pilot conversations, investor intros, product decisions.

---

## The Market in One Paragraph

US financial compliance is a $15B+ market dominated by two types of solutions: enterprise platforms costing $50K–$200K/year (Wolters Kluwer, Regology, Refinitiv) that serve large banks, and manual spreadsheet processes used by the 9,700 community banks and credit unions that can't afford enterprise software. RegWatch AI targets the underserved middle: community banks and credit unions with $100M–$10B in assets, compliance teams of 1–5 people, and a real need for automated regulatory intelligence at a price they can actually pay.

---

## Competitive Landscape

### Competitor 1: Wolters Kluwer Compliance Intelligence

**What they do:** Enterprise regulatory change management platform. Covers global regulations, includes policy management, workflow tools, and expert analysis.

**Price:** $50,000–$200,000/year. Requires multi-month implementations.

**Target:** Large banks ($10B+ assets), multinational financial institutions.

**Why community banks can't use it:**
- Price exceeds entire compliance budget for many community banks
- Implementation requires dedicated IT project (3–6 months)
- Built for large institutions with complex regulatory frameworks — overwhelming for a 2-person compliance team
- Annual contract locks them in before they know if it works

**Our advantage:** RegWatch AI is live in minutes (API key + URL), costs $999–$2,999/month, and is built specifically for the community bank use case — simpler, focused, affordable.

---

### Competitor 2: Regology

**What they do:** Regulatory intelligence platform with a large database of regulations, tracking, and workflow tools. Mid-market positioning.

**Price:** ~$15,000–$50,000/year. Quote-based.

**Target:** Mid-size financial institutions, compliance consulting firms.

**Key weakness:** Generic regulatory database. Not tuned to financial institutions specifically. "AI" features are primarily search and classification, not structured summarisation with compliance-specific output. No policy impact mapping.

**Our advantage:**
1. **Structured output built for compliance action** — RegWatch AI produces a 9-field JSON summary (effective_date, compliance_deadline, affected_institution_types, what_changed, why_it_matters). Regology produces search results.
2. **Policy impact mapping** — RegWatch AI maps regulations TO your internal policies (F3). Regology doesn't.
3. **Confidence scoring with review queue** — RegWatch AI flags uncertain summaries for human review. Regology has no equivalent.
4. **Purpose-built for community banks** — Regology serves broad financial services; RegWatch AI is designed for the community bank compliance officer persona.

---

### Competitor 3: Manual / Spreadsheets (THE REAL INCUMBENT)

**What they do:** Compliance officers manually check agency websites, download PDFs, read regulations, and track action items in spreadsheets or shared drives.

**Price:** $0 in software cost. 15–20 hours/week per compliance officer in labour cost.

**Why this is the real competitor:**
- 80%+ of community banks use this approach
- Zero switching cost — no contract to cancel, no data migration
- The compliance officer knows their own process, even if it's inefficient
- Feels "safe" because the human is fully in control

**Why community banks will switch:**
1. **Cost:** A compliance officer at $80,000/year spends 40% of time on manual monitoring = $32,000/year in hidden cost. RegWatch at $2,000/month = $24,000/year — and gives the officer 15+ hours back weekly.
2. **Risk:** Manual processes miss regulations. One missed rule = $500K–$5M in fines. RegWatch eliminates the "I didn't see that" failure mode.
3. **Defensibility:** Examiners increasingly ask "how do you monitor for regulatory changes?" A documented, auditable AI system is more defensible than "we check websites."

**Our advantage:** We don't compete on features with spreadsheets. We compete on ROI and risk reduction. The question is not "is RegWatch better than spreadsheets?" — obviously yes. The question is "is the compliance officer willing to trust an AI for something this important?" That's a trust sale, not a features sale.

---

## RegWatch AI's Position

**Statement:** RegWatch AI is the first AI-native compliance intelligence platform purpose-built for community banks and credit unions — delivering structured regulatory summaries, policy impact mapping, and automated task generation at 1/10th the cost of enterprise solutions.

**Positioning matrix:**

```
                    Enterprise (Wolters Kluwer, Regology)
                    └─ Full-featured, expensive, complex
                       Serves: Large banks ($10B+)

RegWatch AI
└─ AI-native, affordable, community-bank-specific
   Serves: Community banks ($100M–$10B)

Manual / Spreadsheets
└─ Free, familiar, risky, time-consuming
   Serves: Everyone who can't afford software
```

---

## Three Defensible Moats

**1. Policy library data network effect**
Every policy document uploaded by a client teaches RegWatch AI more about how real community bank policies are structured. The more policies we see, the better our impact mapping (F3) becomes. Competitors can copy our UI; they can't copy 500 community bank policy libraries.

**2. Switching cost after F3**
Once Sarah uploads her bank's policy library and RegWatch AI has mapped every regulation to her specific policies, switching means re-doing that work. The mapping becomes institutional knowledge. High switching cost is a product design choice, not a lock-in trick.

**3. Community bank trust**
Vishal's Moody's background gives unique credibility in the community bank compliance space. Community banks don't trust tech startups with compliance — they trust people with financial industry credentials. The trust is earned before the first demo call and can't be manufactured by a competitor who enters later.

---

## Why Now

Three things converging in 2026:
1. **AI capability:** Claude Sonnet produces structured JSON summaries of 400-page regulations in 10 seconds. 12 months ago this was impossible reliably.
2. **Regulatory pressure:** 2025–2026 saw record BSA/AML enforcement fines at community banks. Boards are requiring documented monitoring processes.
3. **Price accessibility:** Community banks couldn't afford $50K enterprise tools. At $1K–$3K/month, RegWatch enters affordable territory for an institution with $500M in assets.

---

## What RegWatch AI Is NOT

- **Not a legal advice tool** — RegWatch summarises regulations; Sarah's compliance judgement remains primary.
- **Not an enterprise platform** — We don't serve $50B+ banks. We don't want to. Wolters Kluwer owns that market and we can't compete there.
- **Not a general AI assistant** — RegWatch is domain-specific. It knows BSA, ECOA, TRID, HMDA, CRA. It doesn't help with HR policies or marketing campaigns.
- **Not a replacement for compliance officers** — RegWatch gives Sarah 15 hours back per week. She uses that time for higher-value work: vendor reviews, board reporting, examination prep.

---

## The Pitch in 30 Seconds

> "Every Monday morning, your compliance officer manually checks six government websites, downloads PDFs, and tries to figure out what changed. That takes 15–20 hours a week. One missed regulation can cost $500,000 to $5 million in fines.
>
> RegWatch AI monitors all five federal agencies daily, summarises every new regulation in plain English in under 30 seconds, maps it to your specific internal policies, and generates compliance tasks automatically.
>
> It's $1,999 a month. Your compliance officer's time costs $40 per hour. RegWatch pays for itself the first week."

---

*This memo is version 1.0. Update after first 3 pilot conversations with real compliance officers.*
