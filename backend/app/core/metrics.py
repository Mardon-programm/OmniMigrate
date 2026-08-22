from __future__ import annotations

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

# --- Prometheus metrics ---------------------------------------------------

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ACTIVE_JOBS = Gauge(
    "migration_jobs_active",
    "Number of currently running migration jobs",
)

MIGRATION_TOTAL = Counter(
    "migrations_total",
    "Total migration jobs processed",
    ["status"],
)

LLM_CALLS = Counter(
    "llm_calls_total",
    "Total LLM API calls",
    ["provider", "status"],
)

LLM_LATENCY = Histogram(
    "llm_call_duration_seconds",
    "LLM call latency in seconds",
    ["provider"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

SANDBOX_RUNS = Counter(
    "sandbox_runs_total",
    "Total sandbox test runs",
    ["result"],
)

ORG_JOBS = Counter(
    "org_migrations_total",
    "Migrations per organization",
    ["org_id", "plan"],
)

REDIS_ERRORS = Counter(
    "redis_errors_total",
    "Redis operation failures",
)


def metrics_endpoint(_request: Request) -> Response:
    return PlainTextResponse(
        generate_latest(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


def setup_prometheus_middleware(app) -> None:
    """Instrument FastAPI with Prometheus request metrics."""
    from starlette.middleware.base import BaseHTTPMiddleware

    class PrometheusMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            if request.url.path == "/metrics":
                return await call_next(request)
            method = request.method
            path = request.url.path
            with REQUEST_LATENCY.labels(method=method, endpoint=path).time():
                response = await call_next(request)
            REQUEST_COUNT.labels(method=method, endpoint=path, status=response.status_code).inc()
            return response

    app.add_middleware(PrometheusMiddleware)
