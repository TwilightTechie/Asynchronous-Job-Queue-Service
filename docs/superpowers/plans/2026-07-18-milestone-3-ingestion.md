# Milestone 3: Ingestion + Validation (`POST /jobs`)

> Implements `docs/plan.md`'s M3 section (T+90 → T+115). Builds the domain model, the `JobRepository` protocol + in-memory implementation, `JobService.submit_job`, and `POST /jobs` with structured `422` errors. **No queue, no worker pool, no `GET` routes** — those are M4. This keeps the layered architecture from `docs/requirements.md` §3 intact: routes → service → repository, with the repository behind a `Protocol` so M4 doesn't touch this milestone's code, only extends it.
>
> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `POST /jobs` validates the body, creates a `Job` in `queued` state, stores it, and returns `201` immediately — no processing occurs yet, no worker exists yet.

**Tech Stack:** builds on Milestone 1/2's FastAPI skeleton. No new dependencies.

## Global Constraints

(From `docs/requirements.md` §2.1, §3, §6, §7 and `docs/design.md` §5 — every task below implicitly includes these.)

- Request body: `{"type": "report"|"transcode"|"export", "input": {...}}`. `type` is a strict enum; `input` is a required JSON object, contents otherwise unvalidated.
- Success: `201 {"id": <uuid>, "status": "queued", "created_at": <iso8601>}`. The handler must not wait on processing — there is no processing yet.
- Invalid payload → `422` with `{"error": {"code": "invalid_request", "message": "..."}}` — one shared error shape, produced by a single exception handler, not scattered inline `HTTPException` calls.
- `Job` schema exactly as `docs/design.md` §5: `id: UUID, type: JobType, input: dict, status: JobStatus, result: dict | None, error: str | None, attempts: int, max_attempts: int, created_at: datetime, updated_at: datetime`.
- `JobRepository` is a `Protocol` (dependency inversion per `docs/requirements.md` §3) — only `save` and `get` are needed this milestone; `list` is added in M4 when `GET /jobs` needs it. Do not add it now.
- **No `JobQueue`, no worker pool, no `GET /jobs/{id}`, no `GET /jobs` in this milestone** — `docs/plan.md` M3 is explicit that consuming the job is M4's job. `JobService` this milestone has only `submit_job`.
- No auth, no persistence beyond the in-memory dict, no pagination (`docs/requirements.md` §5).
- `MAX_ATTEMPTS` (default `3`) becomes a real `Settings` field this milestone because `Job.max_attempts` is populated from it at creation time (`docs/requirements.md` §7).

---

## Task 1: Domain Models

**Files:**
- Create: `app/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `JobType(str, Enum)` (`REPORT`, `TRANSCODE`, `EXPORT`), `JobStatus(str, Enum)` (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`), `Job(BaseModel)` with the fields listed in Global Constraints. Used by every later task in this milestone.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
import uuid
from datetime import datetime, timezone

from app.models import Job, JobStatus, JobType


def test_job_type_values():
    assert JobType.REPORT == "report"
    assert JobType.TRANSCODE == "transcode"
    assert JobType.EXPORT == "export"


def test_job_status_values():
    assert JobStatus.QUEUED == "queued"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"


def test_job_construction_defaults():
    now = datetime.now(timezone.utc)
    job = Job(
        id=uuid.uuid4(),
        type=JobType.REPORT,
        input={"customer_id": "abc123"},
        status=JobStatus.QUEUED,
        result=None,
        error=None,
        attempts=0,
        max_attempts=3,
        created_at=now,
        updated_at=now,
    )
    assert job.status == JobStatus.QUEUED
    assert job.result is None
    assert job.error is None
    assert job.attempts == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 3: Write the implementation**

```python
# app/models.py
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class JobType(str, Enum):
    REPORT = "report"
    TRANSCODE = "transcode"
    EXPORT = "export"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(BaseModel):
    id: UUID
    type: JobType
    input: dict
    status: JobStatus
    result: dict | None
    error: str | None
    attempts: int
    max_attempts: int
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models.py
git commit -m "feat: add JobType, JobStatus, Job domain models"
```

---

## Task 2: JobRepository Protocol + InMemoryJobRepository

**Files:**
- Create: `app/repository.py`
- Test: `tests/test_repository.py`

**Interfaces:**
- Consumes: `Job` (Task 1).
- Produces: `class JobRepository(Protocol)` with `save(self, job: Job) -> None` and `get(self, job_id: UUID) -> Job | None`; `class InMemoryJobRepository` implementing it. Used by Task 5 (`JobService`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_repository.py
import uuid
from datetime import datetime, timezone

from app.models import Job, JobStatus, JobType
from app.repository import InMemoryJobRepository


def _make_job(**overrides) -> Job:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        type=JobType.REPORT,
        input={},
        status=JobStatus.QUEUED,
        result=None,
        error=None,
        attempts=0,
        max_attempts=3,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return Job(**defaults)


def test_save_then_get_returns_the_job():
    repo = InMemoryJobRepository()
    job = _make_job()

    repo.save(job)

    assert repo.get(job.id) == job


def test_get_unknown_id_returns_none():
    repo = InMemoryJobRepository()

    assert repo.get(uuid.uuid4()) is None


def test_save_overwrites_existing_job():
    repo = InMemoryJobRepository()
    job = _make_job()
    repo.save(job)

    updated = job.model_copy(update={"status": JobStatus.RUNNING})
    repo.save(updated)

    assert repo.get(job.id).status == JobStatus.RUNNING
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_repository.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.repository'`

- [ ] **Step 3: Write the implementation**

```python
# app/repository.py
from typing import Protocol
from uuid import UUID

from app.models import Job


class JobRepository(Protocol):
    def save(self, job: Job) -> None: ...

    def get(self, job_id: UUID) -> Job | None: ...


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[UUID, Job] = {}

    def save(self, job: Job) -> None:
        self._jobs[job.id] = job

    def get(self, job_id: UUID) -> Job | None:
        return self._jobs.get(job_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_repository.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add app/repository.py tests/test_repository.py
git commit -m "feat: add JobRepository protocol and in-memory implementation"
```

---

## Task 3: Config — `MAX_ATTEMPTS`

**Files:**
- Modify: `app/config.py`
- Modify: `tests/test_config.py`

**Interfaces:**
- Consumes: existing `Settings` (M1).
- Produces: `Settings.max_attempts: int` (default `3`, env var `MAX_ATTEMPTS`). Used by Task 5 (`JobService`).

- [ ] **Step 1: Write the failing test (append to existing file)**

```python
# tests/test_config.py — add these two test functions
def test_settings_max_attempts_default(monkeypatch):
    monkeypatch.delenv("MAX_ATTEMPTS", raising=False)

    settings = Settings()

    assert settings.max_attempts == 3


def test_settings_max_attempts_reads_env_var(monkeypatch):
    monkeypatch.setenv("MAX_ATTEMPTS", "5")

    settings = Settings()

    assert settings.max_attempts == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `AttributeError` / `ValidationError` referencing `max_attempts` not existing.

- [ ] **Step 3: Update the implementation**

```python
# app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8080
    max_attempts: int = 3


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add MAX_ATTEMPTS to Settings"
```

---

## Task 4: Request/Response Schemas

**Files:**
- Create: `app/schemas.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Consumes: `JobType`, `JobStatus` (Task 1).
- Produces: `JobCreateRequest(type: JobType, input: dict)`, `JobCreateResponse(id: UUID, status: JobStatus, created_at: datetime)`, `ErrorDetail(code: str, message: str)`, `ErrorResponse(error: ErrorDetail)`. Used by Task 6 (routes + error handler).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schemas.py
import pytest
from pydantic import ValidationError

from app.schemas import ErrorDetail, ErrorResponse, JobCreateRequest


def test_job_create_request_accepts_valid_payload():
    req = JobCreateRequest(type="report", input={"customer_id": "abc123"})
    assert req.type == "report"
    assert req.input == {"customer_id": "abc123"}


def test_job_create_request_rejects_invalid_type():
    with pytest.raises(ValidationError):
        JobCreateRequest(type="not-a-real-type", input={})


def test_job_create_request_requires_input():
    with pytest.raises(ValidationError):
        JobCreateRequest(type="report")


def test_error_response_shape():
    err = ErrorResponse(error=ErrorDetail(code="invalid_request", message="bad payload"))
    assert err.model_dump() == {"error": {"code": "invalid_request", "message": "bad payload"}}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.schemas'`

- [ ] **Step 3: Write the implementation**

```python
# app/schemas.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models import JobStatus, JobType


class JobCreateRequest(BaseModel):
    type: JobType
    input: dict


class JobCreateResponse(BaseModel):
    id: UUID
    status: JobStatus
    created_at: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_schemas.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add app/schemas.py tests/test_schemas.py
git commit -m "feat: add job create request/response and error schemas"
```

---

## Task 5: `JobService.submit_job`

**Files:**
- Create: `app/service.py`
- Test: `tests/test_service.py`

**Interfaces:**
- Consumes: `Job`, `JobType`, `JobStatus` (Task 1); `JobRepository` (Task 2).
- Produces: `class JobService` with `__init__(self, repository: JobRepository, max_attempts: int)` and `submit_job(self, job_type: JobType, input: dict) -> Job`. Used by Task 6 (routes).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_service.py
from app.models import JobStatus, JobType
from app.repository import InMemoryJobRepository
from app.service import JobService


def test_submit_job_creates_queued_job_with_configured_max_attempts():
    repo = InMemoryJobRepository()
    service = JobService(repository=repo, max_attempts=3)

    job = service.submit_job(JobType.REPORT, {"customer_id": "abc123"})

    assert job.type == JobType.REPORT
    assert job.input == {"customer_id": "abc123"}
    assert job.status == JobStatus.QUEUED
    assert job.attempts == 0
    assert job.max_attempts == 3
    assert job.result is None
    assert job.error is None
    assert job.created_at == job.updated_at


def test_submit_job_persists_to_repository():
    repo = InMemoryJobRepository()
    service = JobService(repository=repo, max_attempts=3)

    job = service.submit_job(JobType.EXPORT, {})

    assert repo.get(job.id) == job


def test_submit_job_generates_unique_ids():
    repo = InMemoryJobRepository()
    service = JobService(repository=repo, max_attempts=3)

    job1 = service.submit_job(JobType.TRANSCODE, {})
    job2 = service.submit_job(JobType.TRANSCODE, {})

    assert job1.id != job2.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.service'`

- [ ] **Step 3: Write the implementation**

```python
# app/service.py
import uuid
from datetime import datetime, timezone

from app.models import Job, JobStatus, JobType
from app.repository import JobRepository


class JobService:
    def __init__(self, repository: JobRepository, max_attempts: int) -> None:
        self._repository = repository
        self._max_attempts = max_attempts

    def submit_job(self, job_type: JobType, input: dict) -> Job:
        now = datetime.now(timezone.utc)
        job = Job(
            id=uuid.uuid4(),
            type=job_type,
            input=input,
            status=JobStatus.QUEUED,
            result=None,
            error=None,
            attempts=0,
            max_attempts=self._max_attempts,
            created_at=now,
            updated_at=now,
        )
        self._repository.save(job)
        return job
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_service.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add app/service.py tests/test_service.py
git commit -m "feat: add JobService.submit_job"
```

---

## Task 6: `POST /jobs` Route + Structured Error Handling + Wiring

**Files:**
- Create: `app/errors.py`
- Create: `app/routes/jobs.py`
- Modify: `app/main.py`
- Test: `tests/test_jobs_routes.py`

**Interfaces:**
- Consumes: `JobCreateRequest`, `JobCreateResponse` (Task 4); `JobService` (Task 5); `InMemoryJobRepository` (Task 2); `Settings` (Task 3).
- Produces: `install_exception_handlers(app: FastAPI) -> None`; `router: APIRouter` with `POST /jobs`. `create_app()` now constructs a repository + service and stores the service on `app.state.job_service`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_jobs_routes.py
from fastapi.testclient import TestClient

from app.main import create_app


def test_post_jobs_returns_201_with_id_status_created_at():
    client = TestClient(create_app())

    response = client.post("/jobs", json={"type": "report", "input": {"customer_id": "abc123"}})

    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"id", "status", "created_at"}
    assert body["status"] == "queued"


def test_post_jobs_does_not_wait_on_processing():
    client = TestClient(create_app())

    response = client.post("/jobs", json={"type": "transcode", "input": {}})

    assert response.status_code == 201


def test_post_jobs_invalid_type_returns_structured_422():
    client = TestClient(create_app())

    response = client.post("/jobs", json={"type": "not-a-real-type", "input": {}})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_request"
    assert "message" in body["error"]


def test_post_jobs_missing_input_returns_structured_422():
    client = TestClient(create_app())

    response = client.post("/jobs", json={"type": "report"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_jobs_routes.py -v`
Expected: FAIL — `404` (no `/jobs` route registered yet) or import errors.

- [ ] **Step 3: Write `app/errors.py`**

```python
# app/errors.py
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        message = "; ".join(str(err.get("msg", "")) for err in exc.errors()) or "invalid request"
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": "invalid_request", "message": message}},
        )
```

- [ ] **Step 4: Write `app/routes/jobs.py`**

```python
# app/routes/jobs.py
from fastapi import APIRouter, Request, status

from app.schemas import JobCreateRequest, JobCreateResponse

router = APIRouter()


@router.post("/jobs", status_code=status.HTTP_201_CREATED, response_model=JobCreateResponse)
async def create_job(payload: JobCreateRequest, request: Request) -> JobCreateResponse:
    job = request.app.state.job_service.submit_job(payload.type, payload.input)
    return JobCreateResponse(id=job.id, status=job.status, created_at=job.created_at)
```

- [ ] **Step 5: Update `app/main.py`**

```python
# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.errors import install_exception_handlers
from app.repository import InMemoryJobRepository
from app.routes.health import router as health_router
from app.routes.jobs import router as jobs_router
from app.service import JobService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.ready = True
        yield
        app.state.ready = False

    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings
    app.state.ready = False
    app.state.job_repository = InMemoryJobRepository()
    app.state.job_service = JobService(
        repository=app.state.job_repository, max_attempts=settings.max_attempts
    )
    install_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(jobs_router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=app.state.settings.port)
```

- [ ] **Step 6: Run the new tests**

Run: `pytest tests/test_jobs_routes.py -v`
Expected: `4 passed`

- [ ] **Step 7: Run the full suite and lint**

Run: `pytest -v`
Expected: all tests pass (M1's 7 + this milestone's ~17 new tests).

Run: `ruff check .`
Expected: `All checks passed!`

- [ ] **Step 8: Manually verify against a running server**

```bash
uvicorn app.main:app --port 8080 &
sleep 1
curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8080/jobs \
  -H "Content-Type: application/json" \
  -d '{"type": "report", "input": {"customer_id": "abc123"}}'
curl -s -X POST localhost:8080/jobs \
  -H "Content-Type: application/json" \
  -d '{"type": "not-a-real-type", "input": {}}'
kill %1
```
Expected: first call prints `201`; second prints a JSON body with `{"error": {"code": "invalid_request", ...}}`.

- [ ] **Step 9: Commit**

```bash
git add app/errors.py app/routes/jobs.py app/main.py tests/test_jobs_routes.py
git commit -m "feat: add POST /jobs with structured 422 error handling"
```
