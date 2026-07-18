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
