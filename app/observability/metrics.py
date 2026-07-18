from prometheus_client import Counter, Gauge, Histogram

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

JOBS_SUBMITTED = Counter("jobs_submitted_total", "Total jobs submitted")
JOBS_COMPLETED = Counter("jobs_completed_total", "Total jobs completed successfully")
JOBS_FAILED = Counter("jobs_failed_total", "Total jobs that failed after exhausting retries")
JOB_QUEUE_DEPTH = Gauge("job_queue_depth", "Current number of jobs waiting in the queue")
JOB_PROCESSING_DURATION = Histogram(
    "job_processing_duration_seconds", "Job processing duration in seconds"
)


def record_request(method: str, route: str, status_code: int, duration_seconds: float) -> None:
    REQUEST_COUNT.labels(method=method, route=route, status=str(status_code)).inc()
    REQUEST_LATENCY.labels(method=method, route=route).observe(duration_seconds)


def record_job_submitted() -> None:
    JOBS_SUBMITTED.inc()


def record_job_completed(duration_seconds: float) -> None:
    JOBS_COMPLETED.inc()
    JOB_PROCESSING_DURATION.observe(duration_seconds)


def record_job_failed() -> None:
    JOBS_FAILED.inc()


def set_queue_depth(depth: int) -> None:
    JOB_QUEUE_DEPTH.set(depth)
