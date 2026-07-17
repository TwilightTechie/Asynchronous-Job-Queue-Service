# Milestone 1 (adapted): Walking Skeleton — Health Endpoints Only

> Supersedes `docs/superpowers/plans/2026-07-17-milestone-1-skeleton-app.md` for M1 scope, per `docs/plan.md`'s explicit split: structured logging, Prometheus metrics, and the observability middleware move to M5. This file is M1 only — health/readiness endpoints, env-var config, and a container-ready Dockerfile — matching `docs/plan.md`'s M1 section (T+0 → T+40).
>
> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A runnable, deployable-shape FastAPI skeleton with `/healthz`, `/readyz`, and `PORT` read from env var — plus a multi-stage, non-root Dockerfile so M2 can deploy it as-is. No logging, no metrics, no job queue logic yet.

**Architecture:** A FastAPI app assembled by a `create_app()` factory in `app/main.py`. Readiness is tracked via `app.state.ready`, toggled by the FastAPI lifespan — the same mechanism M4 extends to gate on worker-pool startup, and M5 extends with logging/metrics middleware.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, `pydantic-settings` (env-var config), `pytest` + `httpx` (tests), `ruff` (lint).

## Global Constraints

(From `docs/requirements.md` and `docs/plan.md` M1 — every task below implicitly includes these.)

- Config via env vars only — no hardcoded ports (`docs/requirements.md` §7). Only `PORT` exists as a setting in this milestone; other env vars (`WORKER_POOL_SIZE`, `LOG_LEVEL`, etc.) are added in later milestones when the code that needs them exists — do not add unused settings fields now.
- `/healthz` returns `200` whenever the process is up (`docs/requirements.md` §4.1).
- `/readyz` returns `200` once the app is ready, `503` otherwise (`docs/requirements.md` §4.2).
- **No logging, no metrics, no middleware in this milestone.** `prometheus-client` is not a dependency yet. Those are M5 (`docs/plan.md`).
- No authentication, no persistence, no pagination, no job queue (`docs/requirements.md` §5 — explicit scope cuts; job queue is M3/M4).
- Dockerfile: multi-stage (build stage installs deps, runtime stage copies only runtime artifacts), runs as a non-root user, reads `PORT` from env at runtime (`docs/requirements.md` §4.8).
- Definition of done (`docs/plan.md` M1): `docker build` succeeds; the container runs and serves both routes on the configured port.

---

## Task 1: Project Scaffolding & Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `pyproject.toml`
- Create: `conftest.py`
- Create: `.python-version`
- Create: `.dockerignore`
- Create: `app/__init__.py`
- Create: `app/routes/__init__.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: an installable, lintable, testable project skeleton. No code interfaces — later tasks import from `app.*` once those modules exist.

- [ ] **Step 1: Create the package directories and empty `__init__.py` files**

```bash
mkdir -p app/routes tests
touch app/__init__.py app/routes/__init__.py
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic-settings==2.6.0
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

- [ ] **Step 7: Create `.dockerignore`**

```
.venv
__pycache__
*.pyc
.git
.pytest_cache
tests
.ruff_cache
```

- [ ] **Step 8: Create venv and install dependencies**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

- [ ] **Step 9: Verify dependencies import correctly**

Run: `python -c "import fastapi, uvicorn, pydantic_settings; print('deps-ok')"`
Expected: `deps-ok`

- [ ] **Step 10: Verify ruff runs clean on the empty skeleton**

Run: `ruff check .`
Expected: `All checks passed!`

- [ ] **Step 11: Verify pytest runs (no tests yet)**

Run: `pytest`
Expected: exits with `no tests ran` (pytest exit code 5 — expected at this point, not a failure)

- [ ] **Step 12: Commit**

```bash
git add requirements.txt requirements-dev.txt pyproject.toml conftest.py .python-version .dockerignore app/__init__.py app/routes/__init__.py
git commit -m "chore: scaffold Python project (deps, lint, test config)"
```

---

## Task 2: Config via Env Vars

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `class Settings(BaseSettings)` with field `port: int` (default `8080`); function `get_settings() -> Settings`. Used by Task 4 (`app/main.py`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from app.config import Settings, get_settings


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)

    settings = Settings()

    assert settings.port == 8080


def test_settings_reads_env_vars(monkeypatch):
    monkeypatch.setenv("PORT", "9090")

    settings = Settings()

    assert settings.port == 9090


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


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add env-var backed Settings (PORT)"
```

---

## Task 3: Health & Readiness Routes

**Files:**
- Create: `app/routes/health.py`
- Test: `tests/test_health_routes.py`

**Interfaces:**
- Consumes: `request.app.state.ready: bool` (set by Task 4's lifespan).
- Produces: `router: APIRouter` with `GET /healthz` (always `200`) and `GET /readyz` (`200` if `app.state.ready` else `503`). Used by Task 4 (`app/main.py`).

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

## Task 4: App Factory — Wire Together

**Files:**
- Create: `app/main.py`
- Create: `README.md`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `Settings`, `get_settings` (Task 2); `health_router` (Task 3).
- Produces: `create_app(settings: Settings | None = None) -> FastAPI`; module-level `app = create_app()` as the ASGI entry point (`app.main:app`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_main.py
from fastapi.testclient import TestClient

from app.main import create_app


def test_app_skeleton_end_to_end():
    app = create_app()

    with TestClient(app) as client:
        assert app.state.ready is True

        healthz = client.get("/healthz")
        assert healthz.status_code == 200
        assert healthz.json() == {"status": "ok"}

        readyz = client.get("/readyz")
        assert readyz.status_code == 200
        assert readyz.json() == {"status": "ready"}
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
from app.routes.health import router as health_router


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
    app.include_router(health_router)
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
Expected: `7 passed` (3 in test_config.py + 3 in test_health_routes.py + 1 in test_main.py)

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

## Tests

pytest
ruff check .

## Docker

docker build -t jobqueue .
docker run -d -p 8080:8080 --name jobqueue jobqueue
curl localhost:8080/healthz
docker rm -f jobqueue
```

- [ ] **Step 7: Manually verify the server runs**

Run: `uvicorn app.main:app --port 8080 &`
Then: `curl -s localhost:8080/healthz`
Expected: `{"status":"ok"}`
Then: `curl -s localhost:8080/readyz`
Expected: `{"status":"ready"}`
Then stop the server: `kill %1`

- [ ] **Step 8: Commit**

```bash
git add app/main.py README.md tests/test_main.py
git commit -m "feat: wire skeleton app together"
```

---

## Task 5: Multi-Stage, Non-Root Dockerfile

**Files:**
- Create: `Dockerfile`

**Interfaces:**
- Consumes: `requirements.txt`, `app/` (Tasks 1-4).
- Produces: a container image that runs `app.main:app` via uvicorn, reading `PORT` from the environment, as a non-root user.

- [ ] **Step 1: Write the Dockerfile**

```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.12-slim AS build

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime

RUN useradd --create-home --shell /usr/sbin/nologin appuser
WORKDIR /app

COPY --from=build /install /usr/local
COPY app/ ./app/

USER appuser

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

- [ ] **Step 2: Build the image**

Run: `docker build -t jobqueue .`
Expected: build succeeds, ends with `naming to docker.io/library/jobqueue`

- [ ] **Step 3: Run the container and verify both routes**

```bash
docker run -d -p 8080:8080 --name jobqueue-m1 jobqueue
sleep 1
curl -s localhost:8080/healthz
curl -s localhost:8080/readyz
docker rm -f jobqueue-m1
```
Expected: `{"status":"ok"}` then `{"status":"ready"}`.

- [ ] **Step 4: Verify the process runs as non-root**

```bash
docker run -d -p 8080:8080 --name jobqueue-m1 jobqueue
docker exec jobqueue-m1 whoami
docker rm -f jobqueue-m1
```
Expected: `appuser` (not `root`).

- [ ] **Step 5: Verify `PORT` is respected**

```bash
docker run -d -p 9090:9090 -e PORT=9090 --name jobqueue-m1 jobqueue
sleep 1
curl -s localhost:9090/healthz
docker rm -f jobqueue-m1
```
Expected: `{"status":"ok"}`.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile
git commit -m "chore: add multi-stage, non-root Dockerfile"
```
