# Day 40 — FastAPI + Docker (KM #227 / #229)

**Date:** 2026-06-13
**Roadmap:** Week 6 ("Deploy & Demo"), Day 5 of 7

---

## What Was Built

| Artifact | Type | Status |
|---|---|---|
| `api/main.py` | NEW | Done — 9 read-only endpoints over F1-F5 data |
| `tests/test_api.py` | NEW | Done — 12/12 passing |
| `requirements.txt` | EDIT | `fastapi==0.136.3`, `uvicorn==0.49.0` added, installed |
| `Dockerfile` | NEW | Written, **build unverified** (no Docker in this env) |
| `.dockerignore` | NEW | Done |
| `render.yaml` | NEW | Written, **deploy unverified** (no cloud access) |
| `docs/Deployment-Guide-v1.md` | NEW | Done |
| `docs/Demo-Walkthrough-Script-v1.md` | NEW | Done |
| `docs/ARCHITECTURE.md` | EDIT | Day 40 entries added |

---

## Roadmap v2.2 — Day 40 columns

| Column | Content |
|---|---|
| KM reference | #227 (FastAPI), #229 (Docker) |
| Feature | Infrastructure — deploy layer over F1-F5 |
| Deliverable | Working API + Dockerfile + deploy runbook + demo script |
| Eval / success metric | API endpoints return correct, filtered data matching known counts (72 policy sections, 23 high-impact sections, 182 total tests passing) |

---

## What Changed and Why

**`api/main.py`** wraps existing read paths (DB via `src/database.get_session`,
and `data/f3_indexes/*.json`) in FastAPI routes. No new tables, no write
endpoints — this is purely an integration surface for whatever already
exists. Each F-area gets its own small section (`/f1/...` through
`/f5/...`), mirroring the 5-feature pipeline structure so the API's shape
matches the product's mental model.

`/f5/compliance-report` just calls Day 38's `build_report()` directly —
no duplication, the API is a thin wrapper.

**`tests/test_api.py`** intentionally runs against the *real* dev DB rather
than a fixture DB (same pattern as `dashboard/app.py`'s read-only access).
The goal isn't to re-test F1-F5 logic (already covered by 170 other tests)
— it's to verify the API layer correctly shapes and filters whatever data
is currently there. `test_policy_sections_returns_metadata` hard-asserts
`len(sections) == 72`, which is the current real count; if that ever
changes (e.g. policy fixtures change), this test will need updating —
that's intentional, it's a canary for "did the index shape change
unexpectedly."

**Dockerfile / render.yaml** follow the deploy target named in CLAUDE.md
(Render or Railway, Docker). `render.yaml` marks `ANTHROPIC_API_KEY` and
`LANGCHAIN_API_KEY` as `sync: false` so Render prompts for them manually —
consistent with the "no secrets in repo" hard constraint.

---

## Result

```
$ python -m pytest tests/ -q
182 passed, 11 deselected, 62 warnings in 10.61s
```

(170 from Days 1-39 + 12 new in `tests/test_api.py`.)

All 9 endpoints manually verified live via `TestClient` against current dev
data:
- `/health` → `{"status": "ok"}`
- `/f1/documents` → 111 docs; single-doc lookup and 404 both correct
- `/f2/review-queue` → 5 flagged docs; `/f2/summaries` → 25 docs with summaries
- `/f3/impact-results?impact_level=high` → 23 sections, all matches "high"
- `/f3/policy-sections` → 72 entries
- `/f4/tasks` → 3 tasks; `?status=open` → 3
- `/f5/audit-log?action=summarise&limit=3` → 3 rows, all `action: "summarise"`;
  unknown action → 400
- `/f5/compliance-report` → matches Day 38's markdown report numbers exactly

---

## v1 Limitations

1. **Docker build not verified in this session.** `docker --version` →
   "command not found" — this dev environment has no Docker installed. The
   Dockerfile follows standard conventions (`python:3.12-slim`, install
   requirements, copy app, `uvicorn` CMD) but `docker build -t regwatch-api .`
   has not been run. `docs/Deployment-Guide-v1.md` documents this honestly
   and gives you the exact commands to run locally to verify.
2. **Render/Railway deploy not executed.** No cloud account access from this
   session. `render.yaml` is written and `docs/Deployment-Guide-v1.md` walks
   through both Render (Blueprint) and Railway (Dockerfile auto-detect).
3. **No Loom recording.** `docs/Demo-Walkthrough-Script-v1.md` is the script
   to record over — recording itself is a user action.
4. **No auth, SQLite on (likely) ephemeral filesystem.** Fine for a demo;
   both are called out as v2 follow-ups in the deployment guide.
5. **Large image size** (~3-4GB) from `sentence-transformers`/`torch`, which
   the API doesn't use. A `requirements-api.txt` split is the fix, deferred
   until it's confirmed to actually be a problem.

---

## PM Insight

Today's pattern is different from Days 37-39 ("infrastructure exists but
inert" — trace IDs, citations, audit actions that were defined but never
used). Today everything *built* works and is *tested* — but three of the
"deliverables" (Docker build, cloud deploy, recorded demo) are steps that
require tools or access this session doesn't have. The honest move is the
same kind of thing as a guardrail: rather than claim "Dockerized and
deployed," the deliverable is "here's the Dockerfile, here's the exact
command, here's what to watch for if it fails" — i.e., the runbook *is*
the Day 40 artifact, same way the weekly compliance report *is* the F5
artifact rather than a claim that compliance was achieved.

---

**Next: Day 41** — do not start without explicit "next".
