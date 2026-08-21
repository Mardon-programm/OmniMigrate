from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings


class RateLimitExceededError(Exception):
    """Raised when a client exceeds the configured request rate limit."""


async def is_rate_limited(request: Request, key: str, limit: int, window: int) -> bool:
    """Fixed-window rate limiter backed by Redis. Falls back to allow."""
    if not settings.rate_limit_enabled:
        return False
    try:
        redis = request.app.state.redis
        if redis is None:
            return False
        bucket = f"ratelimit:{key}:{request.client.host if request.client else 'unknown'}"
        current = await redis.get(bucket)
        if current is None:
            await redis.setex(bucket, window, 1)
            return False
        count = int(current)
        if count >= limit:
            return True
        await redis.incr(bucket)
        return False
    except Exception:
        return False


async def is_org_rate_limited(request: Request, org_id: int, limit: int, window: int) -> bool:
    """Per-organization fixed-window rate limiter backed by Redis."""
    if not settings.rate_limit_enabled:
        return False
    try:
        redis = request.app.state.redis
        if redis is None:
            return False
        bucket = f"ratelimit:org:{org_id}"
        current = await redis.get(bucket)
        if current is None:
            await redis.setex(bucket, window, 1)
            return False
        count = int(current)
        if count >= limit:
            return True
        await redis.incr(bucket)
        return False
    except Exception:
        return False


async def rate_limit_middleware(request: Request, call_next):
    """ASGI middleware enforcing per-path and per-organization rate limits."""
    import re

    if request.url.path.startswith(("/api/v1/auth/", "/api/v1/migrations")):
        limited = await is_rate_limited(
            request,
            key=request.url.path,
            limit=settings.rate_limit_requests,
            window=settings.rate_limit_window_seconds,
        )
        if limited:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please retry later.",
                    "code": "RATE_LIMITED",
                },
            )

    org_match = re.match(r"/api/v1/organizations/(\d+)", request.url.path)
    if org_match:
        org_id = int(org_match.group(1))
        limited = await is_org_rate_limited(
            request,
            org_id=org_id,
            limit=settings.rate_limit_requests,
            window=settings.rate_limit_window_seconds,
        )
        if limited:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Organization rate limit exceeded.",
                    "code": "ORG_RATE_LIMITED",
                },
            )

    return await call_next(request)
