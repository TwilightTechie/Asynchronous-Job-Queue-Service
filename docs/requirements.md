# Requirements — Asynchronous Job Queue Service

Status: approved for implementation
Target: single, small, deployed service on DigitalOcean within a 3-hour build window. Optimize for a working deployed increment over completeness; no speculative generality.

## 1. Problem & Goal

Customers submit long-running work (report generation, media transcoding, data exports). Synchronous HTTP handling doesn't scale for this. Build a REST API backed by an asynchronous job queue that:

- accepts a job submission and returns immediately with a job ID (HTTP response is fully decoupled from processing),
- processes jobs in the background via a bounded worker pool,
- lets callers poll job status and list jobs by status.

## 2. Functional Requirements

### 2.1 Job Submission — `POST /jobs`

- Body: `{"type": "report"|"transcode"|"export", "input": {...}}`.
- `type` is validated against a fixed enum; `input` is a required JSON object (contents not otherwise validated).
- Invalid payload → `422` with a structured error body (see §6).
- On success → `201 {"id": <uuid>, "status": "queued", "created_at": <iso8601>}`. The job is placed on the queue; the HTTP handler does not wait for processing.

### 2.2 Background Worker Pool

- A fixed pool of `WORKER_POOL_SIZE` (default 4, env-configurable) asyncio worker tasks, started at app startup, each loop: pull a job from the queue, mark it `running`, execute the processor, record the outcome.
- Mock processing: sleep for a random duration in `[MOCK_MIN_SLEEP_SECONDS, MOCK_MAX_SLEEP_SECONDS]` (default 2–10s, env-configurable so tests can shrink it to near-zero), then fail with probability `MOCK_FAILURE_RATE` (default 0.2, env-configurable).
- Retry policy: on failure, if `attempts < MAX_ATTEMPTS` (default 3, i.e. up to 2 retries), the job is immediately requeued (`running → queued`, no artificial backoff — the mock work itself already takes 2–10s). Once attempts are exhausted, the job moves to `failed` with an error message. `attempts` is exposed on the job so retry behavior is observable via the API.

### 2.3 Job Status — `GET /jobs/{id}`

- Returns the full job object: `id, type, input, status, result, error, attempts, max_attempts, created_at, updated_at`.
- `status ∈ {queued, running, completed, failed}`.
- `result` is populated only when `status == completed`; `error` only when `status == failed`.
- Unknown ID → `404` with a structured error body.

### 2.4 Job Listing — `GET /jobs?status=`

- Returns `{"jobs": [...]}`, newest first (by `created_at`), no pagination.
- Optional `status` query filter; an invalid status value → `422`.

## 3. Architecture

Layered, dependency-inverted design so the in-memory implementation can later be swapped (e.g. for SQLite/Redis) without touching callers:

```
HTTP layer (FastAPI routers)      — request/response only, no business logic
   │
Service layer (JobService)        — submit_job / get_job / list_jobs orchestration
   │           │
Repository        Queue           — Protocol interfaces (dependency inversion)
(InMemoryJobRepo)  (AsyncioJobQueue)
                       │
                Worker pool (N asyncio tasks) → JobProcessor Protocol → MockProcessor
                       │
                updates Repository only; never touches the HTTP layer
```

- `JobRepository` and `JobQueue` are `Protocol` interfaces; `JobService` depends on the abstraction (Dependency Inversion). Swapping storage later means adding a class, not editing the service or API layer (Open/Closed).
- `JobProcessor` is a `Protocol`; `MockProcessor` is the only implementation for this build. A real per-`type` processor would be a separate implementation selected by `job.type` — explicitly out of scope now (§5).
- Single responsibility per layer: routers validate/serialize, service orchestrates, repository stores, queue sequences, workers execute, processor does the "work."
- Storage: in-process only — `asyncio.Queue` for the queue, an in-memory `dict` for job state. Both live in one asyncio event loop, so no locks are needed: no `await` occurs between a read and its corresponding write within any single repository method.

## 4. Non-Negotiables (every service, no exceptions)

These apply regardless of feature scope and are not up for descoping:

1. **`/healthz`** — liveness probe, `200` whenever the process is up.
2. **`/readyz`** — readiness probe, `200` once the worker pool has started and the app can accept work; `503` during startup and during shutdown drain.
3. **Prometheus `/metrics`** — RED (Rate, Errors, Duration) for HTTP: `http_requests_total{method,route,status}`, `http_request_duration_seconds` histogram. Plus job-domain metrics: `jobs_submitted_total`, `jobs_completed_total`, `jobs_failed_total`, `job_queue_depth` (gauge), `job_processing_duration_seconds` (histogram).
4. **JSON structured logs** — one line per request: `{ts, req_id, route, status, dur_ms}`. `req_id` is a `uuid4`, or passthrough of an incoming `X-Request-ID` header.
5. **Input validation** — structured JSON errors with correct HTTP status codes (§6), not raw stack traces or plain-text errors.
6. **Graceful shutdown on SIGTERM** — stop accepting new HTTP connections, signal workers to stop pulling new jobs, let in-flight jobs finish (bounded by 2–10s mock work, well under budget), then exit. Drain budget: ≤30s.
7. **Config via env vars** — no hardcoded ports, pool sizes, or tunables (full list in §7).
8. **Multi-stage Dockerfile, non-root** — build stage installs dependencies; final runtime stage is slim, copies only runtime artifacts, runs as a non-root user.
9. **CI: lint → test → build → deploy** — every push/PR runs lint (ruff) and test (pytest); on `main`, after both pass, build the Docker image and deploy (§8). A red lint/test stage must block deploy.
10. **Tests** — unit tests plus one API-level integration test, all run in CI (§9).

## 5. Explicit Scope Cuts (out of scope for this build)

Deliberately excluded to fit the 3-hour window. Each is a straightforward follow-up, not a hidden gap:

- **No persistent storage.** Job state is in-memory only; a restart or redeploy loses all jobs. Acceptable because this is a single-instance demo service, not a durability guarantee.
- **No horizontal scaling / multi-instance coordination.** The queue is process-local (`asyncio.Queue`); running more than one instance would give each instance its own disjoint queue and job set. Single instance only.
- **No authentication/authorization.** The API is open. Would need an API key or gateway auth before handling real customer data.
- **No pagination on `GET /jobs`.** Full (optionally filtered) list every time — fine at demo scale, not at production job volume.
- **No real job-type business logic.** `report` / `transcode` / `export` are validated as types but all route through the same `MockProcessor` (random sleep + ~20% failure) — no actual report generation, transcoding, or export happens.
- **No retry backoff strategy.** Retries requeue immediately; no exponential backoff or jitter.
- **No job cancellation or deletion endpoints.**
- **No rate limiting.**
- **No push/streaming status updates** (WebSocket, SSE) — status is polling-only via `GET /jobs/{id}`.
- **No multi-region or HA deployment.** Single DO App Platform instance/region.
- **No distributed tracing** (e.g. OpenTelemetry spans) — structured request logs only.

## 6. Error Contract

All errors share one shape:

```json
{"error": {"code": "job_not_found", "message": "No job with id <id>"}}
```

Produced via a single FastAPI exception handler mapping a small set of domain exceptions to status codes — not scattered inline `HTTPException` calls. Known cases: `422` invalid payload / invalid `status` filter value, `404` unknown job id.

## 7. Configuration (env vars)

| Var | Default | Purpose |
|---|---|---|
| `PORT` | `8080` | HTTP listen port |
| `WORKER_POOL_SIZE` | `4` | number of concurrent background workers |
| `MAX_ATTEMPTS` | `3` | total attempts before a job is marked `failed` (i.e. up to 2 retries) |
| `MOCK_MIN_SLEEP_SECONDS` | `2` | mock processing lower bound |
| `MOCK_MAX_SLEEP_SECONDS` | `10` | mock processing upper bound |
| `MOCK_FAILURE_RATE` | `0.2` | probability a mock job fails |
| `LOG_LEVEL` | `INFO` | log verbosity |

Tests override `MOCK_MIN_SLEEP_SECONDS`/`MOCK_MAX_SLEEP_SECONDS`/`MOCK_FAILURE_RATE` so the integration test completes in milliseconds rather than seconds.

## 8. Deployment

- Multi-stage Dockerfile → DigitalOcean App Platform (Dockerfile source), single instance.
- GitHub Actions: `lint (ruff) → test (pytest) → build (docker build)` on every push/PR. On `main`, after lint+test pass, a deploy step calls `doctl apps create-deployment` (using `DIGITALOCEAN_ACCESS_TOKEN` + `DO_APP_ID` secrets) to trigger the App Platform deploy — deploy never fires on a red pipeline.

## 9. Testing Strategy

- Unit tests: `JobService` (submit/get/list, not-found, invalid filter), state-machine/retry transitions with a fake deterministic processor, validation error shapes.
- One API-level integration test: `TestClient` posts a job and polls `GET /jobs/{id}` until it reaches a terminal state, asserting the full `queued → running → completed|failed` lifecycle — run with sleep/failure-rate env vars shrunk for speed.
- Both run in CI as part of the `test` stage; deploy is gated on green.

## 10. Service Level Objectives (SLOs)

Measured against the metrics defined in §4.3, over the deployed single instance:

1. **Availability** — ≥99% of requests to `/healthz`, `/readyz`, `POST /jobs`, and `GET /jobs*` return a non-5xx status, measured over any rolling 24h window.
2. **Submission latency** — `POST /jobs` responds in <200ms at p95. It only validates and enqueues; it never waits on processing, so this should hold regardless of queue depth.
3. **Job turnaround** — ≥95% of submitted jobs reach a terminal state (`completed` or `failed`) within 60 seconds of submission under normal load (bounded by `MAX_ATTEMPTS × MOCK_MAX_SLEEP_SECONDS` plus queue wait time at the default config).

These are demo-scale targets to validate the design, not contractual production SLAs (see §5 — no HA/multi-instance, no persistence).

## 11. Milestone Plan (build one at a time, proceed through all without stopping for confirmation)

1. Skeleton FastAPI app + `/healthz`, `/readyz`, `/metrics`, structured logging middleware, config via env vars — runnable, deployable no-op.
2. Domain models, `JobRepository`/`JobQueue`/`JobProcessor` protocols, `MockProcessor`.
3. `JobService` + worker pool wired to app startup/shutdown (graceful SIGTERM drain).
4. `POST /jobs`, `GET /jobs/{id}`, `GET /jobs` routes + structured error handling.
5. Unit tests + the one API-level integration test.
6. Multi-stage Dockerfile, non-root.
7. CI pipeline (lint → test → build → deploy) + DO App Platform deployment.
