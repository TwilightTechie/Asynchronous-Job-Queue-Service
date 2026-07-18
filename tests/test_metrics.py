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
