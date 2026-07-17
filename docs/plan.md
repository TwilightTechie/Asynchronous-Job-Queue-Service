# Plan — Ordered, Runnable Milestones

Companion to `docs/requirements.md` (functional spec, SLOs, scope cuts) and `docs/design.md` (stack, deployment target, schema). This document fixes the **build order** for the 3-hour window in `AGENTS.md`: get something live on DigitalOcean early to retire deploy risk first, then layer features onto the deployed target. Each milestone below ends in a state you can independently verify with a `curl` command (or, for the test/CI milestones, an equivalent exact command) — no milestone depends on a later one to be checkable.

**Note on the existing Milestone 1 TDD plan** (`docs/superpowers/plans/2026-07-17-milestone-1-skeleton-app.md`): it currently bundles health endpoints, structured logging, and Prometheus metrics into one milestone. This plan splits that: **M1** here is health endpoints only (needed to deploy something by T+90); logging + metrics move to **M5**, after the worker and status endpoint exist and there's real job activity to observe. When M1 execution starts, split that TDD plan's Tasks 3–4 (logging, metrics) and Task 5 (middleware) out into the M5 plan rather than building them early.

Time budget totals 180 minutes (3 hours), checkpointed at T+90 as instructed.

---

## M1 — Walking Skeleton (Health Endpoints)

**Time:** T+0 → T+40

**Builds:** Minimal FastAPI app with `/healthz` and `/readyz`; `PORT` read from env var (`pydantic-settings`), since App Platform injects `PORT` at runtime; multi-stage, non-root Dockerfile so the skeleton is container-ready for M2.

**Definition of done:** `docker build` succeeds; the container runs and serves both routes on the configured port.

**Test:**
```bash
docker build -t jobqueue .
docker run -d -p 8080:8080 --name jobqueue-m1 jobqueue
curl -s localhost:8080/healthz
curl -s localhost:8080/readyz
docker rm -f jobqueue-m1
```
**Expected:** both return `200` with `{"status": "ok"}` / `{"status": "ready"}`.

**Non-negotiables introduced:** `/healthz`, `/readyz`, config via env vars, multi-stage non-root Dockerfile.

---

## M2 — Deployed to DigitalOcean (checkpoint: **by T+90**)

**Time:** T+40 → T+90

**Builds:** Nothing new in the app — this milestone is purely "get M1's artifact live." Primary path: DO App Platform, Dockerfile source, deploy via `git push` to `main` (per `docs/design.md` §2). Create the app, confirm the build succeeds, capture the live URL.

**Definition of done:** the walking skeleton from M1 answers on a public DO URL. This is the hard checkpoint — if App Platform is blocking (build errors, account limits) past T+75, fall back to Droplet + Docker (`docs/design.md` §2) rather than burning the rest of the budget on it.

**Test:**
```bash
export APP_URL=https://<your-app>.ondigitalocean.app   # from the DO dashboard/doctl output
curl -s "$APP_URL/healthz"
curl -s "$APP_URL/readyz"
```
**Expected:** same `200` responses as M1, now from the public URL. From here on, every later milestone's curl test targets `$APP_URL` — each `git push` to `main` triggers an App Platform rebuild+redeploy of whatever is on `main` at that point.

**Non-negotiables confirmed:** service is actually deployed (the overarching goal), config via env vars proven end-to-end (DO sets `PORT`, app reads it correctly).

---

## M3 — Ingestion + Validation

**Time:** T+90 → T+115

**Builds:** `POST /jobs` — Pydantic-validated body (`type` restricted to the `report|transcode|export` enum, `input` required object), `JobService.submit_job()`, `InMemoryJobRepository` storing the job as `queued`. No worker yet — job just lands in the store; consuming it is M4. Structured `422` error responses for invalid payloads (`docs/design.md` §5).

**Definition of done:** a valid submission returns `201` with an id immediately (no waiting); an invalid submission returns a structured `422`.

**Test:**
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$APP_URL/jobs" \
  -H "Content-Type: application/json" \
  -d '{"type": "report", "input": {"customer_id": "abc123"}}'

curl -s -X POST "$APP_URL/jobs" \
  -H "Content-Type: application/json" \
  -d '{"type": "not-a-real-type", "input": {}}'
```
**Expected:** first call prints `201`; second returns `422` with `{"error": {"code": "invalid_request", "message": "..."}}`.

**Non-negotiables introduced:** input validation with structured JSON errors and correct status codes.

---

## M4 — Processing Worker + Status Endpoint

**Time:** T+115 → T+140

**Builds:** `asyncio.Queue` + fixed-size worker pool started in the app lifespan; `MockProcessor` (random 2–10s sleep, ~20% failure rate, retry up to `MAX_ATTEMPTS`); `GET /jobs/{id}` returning full job state; `404` with a structured error for unknown ids. `/readyz` now also gates on the worker pool having started.

**Definition of done:** a submitted job visibly transitions `queued → running → completed|failed` when polled, and `attempts` reflects any retries.

**Test:**
```bash
ID=$(curl -s -X POST "$APP_URL/jobs" \
  -H "Content-Type: application/json" \
  -d '{"type": "transcode", "input": {"file": "clip.mp4"}}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

for i in $(seq 1 12); do
  curl -s "$APP_URL/jobs/$ID"; echo
  sleep 3
done

curl -s "$APP_URL/jobs/00000000-0000-0000-0000-000000000000"
```
**Expected:** the polling loop shows `status` moving from `queued` to `running` to a terminal `completed` (with `result`) or `failed` (with `error`, `attempts == max_attempts`) within the loop's ~36s window. The unknown-id call returns `404` with `{"error": {"code": "job_not_found", ...}}`.

**Non-negotiables introduced:** none new (this is the core functional milestone); `/readyz` semantics deepen.

---

## M5 — Metrics + Logs

**Time:** T+140 → T+155

**Builds:** `ObservabilityMiddleware` emitting one structured JSON log line per request (`{ts, req_id, route, status, dur_ms}`); Prometheus `/metrics` with RED metrics (`http_requests_total`, `http_request_duration_seconds`) plus job-domain metrics (`jobs_submitted_total`, `jobs_completed_total`, `jobs_failed_total`, `job_queue_depth`, `job_processing_duration_seconds`).

**Definition of done:** every request produces a log line with the required keys; `/metrics` reflects job activity generated in M3/M4's tests.

**Test:**
```bash
curl -s "$APP_URL/jobs" >/dev/null   # generate a request to observe
curl -s "$APP_URL/metrics" | grep -E 'http_requests_total|jobs_submitted_total|jobs_completed_total|jobs_failed_total'
```
**Expected:** at least one sample line for each metric name, with the labels from earlier milestones' requests (e.g. `route="/jobs"`, `method="GET"`). Structured logs are checked via the platform's log stream (`doctl apps logs <app-id>` or the DO dashboard) rather than curl — confirm a line like `{"ts": "...", "req_id": "...", "route": "/jobs", "status": 200, "dur_ms": 4.1}` appears.

**Non-negotiables introduced:** Prometheus `/metrics` (RED), JSON structured logs.

---

## M6 — Tests

**Time:** T+155 → T+170

**Builds:** fills in the unit test suite left implicit in M1–M5 (config, logging, metrics, middleware, health/status routes, service-layer retry logic) plus the one required API-level integration test (`TestClient` drives a job through its full lifecycle, with mock sleep/failure-rate env vars shrunk for speed).

**Definition of done:** full suite green locally; no code changes needed to make it pass (tests describe what M1–M5 already built).

**Test:**
```bash
pytest -v
ruff check .
```
**Expected:** all tests `passed`, `ruff check .` prints `All checks passed!`. As a regression check against the live deploy, re-run M2's curl:
```bash
curl -s "$APP_URL/healthz"
```
**Expected:** still `{"status": "ok"}` — confirms nothing in the test-writing pass required app changes that weren't deployed.

**Non-negotiables introduced:** the "tests: unit + one API-level integration test" requirement is fully met.

---

## M7 — CI Green

**Time:** T+170 → T+180

**Builds:** `.github/workflows/ci.yml` — `lint (ruff) → test (pytest) → build (docker build)` on every push/PR; on `main`, after both are green, a deploy step (`doctl apps create-deployment`, using `DIGITALOCEAN_ACCESS_TOKEN` + `DO_APP_ID` secrets) triggers the App Platform redeploy. A red lint/test stage blocks the deploy step from running.

**Definition of done:** pushing to `main` produces a green GitHub Actions run that ends in a successful DO deployment, end to end, with no manual step.

**Test:**
```bash
git push origin main
gh run watch --exit-status
curl -s "$APP_URL/healthz"
```
**Expected:** `gh run watch` exits `0` (all jobs passed, including deploy); the final curl still returns `{"status": "ok"}`, now served by the CI-triggered deployment rather than a manual one.

**Non-negotiables introduced:** CI pipeline (lint → test → build → deploy), fully gated on green.
