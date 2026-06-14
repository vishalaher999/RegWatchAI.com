# Deployment Guide v1 — FastAPI API (Day 40, KM #227/#229)

**Date:** 2026-06-13
**Feature:** Week 6, Day 5 of 7 (infrastructure)
**Status:** `api/main.py` + `Dockerfile` + `render.yaml` written and the API
verified locally via `TestClient` (12/12 tests in `tests/test_api.py`). The
Docker build and the actual Render/Railway deploy were **not** run from this
session — this environment has no `docker` CLI and no cloud account access.
This doc is the runbook for you to do both.

---

## What's been verified

```
$ python -m pytest tests/test_api.py -q
12 passed in 0.95s
```

All 9 endpoints (`/health`, `/f1/documents[/{id}]`, `/f2/review-queue`,
`/f2/summaries`, `/f3/impact-results`, `/f3/policy-sections`, `/f4/tasks`,
`/f5/audit-log`, `/f5/compliance-report`) return real data from the current
dev DB + `data/f3_indexes/*.json` when run via FastAPI's `TestClient` (an
in-process ASGI client — no server/socket needed, which is why it works
without `uvicorn` running).

---

## Step 1 — Run locally with uvicorn (verify before Docker)

```
pip install -r requirements.txt
uvicorn api.main:app --reload
```

Then visit:
- `http://127.0.0.1:8000/health` → `{"status": "ok"}`
- `http://127.0.0.1:8000/docs` → FastAPI's auto-generated Swagger UI — useful
  for the Loom walkthrough (see `docs/Demo-Walkthrough-Script-v1.md`)

---

## Step 2 — Build and run the Docker image

```
docker build -t regwatch-api .
docker run -p 8000:8000 --env-file .env regwatch-api
```

Then `curl http://localhost:8000/health` from another terminal.

**Not verified in this session** — no `docker` binary available here. If the
build fails, the most likely culprits are `sentence-transformers`/`torch`
download size (the image is large, ~3-4GB) or a missing system library for
`torch` on `python:3.12-slim`. If that happens, the quickest fix is splitting
a `requirements-api.txt` containing only `fastapi`, `uvicorn`, `sqlmodel`,
`python-dotenv` (the API's actual imports — see `api/main.py`'s import list)
and pointing the Dockerfile at that instead. This is flagged as a v2 item
below rather than done preemptively, since it's unverified whether it's
even needed.

---

## Step 3 — Deploy to Render

1. Push this repo to GitHub (if not already).
2. At https://dashboard.render.com/blueprints, click "New Blueprint
   Instance" and connect the repo. Render reads `render.yaml` automatically.
3. `render.yaml` declares `ANTHROPIC_API_KEY` and `LANGCHAIN_API_KEY` with
   `sync: false` — Render will prompt you to enter these manually in its
   dashboard. **Never commit real values for these** — `.env` stays
   gitignored, as it always has been.
4. `DATABASE_URL` defaults to the SQLite file baked into the image at build
   time (whatever `regwatch.db` contains when you `docker build`/push). This
   is fine for a demo but **not persistent** — Render's filesystem is
   ephemeral, so writes (new ingests, new tasks) during the live demo won't
   survive a redeploy. For anything beyond a demo, point `DATABASE_URL` at a
   managed Postgres instance (Render offers one) — this is the
   `sqlite:///` → `postgres://` swap `src/database.py`'s docstring already
   anticipates.
5. Render builds the Docker image and exposes a public URL
   (`https://regwatch-api-<random>.onrender.com`). Health check path
   `/health` is set in `render.yaml`.

### Railway alternative

Railway also supports "Deploy from Dockerfile" directly from a GitHub repo —
no blueprint file needed, just connect the repo and Railway detects the
`Dockerfile`. Set the same environment variables (`ANTHROPIC_API_KEY`,
`LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`, `LANGCHAIN_TRACING_V2`,
`DATABASE_URL`) in Railway's dashboard under the service's "Variables" tab.

---

## v1 Limitations / v2 follow-ups

- **Docker build unverified** (no `docker` CLI in this session) — verify
  `docker build -t regwatch-api .` succeeds before relying on it for a live
  demo.
- **SQLite + ephemeral filesystem** — fine for a read-only demo of existing
  data; not suitable for a deploy that needs to persist new writes (new
  ingests, F4 tasks, audit rows). Swap to managed Postgres for that.
- **Image size** — `requirements.txt` includes `sentence-transformers`/
  `torch` for F2/F3, which `api/main.py` never imports. A `requirements-api.txt`
  split would shrink the image substantially; not done here since it's
  unverified whether the current image even fails to build/deploy.
- **No auth** — every endpoint is open. Fine for an internal demo URL; not
  fine for anything handling real client data (ties into
  `docs/Enterprise-Pilot-Program-v1.md`'s "no frontend SSO/multi-user
  accounts" out-of-scope note from Day 39).
