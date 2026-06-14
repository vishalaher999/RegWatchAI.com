# RegWatch AI — 3/6/12-Month Product Roadmap

**Version:** 1.0
**Date:** 2026-06-01
**Author:** Vishal Aher
**Based on:** 45-day build plan + pilot feedback (anticipated)

---

## Where We Are (Day 21 / Week 3 Complete)

| Feature | Status | Quality |
|---------|--------|---------|
| F1 — Feed Monitoring | COMPLETE | 6 agencies, 111 docs, anomaly detection live |
| F2 — AI Summarisation | COMPLETE | RAGAS faithfulness 0.783 (target 0.75 met) |
| F3 — Policy Impact Mapping | Building (Week 4) | — |
| F4 — Task Generation | Building (Week 5) | — |
| F5 — Audit Trail | Building (Week 6) | — |

---

## Month 1 (Weeks 1–4): Core Intelligence + First Pilots

**Milestone:** First pilot client using RegWatch AI to monitor regulations.

**Engineering:**
- F1 + F2 complete (done today)
- F3 v1: policy upload, semantic mapping, High/Medium/Low/N/A classification
- F3 eval: 30+ regulation-policy pairs labeled, precision@3 >= 0.75
- Deploy to Railway (URL live for pilot demos)

**Product:**
- 2–3 pilot clients signed (compliance consultants prioritised)
- Weekly feedback calls with pilots
- Onboarding flow built (self-service setup)
- Mobile-readable summary cards

**GTM:**
- LinkedIn outreach to compliance consultants in NAFCU/ABA communities
- First 5 outreach messages sent by Week 4
- Demo Loom video recorded (F1 + F2 + F3 preview)

**Success criteria:**
- At least 1 pilot actively using F2 summaries daily
- F3 maps at least 10 real regulation-policy pairs for pilot client
- Pilot NPS >= 7/10

---

## Month 2 (Weeks 5–7): Full Chain + First Revenue

**Milestone:** First paying client. Full F1→F2→F3→F4→F5 chain working.

**Engineering:**
- F4: LangGraph task agent, HITL approval for High-impact, task board UI
- F5 v1: Immutable audit log, LangSmith traces linked, AuditLog viewer in dashboard
- F5 v2: Compliance report export (PDF/CSV), weekly summary email
- Postgres migration (Railway deploy)
- React frontend replaces Streamlit for production quality
- FastAPI backend wiring all features

**Product:**
- Convert 1–2 pilots to paid ($999–$1,999/month)
- Officer edit UX live in production
- Notification system (email digest on new rules)
- Override rate tracking dashboard (target <20%)

**GTM:**
- Content: "How Community Banks Can Automate Regulatory Monitoring" (LinkedIn + ABA forums)
- First partner conversation with compliance consultant
- Referral program design

**Success criteria:**
- 1 paying client (any plan)
- End-to-end demo: RSS → summary → impact → task → audit in 5 minutes
- F3 precision@3 >= 0.75 confirmed on real client policies

---

## Month 3 (Weeks 8–12): Scale to 10 Clients + Quality Bar

**Milestone:** 8–10 clients, $12K–$20K MRR.

**Engineering:**
- State regulators (Phase 2): add 5 state banking regulators to F1
- Slack integration: regulatory digest in #compliance channel
- Policy auto-draft: F3 suggests draft policy language for new rules
- RAGAS continuous eval: eval runs weekly, alert if faithfulness drops below 0.70
- Isolation Forest anomaly detection (upgrade from Z-score baseline)
- Multi-tenant data isolation (Pinecone namespace per client)

**Product:**
- Consultant dashboard (multi-client view for Mike persona)
- White-label reports for consultant resellers
- Pricing page live ($999 / $1,999 / $2,999 / Enterprise)
- Pilot-to-paid playbook documented
- SHED and FOMC summary accuracy improved (known gap from Day 21 eval)

**GTM:**
- 2 compliance consultant channel partners signed
- Case study published with real metrics (hours saved, regulations monitored)
- Speaking opportunity at one community banking conference

**Success criteria:**
- 8–10 paying clients
- $12K–$20K MRR
- F2 faithfulness >= 0.85 (Day 45 target)
- At least 1 client successfully using F3 for policy review

---

## Known Technical Debt (to address in months 2–3)

| Item | Impact | Priority |
|------|--------|----------|
| 20-doc cap per agency (pagination missing) | May miss overflow publications | HIGH |
| Isolation Forest not implemented (using Z-score) | Anomaly detection less accurate | MEDIUM |
| utcnow() deprecation warnings | Cosmetic — Python 3.12 | LOW |
| Alembic migrations not set up | Manual DB reset needed for schema changes | MEDIUM |
| Onboarding flow deferred | Mike/Sarah must be set up manually | HIGH |
| 7-day fixture dataset incomplete (4 entries) | Offline dev limited | LOW |

---

## Metrics to Track Every Week

| Metric | Month 1 target | Month 3 target |
|--------|---------------|----------------|
| Clients using daily | 2 (pilots) | 8–10 |
| MRR | $0 (pilots) | $12K–$20K |
| F2 faithfulness | 0.783 (current) | >= 0.85 |
| Review queue rate | 24% (current) | < 20% |
| Time-to-understand | < 2 min (design target) | Measured with pilots |
| Human override rate | Untracked | < 20% |

---

## The One Thing That Must Not Slip

F3 (policy impact mapping) must launch before any client churns from F1+F2.

Reason: F1 and F2 are valuable but replicable. Any well-funded competitor can build an RSS ingester and summarisation pipeline in 6 months. F3 — where Sarah uploads her bank's policy library and RegWatch AI maps regulations to her specific BSA Policy §4.2 — is what creates switching cost. Once a client has their policies mapped, leaving RegWatch means losing all that institutional intelligence.

Every week we don't ship F3 is a week clients are using RegWatch as a glorified RSS reader that could be replaced by a free alert service. Every week we do have F3 shipped is a week of switching cost building.

---

*Roadmap v1.0. Review with pilot clients after Month 1.*
