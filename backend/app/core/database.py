from collections.abc import AsyncGenerator
from typing import Union

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.upstash_redis import UpstashRedis, get_upstash_redis


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""


def _build_engine():
    """Create the async engine with dialect-appropriate pool settings."""
    url = settings.database_url
    if url.startswith("sqlite"):
        # SQLite (aiosqlite) uses NullPool and rejects pool sizing options.
        return create_async_engine(url, echo=settings.debug)
    return create_async_engine(
        url,
        echo=settings.debug,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


engine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


_redis_pool: Union[Redis, UpstashRedis] | None = None


def _use_upstash() -> bool:
    """Check if we should use Upstash (serverless) instead of regular Redis."""
    return bool(settings.upstash_redis_rest_url and settings.upstash_redis_rest_token)


async def get_redis() -> Union[Redis, UpstashRedis]:
    """Return a shared async Redis client (Upstash for serverless, regular Redis otherwise)."""
    global _redis_pool
    if _redis_pool is None:
        if _use_upstash():
            _redis_pool = get_upstash_redis()
        else:
            _redis_pool = Redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
    return _redis_pool


async def close_redis() -> None:
    """Close the shared Redis client (used on application shutdown)."""
    global _redis_pool
    if _redis_pool is not None:
        if hasattr(_redis_pool, "aclose"):
            await _redis_pool.aclose()
        elif hasattr(_redis_pool, "close"):
            await _redis_pool.close()
        _redis_pool = None
