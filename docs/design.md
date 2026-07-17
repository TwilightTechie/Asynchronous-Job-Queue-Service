# Design — Asynchronous Job Queue Service

Companion to `docs/requirements.md` (functional requirements, SLOs, scope cuts, non-negotiables, milestone plan). This document fixes the concrete technical decisions: tech stack, deployment target, storage, data flow, and schema — and maps each non-negotiable to where it lives in the code.

## 1. Tech Stack

Kept deliberately small — every piece earns its place; nothing is added for hypothetical future needs.

| Concern | Choice | Why |
|---|---|---|
| Language/runtime | Python 3.12 | Readable, fast to write correctly under a 3-hour deadline. |
| Web framework | FastAPI (on Uvicorn, ASGI) | Native `async def` routes, Pydantic validation built in, generates OpenAPI for free. |
| Config | `pydantic-settings` | Typed env-var config, no hand-rolled `os.environ.get` parsing. |
| Queue | stdlib `asyncio.Queue` | In-process, zero extra infrastructure, zero network hops — the most efficient option for a single-instance service (see §3). |
| Job state store | in-memory `dict`, guarded by the single-threaded event loop | No `await` occurs between a read and its paired write in any repository method, so no locks are needed. Same reasoning as the queue: no external dependency to provision or fail. |
| Metrics | `prometheus-client` | Standard exposition format, no custom `/metrics` serialization. |
| Logging | stdlib `logging` + `json.dumps` | One dependency-free formatter; no logging framework needed for one JSON line per request. |
| Tests | `pytest` + `httpx` (via FastAPI `TestClient`) | Standard, no separate test runner. |
| Lint | `ruff` | Single fast tool covering lint + import order. |

Explicitly **not** used: Celery, Redis, RQ, Postgres/SQLite, Kubernetes, a task-queue-as-a-service. Each would add a network hop, a provisioning step, and a failure mode this service doesn't need at its current scope (single instance, in-memory queue — `docs/requirements.md` §5).

## 2. Deployment Target

**Primary: DigitalOcean App Platform, deployed via `git push`.**
App Platform detects the repo's Dockerfile, builds the image, and deploys it — no separate registry push, no reverse proxy or TLS setup to hand-roll. CI's deploy stage (`docs/requirements.md` §8) triggers a redeploy with `doctl apps create-deployment` after lint+test pass. This is the target the CI pipeline (Milestone 7) will implement first.

**Fallback: Droplet + Docker.**
If App Platform turns out not to fit (build-time limits, networking requirements, account constraints), the same multi-stage Dockerfile runs unchanged via `docker run` on a Droplet; only the deploy *step* in CI changes (SSH + `docker pull && docker run`, or `docker compose up -d`), not the application or Dockerfile. TLS/reverse proxy would then be the deployer's responsibility (e.g. Caddy or Nginx in front).

Which target is used is pending confirmation before Milestone 7 is built — the application code is identical either way, so this doesn't block Milestones 1–6.

## 3. Storage Choices

**No database. No object storage.**

- Job state (queue + status dict) is in-memory only, per the architecture in `docs/requirements.md` §3 — this is a deliberate scope cut (§5: no persistence, no horizontal scaling), not an oversight. A restart loses in-flight jobs; acceptable for a single-instance demo service.
- No DO Spaces (or any blob store) is needed because no job in this build produces a real file artifact. `report` / `transcode` / `export` are validated job *types*, but all route through `MockProcessor`, which returns an inline JSON `result` (e.g. `{"message": "...", "duration_seconds": 6.4}`) — never a file.
- **Future hook, not built now:** if a real processor were added that actually generates a file (a transcoded video, a PDF report), DO Spaces (S3-compatible) is the natural addition — `job.result` would then carry a Spaces object key/URL instead of inline JSON. Nothing in the current schema (§5) forecloses this; `result: dict` can hold either shape.

## 4. Data Flow (ASCII)

```
                 ┌────────────────────────────────────────────────────────────┐
                 │                      FastAPI process                        │
Client           │  HTTP layer              Service            Storage         │
  │              │                                                              │
  │ POST /jobs   │                                                              │
  ├─────────────►│  validate (Pydantic)                                        │
  │              │        │                                                    │
  │              │        ▼                                                    │
  │              │  JobService.submit_job()                                    │
  │              │        ├──► InMemoryJobRepository.save(job, status=queued)  │
  │              │        └──► asyncio.Queue.put(job.id)                       │
  │ 201 {id}     │◄───────┘   (returns immediately — decoupled from work)      │
  │◄─────────────┤                                                              │
  │              │   ┌────────────────────────────────────────────────────┐   │
  │              │   │            Worker pool (N asyncio tasks)            │   │
  │              │   │                                                     │   │
  │              │   │  loop:                                              │   │
  │              │   │    job_id = await queue.get()                       │   │
  │              │   │    repo.update(job_id, status=running)              │   │
  │              │   │    try: result = await MockProcessor.process(job)   │   │
  │              │   │         (sleep 2-10s, raises ~20% of the time)       │   │
  │              │   │    on success: repo.update(completed, result)       │   │
  │              │   │    on failure: attempts += 1                        │   │
  │              │   │      if attempts < max_attempts:                    │   │
  │              │   │          queue.put(job_id)          # retry         │   │
  │              │   │      else:                                          │   │
  │              │   │          repo.update(failed, error)                 │   │
  │              │   └────────────────────────────────────────────────────┘   │
  │              │                                                              │
  │ GET /jobs/id │                                                              │
  ├─────────────►│  JobService.get_job() ──► repo.get(id) ──► 200 job | 404    │
  │◄─────────────┤                                                              │
  │ GET /jobs?…  │                                                              │
  ├─────────────►│  JobService.list_jobs() ──► repo.list(status) ──► 200 jobs  │
  │◄─────────────┤                                                              │
                 └────────────────────────────────────────────────────────────┘
```

## 5. Schema

### Enums

```python
class JobType(str, Enum):
    REPORT = "report"
    TRANSCODE = "transcode"
    EXPORT = "export"

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

### Job entity

```python
class Job:
    id: UUID              # uuid4, generated on submission
    type: JobType
    input: dict            # caller-supplied, opaque to the service
    status: JobStatus
    result: dict | None    # set only when status == completed
    error: str | None      # set only when status == failed
    attempts: int          # attempts made so far
    max_attempts: int      # config MAX_ATTEMPTS, default 3
    created_at: datetime   # UTC
    updated_at: datetime   # UTC
```

### Wire formats

`POST /jobs` request:
```json
{"type": "report", "input": {"customer_id": "abc123"}}
```

`POST /jobs` response — `201`:
```json
{"id": "5b1b6e2a-...", "status": "queued", "created_at": "2026-07-17T12:00:00+00:00"}
```

`GET /jobs/{id}` response — `200`, completed:
```json
{
  "id": "5b1b6e2a-...",
  "type": "report",
  "input": {"customer_id": "abc123"},
  "status": "completed",
  "result": {"message": "report job completed", "duration_seconds": 6.42},
  "error": null,
  "attempts": 1,
  "max_attempts": 3,
  "created_at": "2026-07-17T12:00:00+00:00",
  "updated_at": "2026-07-17T12:00:07+00:00"
}
```

`GET /jobs/{id}` response — `200`, failed (attempts exhausted):
```json
{
  "id": "5b1b6e2a-...",
  "type": "export",
  "input": {"customer_id": "abc123"},
  "status": "failed",
  "result": null,
  "error": "mock processing failed after 3 attempt(s)",
  "attempts": 3,
  "max_attempts": 3,
  "created_at": "2026-07-17T12:00:00+00:00",
  "updated_at": "2026-07-17T12:00:24+00:00"
}
```

`GET /jobs/{id}` response — `404`:
```json
{"error": {"code": "job_not_found", "message": "No job with id 5b1b6e2a-..."}}
```

`POST /jobs` response — `422`, invalid type:
```json
{"error": {"code": "invalid_request", "message": "type must be one of: report, transcode, export"}}
```

`GET /jobs?status=failed` response — `200`:
```json
{"jobs": [ { "...": "job object as above" } ]}
```

## 6. Non-Negotiables — How Each Is Satisfied

| Non-negotiable | How it's satisfied | Where (per the Milestone 1 plan / roadmap) |
|---|---|---|
| `/healthz` | Always returns `200` while the process is up — no dependency checks. | `app/routes/health.py` |
| `/readyz` | Returns `200` only once `app.state.ready` is `True`; `503` otherwise. Set by the FastAPI lifespan; Milestone 3 extends this to also require the worker pool to have started. | `app/routes/health.py`, lifespan in `app/main.py` |
| Prometheus `/metrics` | `http_requests_total{method,route,status}` counter + `http_request_duration_seconds` histogram (RED) recorded by the observability middleware on every request; job-domain metrics (`jobs_submitted_total`, `jobs_completed_total`, `jobs_failed_total`, `job_queue_depth`, `job_processing_duration_seconds`) added in Milestone 3 once jobs exist. | `app/routes/metrics.py`, `app/observability/metrics.py` |
| JSON structured logs `{ts, req_id, route, status, dur_ms}` | Emitted once per request by `ObservabilityMiddleware`, which times the request, resolves the matched route template, and logs via `log_request()`. | `app/middleware.py`, `app/observability/logging.py` |
| Input validation, structured JSON errors, correct status codes | Request/response bodies are Pydantic models (job `type` is a strict enum); a single FastAPI exception handler maps domain exceptions to `{"error": {"code", "message"}}` with the right status (`422` invalid payload/filter, `404` unknown job) — no scattered inline `HTTPException` calls. | `app/schemas.py`, exception handler in `app/main.py` (Milestone 4) |
| Graceful shutdown on SIGTERM (drain ≤30s) | Uvicorn stops accepting new connections on SIGTERM; the lifespan's shutdown phase flips `app.state.ready = False` and signals workers to stop pulling new jobs from the queue while letting in-flight jobs finish (bounded by 2–10s mock work, well under the 30s budget). | lifespan in `app/main.py`, worker loop (Milestone 3) |
| Config via env vars | All tunables (`PORT`, `WORKER_POOL_SIZE`, `MAX_ATTEMPTS`, `MOCK_MIN_SLEEP_SECONDS`, `MOCK_MAX_SLEEP_SECONDS`, `MOCK_FAILURE_RATE`, `LOG_LEVEL`) are fields on a `pydantic-settings` `Settings` class — no hardcoded values. | `app/config.py` |
| Multi-stage Dockerfile, non-root | Build stage installs dependencies; runtime stage copies only the app + installed packages, runs as a non-root `USER`. | `Dockerfile` (Milestone 6) |
| CI: lint → test → build → deploy | GitHub Actions runs `ruff check` → `pytest` on every push/PR; on `main`, only after both are green, it builds the Docker image and triggers the deploy step against the confirmed target (§2). A red lint/test stage blocks deploy. | `.github/workflows/ci.yml` (Milestone 7) |
| Tests: unit + one API-level integration test, run in CI | Per-module unit tests (config, logging, metrics, middleware, routes) plus one `TestClient`-driven integration test that drives a job through `queued → running → completed|failed`, with mock sleep/failure-rate shrunk via env vars for speed. All run in CI's test stage. | `tests/`, Milestone 1 plan (`docs/superpowers/plans/2026-07-17-milestone-1-skeleton-app.md`) §Tasks 2–8, extended in Milestone 5 |
