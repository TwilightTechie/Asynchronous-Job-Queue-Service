# Milestone 6: Test Suite Completion

> Implements `docs/plan.md`'s M6 section (T+155 → T+170). Per its definition of done: "fills in the unit test suite left implicit in M1–M5 ... no code changes needed to make it pass (tests describe what M1–M5 already built)." Every task across M1-M5 was built TDD-first with its own dedicated test file (68 tests currently passing, covering config, logging, RED+job-domain metrics, middleware including the exception path, health/status routes, domain models, repository, schemas, `JobService` including retry state-machine transitions, the worker loop including retry-then-fail, and all `/jobs*` routes including structured error shapes). The one deliberate gap against `docs/requirements.md` §9's testing strategy is the required **API-level integration test**: `TestClient` posting a job and polling `GET /jobs/{id}` until a terminal state, exercising the full `queued → running → completed|failed` lifecycle through the real HTTP layer (not by calling `JobService` methods directly, which is what `tests/test_worker.py` already does).
>
> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One passing test proves the full job lifecycle works end-to-end through the actual FastAPI app (routes → service → queue → worker → repository), for both the success and retry-exhaustion paths, with mock sleep/failure-rate shrunk via `Settings` injection so it runs in milliseconds.

**Global Constraints:**
- No production code changes in this milestone — if this test fails, that's a bug to report, not something to work around.
- Must drive the real HTTP layer via `TestClient`, not call `JobService`/`InMemoryJobRepository` directly.
- Must use `with TestClient(app):` (context-manager form) so the app's lifespan actually runs and the worker pool is live during the test.

---

## Task 1: API-Level Integration Test (Full Job Lifecycle)

**Files:**
- Create: `tests/test_integration_lifecycle.py`

**Interfaces:**
- Consumes: `create_app`, `Settings` (existing).
- Produces: two integration tests proving the full lifecycle for both terminal outcomes.

- [ ] **Step 1: Write the test**

```python
# tests/test_integration_lifecycle.py
import time

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _poll_until_terminal(client: TestClient, job_id: str, attempts: int = 100) -> dict:
    for _ in range(attempts):
        body = client.get(f"/jobs/{job_id}").json()
        if body["status"] in ("completed", "failed"):
            return body
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} did not reach a terminal state in time")


def test_job_lifecycle_completes_end_to_end_via_http():
    settings = Settings(
        mock_min_sleep_seconds=0.01,
        mock_max_sleep_seconds=0.02,
        mock_failure_rate=0.0,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        create_response = client.post(
            "/jobs", json={"type": "report", "input": {"customer_id": "abc123"}}
        )
        assert create_response.status_code == 201
        job_id = create_response.json()["id"]
        assert create_response.json()["status"] == "queued"

        body = _poll_until_terminal(client, job_id)

        assert body["status"] == "completed"
        assert body["result"] is not None
        assert body["error"] is None
        assert body["attempts"] == 1


def test_job_lifecycle_fails_after_exhausting_retries_via_http():
    settings = Settings(
        mock_min_sleep_seconds=0.01,
        mock_max_sleep_seconds=0.02,
        mock_failure_rate=1.0,
        max_attempts=2,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        create_response = client.post("/jobs", json={"type": "export", "input": {}})
        job_id = create_response.json()["id"]

        body = _poll_until_terminal(client, job_id)

        assert body["status"] == "failed"
        assert body["result"] is None
        assert body["error"] is not None
        assert body["attempts"] == 2
```

- [ ] **Step 2: Run test to verify it passes (no implementation step — this exercises existing code only)**

Run: `pytest tests/test_integration_lifecycle.py -v`
Expected: `2 passed`

- [ ] **Step 3: Run the full suite and lint**

Run: `pytest -v`
Expected: all tests pass (68 existing + 2 new = 70).

Run: `ruff check .`
Expected: `All checks passed!`

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration_lifecycle.py
git commit -m "test: add API-level integration test for full job lifecycle"
```
