from prometheus_client import REGISTRY

from app.observability.metrics import (
    record_job_completed,
    record_job_failed,
    record_job_submitted,
    record_request,
    set_queue_depth,
)


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


def test_record_job_submitted_increments_counter():
    from app.observability.metrics import JOBS_SUBMITTED

    before = JOBS_SUBMITTED._value.get()
    record_job_submitted()
    assert JOBS_SUBMITTED._value.get() == before + 1


def test_record_job_completed_increments_counter_and_observes_duration():
    from app.observability.metrics import JOBS_COMPLETED

    before = JOBS_COMPLETED._value.get()
    record_job_completed(1.5)
    assert JOBS_COMPLETED._value.get() == before + 1

    count = REGISTRY.get_sample_value("job_processing_duration_seconds_count")
    assert count is not None and count >= 1.0


def test_record_job_failed_increments_counter():
    from app.observability.metrics import JOBS_FAILED

    before = JOBS_FAILED._value.get()
    record_job_failed()
    assert JOBS_FAILED._value.get() == before + 1


def test_set_queue_depth_sets_gauge_value():
    set_queue_depth(3)
    assert REGISTRY.get_sample_value("job_queue_depth") == 3.0
