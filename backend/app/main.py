from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import router as api_router
from app.core.config import settings
from app.core.database import close_redis, get_redis
from app.core.rate_limit import rate_limit_middleware

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


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
    if issues:
        msg = "Startup secret validation failed:\n  - " + "\n  - ".join(issues)
        logger.critical(msg)
        raise SystemExit(msg)


_validate_production_secrets()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await get_redis()
    yield
    await close_redis()


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
    logging.getLogger(__name__).exception("Unhandled error on %s", request.url.path)
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
    return {"status": "ok", "service": settings.app_name}
