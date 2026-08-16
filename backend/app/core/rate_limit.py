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


async def rate_limit_middleware(request: Request, call_next):
    """ASGI middleware enforcing per-path rate limits."""
    # Only rate limit API mutation endpoints.
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
    return await call_next(request)
