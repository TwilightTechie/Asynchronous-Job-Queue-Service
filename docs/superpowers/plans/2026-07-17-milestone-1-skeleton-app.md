# Milestone 1: Skeleton App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a runnable, deployable-shape FastAPI skeleton with `/healthz`, `/readyz`, Prometheus `/metrics`, structured JSON request logging, and env-var config — no job queue logic yet (that's Milestones 2–4).

**Architecture:** A FastAPI app assembled by a `create_app()` factory in `app/main.py`. Cross-cutting concerns (logging, metrics) live under `app/observability/` and are wired together by a single `ObservabilityMiddleware`. Health/readiness and metrics are plain `APIRouter`s under `app/routes/`. Readiness is tracked via `app.state.ready`, toggled by the FastAPI lifespan context — this is the same mechanism Milestone 3 will extend to gate on worker-pool startup.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, `pydantic-settings` (env-var config), `prometheus-client` (metrics), stdlib `logging` (JSON log lines), `pytest` + `httpx` (tests), `ruff` (lint).

## Global Constraints

(Copied from `docs/requirements.md` — every task below implicitly includes these.)

- Config via env vars only — no hardcoded ports or tunables (`docs/requirements.md` §7).
- `/healthz` returns `200` whenever the process is up (`docs/requirements.md` §4.1).
- `/readyz` returns `200` once the app is ready, `503` otherwise (`docs/requirements.md` §4.2).
- `/metrics` exposes Prometheus RED metrics: `http_requests_total{method,route,status}` counter and `http_request_duration_seconds` histogram (`docs/requirements.md` §4.3). Job-domain metrics (`jobs_submitted_total`, etc.) are added in a later milestone once jobs exist — do not add them here.
- One structured JSON log line per request with exactly the keys `ts, req_id, route, status, dur_ms` (`docs/requirements.md` §4.4).
- No authentication, no persistence, no pagination (`docs/requirements.md` §5 — explicit scope cuts).
- **This plan is Milestone 1 only** (`docs/requirements.md` §11). Graceful SIGTERM shutdown drain, the multi-stage Dockerfile, and the CI pipeline are separate, later milestones — do not build them in this plan.

---

### Task 1: Project Scaffolding & Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `pyproject.toml`
- Create: `conftest.py`
- Create: `.python-version`
- Create: `app/__init__.py`
- Create: `app/observability/__init__.py`
- Create: `app/routes/__init__.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: an installable, lintable, testable project skeleton. No code interfaces — later tasks import from `app.*` once those modules exist.

- [ ] **Step 1: Create the package directories and empty `__init__.py` files**

```bash
mkdir -p app/observability app/routes tests
touch app/__init__.py app/observability/__init__.py app/routes/__init__.py
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic-settings==2.6.0
prometheus-client==0.21.0
```

- [ ] **Step 3: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest==8.3.3
httpx==0.27.2
ruff==0.7.1
```

- [ ] **Step 4: Create `pyproject.toml`**

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 5: Create `.python-version`**

```
3.12
```

- [ ] **Step 6: Create root `conftest.py`**

This file has no test code — its presence causes pytest to add the project root to `sys.path`, which is what makes `import app.main` work from files under `tests/`.

```python
# Empty on purpose: presence of this file adds the project root to sys.path for pytest.
```

- [ ] **Step 7: Create venv and install dependencies**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

- [ ] **Step 8: Verify dependencies import correctly**

Run: `python -c "import fastapi, uvicorn, pydantic_settings, prometheus_client; print('deps-ok')"`
Expected: `deps-ok`

- [ ] **Step 9: Verify ruff runs clean on the empty skeleton**

Run: `ruff check .`
Expected: `All checks passed!`

- [ ] **Step 10: Verify pytest runs (no tests yet)**

Run: `pytest`
Expected: exits with `no tests ran` (pytest exit code 5 — expected at this point, not a failure)

- [ ] **Step 11: Commit**

```bash
git add requirements.txt requirements-dev.txt pyproject.toml conftest.py .python-version app/__init__.py app/observability/__init__.py app/routes/__init__.py
git commit -m "chore: scaffold Python project (deps, lint, test config)"
```

---

### Task 2: Config via Env Vars

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `class Settings(BaseSettings)` with fields `port: int` (default `8080`), `log_level: str` (default `"INFO"`); function `get_settings() -> Settings`. Used by Task 8 (`app/main.py`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from app.config import Settings, get_settings


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings()

    assert settings.port == 8080
    assert settings.log_level == "INFO"


def test_settings_reads_env_vars(monkeypatch):
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings()

    assert settings.port == 9090
    assert settings.log_level == "DEBUG"


def test_get_settings_returns_settings_instance():
    assert isinstance(get_settings(), Settings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 3: Write the implementation**

```python
# app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8080
    log_level: str = "INFO"


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add env-var backed Settings"
```

---

### Task 3: Structured JSON Request Logging

**Files:**
- Create: `app/observability/logging.py`
- Test: `tests/test_logging.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `configure_logging(log_level: str) -> logging.Logger` (logger name `"app.request"`); `log_request(logger: logging.Logger, *, ts: str, req_id: str, route: str, status_code: int, dur_ms: float) -> None`. Used by Task 5 (`ObservabilityMiddleware`) and Task 8 (`app/main.py`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_logging.py
import json
import logging

from app.observability.logging import configure_logging, log_request


def test_log_request_emits_one_json_line_with_expected_keys(caplog):
    logger = configure_logging("INFO")

    with caplog.at_level(logging.INFO, logger="app.request"):
        log_request(
            logger,
            ts="2026-07-17T00:00:00+00:00",
            req_id="test-req-id",
            route="/healthz",
            status_code=200,
            dur_ms=12.34,
        )

    assert len(caplog.records) == 1
    payload = json.loads(caplog.records[0].getMessage())
    assert payload == {
        "ts": "2026-07-17T00:00:00+00:00",
        "req_id": "test-req-id",
        "route": "/healthz",
        "status": 200,
        "dur_ms": 12.34,
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_logging.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.observability.logging'`

- [ ] **Step 3: Write the implementation**

```python
# app/observability/logging.py
import json
import logging
import sys


def configure_logging(log_level: str) -> logging.Logger:
    logger = logging.getLogger("app.request")
    logger.setLevel(log_level)
    logger.handlers = [logging.StreamHandler(sys.stdout)]
    logger.propagate = False
    return logger


def log_request(
    logger: logging.Logger,
    *,
    ts: str,
    req_id: str,
    route: str,
    status_code: int,
    dur_ms: float,
) -> None:
    logger.info(
        json.dumps(
            {
                "ts": ts,
                "req_id": req_id,
                "route": route,
                "status": status_code,
                "dur_ms": round(dur_ms, 2),
            }
        )
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_logging.py -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add app/observability/logging.py tests/test_logging.py
git commit -m "feat: add structured JSON request logging"
```

---

### Task 4: Prometheus RED Metrics

**Files:**
- Create: `app/observability/metrics.py`
- Test: `tests/test_metrics.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `record_request(method: str, route: str, status_code: int, duration_seconds: float) -> None`, backed by module-level `REQUEST_COUNT` (`Counter`, name `http_requests_total`, labels `method,route,status`) and `REQUEST_LATENCY` (`Histogram`, name `http_request_duration_seconds`, labels `method,route`) on the default `prometheus_client` registry. Used by Task 5 (`ObservabilityMiddleware`) and read by Task 7 (`/metrics` route).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metrics.py
from prometheus_client import REGISTRY

from app.observability.metrics import record_request


def test_record_request_increments_counter_and_observes_latency():
    before = (
        REGISTRY.get_sample_value(
            "http_requests_total",
            {"method": "GET", "route": "/test-record-request", "status": "200"},
        )
        or 0.0
    )

    record_request("GET", "/test-record-request", 200, 0.05)

    after = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": "GET", "route": "/test-record-request", "status": "200"},
    )
    assert after == before + 1.0

    count = REGISTRY.get_sample_value(
        "http_request_duration_seconds_count",
        {"method": "GET", "route": "/test-record-request"},
    )
    assert count is not None and count >= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_metrics.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.observability.metrics'`

- [ ] **Step 3: Write the implementation**

```python
# app/observability/metrics.py
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route"],
)


def record_request(method: str, route: str, status_code: int, duration_seconds: float) -> None:
    REQUEST_COUNT.labels(method=method, route=route, status=str(status_code)).inc()
    REQUEST_LATENCY.labels(method=method, route=route).observe(duration_seconds)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_metrics.py -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add app/observability/metrics.py tests/test_metrics.py
git commit -m "feat: add Prometheus RED metrics recorder"
```

---

### Task 5: Observability Middleware

**Files:**
- Create: `app/middleware.py`
- Test: `tests/test_middleware.py`

**Interfaces:**
- Consumes: `configure_logging`, `log_request` from `app.observability.logging` (Task 3); `record_request` from `app.observability.metrics` (Task 4).
- Produces: `class ObservabilityMiddleware(BaseHTTPMiddleware)` with `__init__(self, app, logger: logging.Logger)`. Used by Task 8 (`app/main.py`) via `app.add_middleware(ObservabilityMiddleware, logger=logger)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_middleware.py
import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.middleware import ObservabilityMiddleware
from app.observability.logging import configure_logging


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/dummy-mw-route")
    async def dummy() -> dict:
        return {"ok": True}

    logger = configure_logging("INFO")
    app.add_middleware(ObservabilityMiddleware, logger=logger)
    return app


def test_middleware_records_metrics_logs_and_sets_request_id(caplog):
    client = TestClient(_build_app())

    before = (
        REGISTRY.get_sample_value(
            "http_requests_total",
            {"method": "GET", "route": "/dummy-mw-route", "status": "200"},
        )
        or 0.0
    )

    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/dummy-mw-route")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    after = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": "GET", "route": "/dummy-mw-route", "status": "200"},
    )
    assert after == before + 1.0

    assert len(caplog.records) == 1
    payload = json.loads(caplog.records[0].getMessage())
    assert payload["route"] == "/dummy-mw-route"
    assert payload["status"] == 200
    assert payload["req_id"] == response.headers["X-Request-ID"]
    assert payload["dur_ms"] >= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_middleware.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.middleware'`

- [ ] **Step 3: Write the implementation**

```python
# app/middleware.py
import logging
import time
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.observability.logging import log_request
from app.observability.metrics import record_request


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start = time.perf_counter()

        response = await call_next(request)

        duration_seconds = time.perf_counter() - start
        route = request.scope.get("route")
        route_path = route.path if route is not None else request.url.path

        record_request(request.method, route_path, response.status_code, duration_seconds)
        log_request(
            self.logger,
            ts=datetime.now(timezone.utc).isoformat(),
            req_id=req_id,
            route=route_path,
            status_code=response.status_code,
            dur_ms=duration_seconds * 1000,
        )

        response.headers["X-Request-ID"] = req_id
        return response
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_middleware.py -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add app/middleware.py tests/test_middleware.py
git commit -m "feat: add observability middleware (logging + metrics + request id)"
```

---

### Task 6: Health & Readiness Routes

**Files:**
- Create: `app/routes/health.py`
- Test: `tests/test_health_routes.py`

**Interfaces:**
- Consumes: `request.app.state.ready: bool` (set by Task 8's lifespan).
- Produces: `router: APIRouter` with `GET /healthz` (always `200`) and `GET /readyz` (`200` if `app.state.ready` else `503`). Used by Task 8 (`app/main.py`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_health_routes.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.health import router as health_router


def _build_app(ready: bool) -> FastAPI:
    app = FastAPI()
    app.state.ready = ready
    app.include_router(health_router)
    return app


def test_healthz_returns_200_regardless_of_readiness():
    client = TestClient(_build_app(ready=False))
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_returns_200_when_ready():
    client = TestClient(_build_app(ready=True))
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readyz_returns_503_when_not_ready():
    client = TestClient(_build_app(ready=False))
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_health_routes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.routes.health'`

- [ ] **Step 3: Write the implementation**

```python
# app/routes/health.py
from fastapi import APIRouter, Request, Response, status

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request, response: Response) -> dict:
    if not request.app.state.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready"}
    return {"status": "ready"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_health_routes.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add app/routes/health.py tests/test_health_routes.py
git commit -m "feat: add /healthz and /readyz routes"
```

---

### Task 7: Prometheus `/metrics` Route

**Files:**
- Create: `app/routes/metrics.py`
- Test: `tests/test_metrics_route.py`

**Interfaces:**
- Consumes: `prometheus_client.generate_latest()` reading the same default registry Task 4's `record_request` writes to.
- Produces: `router: APIRouter` with `GET /metrics` returning Prometheus exposition text. Used by Task 8 (`app/main.py`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metrics_route.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.observability.metrics import record_request
from app.routes.metrics import router as metrics_router


def test_metrics_endpoint_exposes_prometheus_text():
    record_request("GET", "/test-metrics-route", 200, 0.01)

    app = FastAPI()
    app.include_router(metrics_router)
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert (
        'http_requests_total{method="GET",route="/test-metrics-route",status="200"}'
        in response.text
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_metrics_route.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.routes.metrics'`

- [ ] **Step 3: Write the implementation**

```python
# app/routes/metrics.py
from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter()


@router.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_metrics_route.py -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add app/routes/metrics.py tests/test_metrics_route.py
git commit -m "feat: add /metrics route"
```

---

### Task 8: App Factory — Wire Everything Together

**Files:**
- Create: `app/main.py`
- Create: `README.md`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `Settings`, `get_settings` (Task 2); `configure_logging` (Task 3); `ObservabilityMiddleware` (Task 5); `health_router` (Task 6); `metrics_router` (Task 7).
- Produces: `create_app(settings: Settings | None = None) -> FastAPI`; module-level `app = create_app()` as the ASGI entry point (`app.main:app`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_main.py
import json
import logging

from fastapi.testclient import TestClient

from app.main import create_app


def test_app_skeleton_end_to_end(caplog):
    app = create_app()

    with TestClient(app) as client:
        assert app.state.ready is True

        assert client.get("/healthz").status_code == 200
        assert client.get("/readyz").status_code == 200

        with caplog.at_level(logging.INFO, logger="app.request"):
            client.get("/healthz")

        assert any(
            json.loads(r.getMessage())["route"] == "/healthz" for r in caplog.records
        )

        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        assert 'route="/healthz"' in metrics_response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Write the implementation**

```python
# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.middleware import ObservabilityMiddleware
from app.observability.logging import configure_logging
from app.routes.health import router as health_router
from app.routes.metrics import router as metrics_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logger = configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.ready = True
        yield
        app.state.ready = False

    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings
    app.state.ready = False
    app.add_middleware(ObservabilityMiddleware, logger=logger)
    app.include_router(health_router)
    app.include_router(metrics_router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=app.state.settings.port)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: `1 passed`

- [ ] **Step 5: Run the full test suite and lint**

Run: `pytest -v`
Expected: `11 passed` (3 in test_config.py + 1 in test_logging.py + 1 in test_metrics.py + 1 in test_middleware.py + 3 in test_health_routes.py + 1 in test_metrics_route.py + 1 in test_main.py)

Run: `ruff check .`
Expected: `All checks passed!`

- [ ] **Step 6: Create `README.md`**

```markdown
# Asynchronous Job Queue Service

## Local development

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

uvicorn app.main:app --reload --port 8080

Then in another terminal:

curl localhost:8080/healthz
curl localhost:8080/readyz
curl localhost:8080/metrics

## Tests

pytest
ruff check .
```

- [ ] **Step 7: Manually verify the server runs**

Run: `uvicorn app.main:app --port 8080 &`
Then: `curl -s localhost:8080/healthz`
Expected: `{"status":"ok"}`
Then: `curl -s localhost:8080/readyz`
Expected: `{"status":"ready"}`
Then: `curl -s localhost:8080/metrics | grep http_requests_total`
Expected: at least one `http_requests_total{...}` line
Then stop the server: `kill %1`

- [ ] **Step 8: Commit**

```bash
git add app/main.py README.md tests/test_main.py
git commit -m "feat: wire skeleton app together (Milestone 1 complete)"
```
