# Day 45 — Git Init, v1.0 Tag, Live Smoke Test, Case Study Finalised (Week 7 Day 3, final day)

**Date:** 2026-06-14
**Roadmap:** Week 7 ("Integration + Portfolio"), Day 3 of 3 — final day

---

## What Was Built

| Artifact | Type | Status |
|---|---|---|
| Git repo | INIT | `git init`, 221 files committed as root commit |
| `v1.0` tag | NEW | Annotated tag on the root commit |
| Local smoke test | RUN | `uvicorn api.main:app` on port 8001, all 6 endpoint groups hit |
| `docs/Case-Study-v1.md` | EDIT | Added "Day 45: The Live Smoke Test" section with real compliance-report numbers; updated test count and date range |
| `docs/ARCHITECTURE.md` | EDIT | Day 45 entry added |
| `.gitignore` | EDIT | Added `.claude/` to "Claude Code local state" section |

---

## Roadmap — Day 45 columns

| Column | Content |
|---|---|
| Engineering | Final smoke test on a live URL; tag `v1.0` release in Git; archive all notes and artifacts |
| Product | Case study finalised with real metrics; portfolio published; Loom updated if needed |
| Deliverable | Portfolio publish ✓ |

---

## What Changed and Why

**Git init + commit + tag.** No git identity was configured (local or global,
per the Git Safety Protocol's "never update the git config"). Resolved by
passing `-c user.name="Vishal Aher" -c user.email="vishalaher904@gmail.com"`
as one-off flags on the `git commit` invocation — scoped to that single
command, not a persistent config change. Before staging, `.gitignore` was
re-verified to exclude `.env`, `*.db`/`*.sqlite*`, `logs/`, `data/f3_indexes/`,
`exports/`, and `.claude/`; `git status --short | grep -i "\.env\|\.db\|\.sqlite"`
confirmed only `.env.example` was staged. The result is one root commit
(`e3eaa74`, 221 files, 36,276 insertions) tagged `v1.0`.

**Live smoke test.** `docker --version` is unavailable in this build
environment (confirmed Day 40/41 and again today), so the Render/Railway
Docker deploy path described in `docs/Deployment-Guide-v1.md` could not be
exercised end-to-end. Instead, `uvicorn api.main:app --port 8001` was run
locally and every documented endpoint was hit with `curl`:

- `/health` → `{"status":"ok"}`
- `/f1/documents?limit=2` → real `RegulatoryDocument` rows with full
  `summary_json`
- `/f2/review-queue?limit=2` → real review-flagged summaries
- `/f3/impact-results?limit=2` → real policy/regulation match pairs
- `/f4/tasks?limit=2` → real drafted `Task` rows (Fair-Lending-ECOA-Policy
  Section 1.1)
- `/f5/compliance-report?days=7` and `?days=90` → real aggregates

All six returned live data from the dev SQLite DB on the first try — no
code changes were needed. This confirms the FastAPI layer built on Day 40
actually works against real data, which is the substance of "final smoke
test on a live URL," even though "live" here means "running locally," not
"reachable from the internet."

**`docs/Case-Study-v1.md` updated with real metrics.** The 90-day
`/f5/compliance-report` response was used as the source of truth:
19 documents ingested, routing breakdown (approved: 11, review: 13,
escalate: 8, dismiss: 48, unknown: 15), 0 guardrail warnings, 54 HIGH
findings, 3 tasks created, 0.0% override rate. These are written into a new
"Day 45: The Live Smoke Test" section, with an explicit note that the 0%
override rate reflects a tiny sample (3 tasks), not calibration. The case
study's date range, test count (191→194), and title were updated to cover
Days 1–45 and tagged `v1.0`.

**"Archive all notes and artifacts."** Interpreted as: `notes/Day-*.md` (all
45 days) and `docs/*.md` (all portfolio/design/ops docs) are already the
archive — they're now committed and tagged as part of `v1.0`, which is the
durable snapshot. No separate archive step or index file was created beyond
this note and the `docs/ARCHITECTURE.md` entry, since both already serve as
the index into the build history.

---

## Result

```
$ git log --oneline -1
e3eaa74 (HEAD -> master, tag: v1.0) v1.0: RegWatch AI initial commit - F1-F5 pipeline complete

$ curl -s http://127.0.0.1:8001/f5/compliance-report?days=90
{"period_start":"2026-03-16T02:12:32","period_end":"2026-06-14T02:12:32",
 "documents_ingested":19,
 "summaries_by_routing":{"unknown":15,"escalate":8,"review":13,"dismiss":48,"approved":11},
 "guardrail_warnings":0,"high_findings":54,"tasks_created":3,"override_rate_pct":0.0}
```

---

## v1 Limitations

1. **No public live URL** — local smoke test only. Docker/Render deploy from
   `docs/Deployment-Guide-v1.md` remains unverified end-to-end (no Docker CLI
   in this environment).
2. **Override rate is statistically meaningless at n=3** — 0.0% is accurate
   but not yet a useful trust signal per `docs/Override-Rate-Dashboard-v1.md`.
3. **F2 faithfulness gap (0.783 vs. 0.85) remains open** — flagged in Day 44
   and SD1 §6, not addressed today; today's scope was integration/portfolio,
   not eval improvement.
4. **No frontend** — the portfolio page (Day 44) is still content only.

---

## PM Insight

The most useful thing about today's smoke test wasn't that it passed — it's
*how* it passed: zero code changes, first try, against the real dev database
that's been accumulating real (synthetic-but-realistic) data since Day 1.
That's the payoff of the "one `AuditLog` table for everything" decision from
Day 1 and the Day 40 read-only API built directly on top of the existing
SQLModel tables — there was no separate "demo data" or "API data model" to
keep in sync. The gap between "smoke test passed" and "this is live on the
internet" is entirely infrastructure (Docker + a host), not application
code — which is exactly the kind of gap that's easy to state honestly in a
case study and easy for a reader to evaluate for themselves.

---

**Week 7 / v1.0 complete.** This closes the 45-day build documented in
`docs/ARCHITECTURE.md`, `docs/Case-Study-v1.md`, and `docs/SD1-System-Design-v1.md`.
