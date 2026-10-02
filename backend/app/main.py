from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import router as api_router
from app.core.config import settings
from app.core.database import close_redis, get_redis
from app.core.logging import configure_logging
from app.core.metrics import metrics_endpoint, setup_prometheus_middleware
from app.core.rate_limit import rate_limit_middleware
from app.core.tracing import setup_tracing, shutdown_tracing

configure_logging(debug=settings.debug)
logger = structlog.get_logger(__name__)


def _validate_production_secrets() -> None:
    """Refuse to start in production if critical secrets are at default values."""
    if settings.environment != "production":
        return
    issues: list[str] = []
    if settings.secret_key == "change-me-in-production" or len(settings.secret_key) < 32:
        issues.append("SECRET_KEY must be set to a secure random value (>=32 chars)")
    if not settings.database_url or "omnimigrate:omnimigrate" in settings.database_url:
        issues.append("DATABASE_URL must use strong credentials, not the defaults")
    if settings.bcrypt_rounds < 12:
        issues.append("BCRYPT_ROUNDS must be at least 12 in production")
    if not settings.openai_api_key and not settings.llm_fallback_to_rules:
        issues.append("OPENAI_API_KEY required when LLM_FALLBACK_TO_RULES=false")
    if settings.paddle_api_key and not settings.paddle_webhook_secret:
        issues.append("PADDLE_WEBHOOK_SECRET required when PADDLE_API_KEY is set")
    if settings.smtp_host and (not settings.smtp_user or not settings.smtp_password):
        issues.append("SMTP_USER and SMTP_PASSWORD required when SMTP_HOST is set")
    if issues:
        msg = "Startup secret validation failed:\n  - " + "\n  - ".join(issues)
        logger.critical(msg)
        raise SystemExit(msg)


_validate_production_secrets()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.otel_enabled:
        setup_tracing()
    app.state.redis = await get_redis()
    yield
    await close_redis()
    if settings.otel_enabled:
        shutdown_tracing()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Autonomous AI-powered migration and modernization engine for legacy source code."
    ),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.prometheus_enabled:
    setup_prometheus_middleware(app)


@app.middleware("http")
async def http_middleware(request: Request, call_next):
    return await rate_limit_middleware(request, call_next)


# --- Global exception handlers -------------------------------------------


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed",
            "code": "VALIDATION_ERROR",
            "errors": exc.errors()[:20],
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error", path=request.url.path)
    if settings.debug:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "INTERNAL_ERROR"},
    )


# --- Routes ---------------------------------------------------------------

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/")
async def root() -> dict:
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/api/docs",
        "health": "/healthz",
    }


@app.get("/healthz")
async def healthz() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    """Readiness probe — checks Redis, DB, and external services connectivity."""
    checks: dict[str, str] = {}
    all_ok = True

    # Redis
    redis_ok = True
    try:
        redis = request.app.state.redis
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        redis_ok = False
        checks["redis"] = "unavailable"
        all_ok = False

    # Database
    db_ok = True
    try:
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        db_ok = False
        checks["database"] = "unavailable"
        all_ok = False

    # LLM API (optional check)
    llm_ok = True
    if settings.openai_api_key:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                if settings.openai_base_url:
                    await client.get(f"{settings.openai_base_url}/models", headers={"Authorization": f"Bearer {settings.openai_api_key}"})
                else:
                    await client.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {settings.openai_api_key}"})
            checks["llm_api"] = "ok"
        except Exception:
            llm_ok = False
            checks["llm_api"] = "unavailable"
            # Don't fail readiness for LLM API
    else:
        checks["llm_api"] = "not_configured"

    # Worker queue
    queue_ok = True
    try:
        redis = request.app.state.redis
        queue_len = await redis.llen("arq:queue:default")
        checks["worker_queue"] = f"{queue_len} jobs"
    except Exception:
        queue_ok = False
        checks["worker_queue"] = "unavailable"

    status_code = 200 if all_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ok else "degraded",
            "checks": checks,
            "version": settings.app_version,
            "environment": settings.environment,
        },
    )


if settings.prometheus_enabled:
    app.add_route("/metrics", metrics_endpoint)
