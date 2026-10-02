# Upstash Redis client for serverless (Vercel) environments
# Uses REST API instead of persistent connections

import json
import os
from typing import Any, Optional

import httpx


class UpstashRedis:
    """Async Redis-compatible client using Upstash REST API."""

    def __init__(self):
        self.url = os.getenv("UPSTASH_REDIS_REST_URL")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # --- Basic operations ---

    async def ping(self) -> bool:
        try:
            r = await self.client.post("/ping")
            return r.json().get("result") == "PONG"
        except Exception:
            return False

    async def get(self, key: str) -> Optional[str]:
        try:
            r = await self.client.get(f"/get/{key}")
            result = r.json().get("result")
            return result if result != "null" else None
        except Exception:
            return None

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        try:
            # Upstash uses SET with optional EX/PX
            cmd = ["set", key, value]
            if ex:
                cmd.extend(["ex", str(ex)])
            if px:
                cmd.extend(["px", str(px)])
            if nx:
                cmd.append("nx")
            if xx:
                cmd.append("xx")

            r = await self.client.post("/", json=cmd)
            return r.json().get("result") == "OK"
        except Exception:
            return False

    async def delete(self, *keys: str) -> int:
        try:
            r = await self.client.post("/", json=["del", *keys])
            return r.json().get("result", 0)
        except Exception:
            return 0

    async def exists(self, *keys: str) -> int:
        try:
            r = await self.client.post("/", json=["exists", *keys])
            return r.json().get("result", 0)
        except Exception:
            return 0

    async def expire(self, key: str, seconds: int) -> bool:
        try:
            r = await self.client.post("/", json=["expire", key, str(seconds)])
            return r.json().get("result", 0) == 1
        except Exception:
            return False

    async def ttl(self, key: str) -> int:
        try:
            r = await self.client.post("/", json=["ttl", key])
            return r.json().get("result", -2)
        except Exception:
            return -2

    # --- List operations (for arq queue) ---

    async def lpush(self, key: str, *values: str) -> int:
        try:
            r = await self.client.post("/", json=["lpush", key, *values])
            return r.json().get("result", 0)
        except Exception:
            return 0

    async def rpop(self, key: str) -> Optional[str]:
        try:
            r = await self.client.post("/", json=["rpop", key])
            result = r.json().get("result")
            return result if result != "null" else None
        except Exception:
            return None

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        try:
            r = await self.client.post("/", json=["lrange", key, str(start), str(end)])
            return r.json().get("result", [])
        except Exception:
            return []

    async def llen(self, key: str) -> int:
        try:
            r = await self.client.post("/", json=["llen", key])
            return r.json().get("result", 0)
        except Exception:
            return 0

    # --- Hash operations ---

    async def hset(self, name: str, key: str = None, value: str = None, mapping: dict = None) -> int:
        try:
            if mapping:
                cmd = ["hset", name]
                for k, v in mapping.items():
                    cmd.extend([k, v])
            else:
                cmd = ["hset", name, key, value]
            r = await self.client.post("/", json=cmd)
            return r.json().get("result", 0)
        except Exception:
            return 0

    async def hget(self, name: str, key: str) -> Optional[str]:
        try:
            r = await self.client.post("/", json=["hget", name, key])
            result = r.json().get("result")
            return result if result != "null" else None
        except Exception:
            return None

    async def hgetall(self, name: str) -> dict:
        try:
            r = await self.client.post("/", json=["hgetall", name])
            result = r.json().get("result", [])
            # Upstash returns flat array [k1, v1, k2, v2, ...]
            return {result[i]: result[i + 1] for i in range(0, len(result), 2)}
        except Exception:
            return {}

    async def hdel(self, name: str, *keys: str) -> int:
        try:
            r = await self.client.post("/", json=["hdel", name, *keys])
            return r.json().get("result", 0)
        except Exception:
            return 0

    # --- Pub/Sub (limited in REST) ---

    async def publish(self, channel: str, message: str) -> int:
        try:
            r = await self.client.post("/", json=["publish", channel, message])
            return r.json().get("result", 0)
        except Exception:
            return 0

    # --- Sorted sets (for rate limiting) ---

    async def zadd(self, name: str, mapping: dict) -> int:
        try:
            cmd = ["zadd", name]
            for score, member in mapping.items():
                cmd.extend([str(score), member])
            r = await self.client.post("/", json=cmd)
            return r.json().get("result", 0)
        except Exception:
            return 0

    async def zrem(self, name: str, *values: str) -> int:
        try:
            r = await self.client.post("/", json=["zrem", name, *values])
            return r.json().get("result", 0)
        except Exception:
            return 0

    async def zrangebyscore(
        self, name: str, min_score: float, max_score: float
    ) -> list[str]:
        try:
            r = await self.client.post(
                "/", json=["zrangebyscore", name, str(min_score), str(max_score)]
            )
            return r.json().get("result", [])
        except Exception:
            return []

    async def zcount(self, name: str, min_score: float, max_score: float) -> int:
        try:
            r = await self.client.post(
                "/", json=["zcount", name, str(min_score), str(max_score)]
            )
            return r.json().get("result", 0)
        except Exception:
            return 0


# Singleton instance
_upstash_redis: Optional[UpstashRedis] = None


def get_upstash_redis() -> UpstashRedis:
    global _upstash_redis
    if _upstash_redis is None:
        _upstash_redis = UpstashRedis()
    return _upstash_redis