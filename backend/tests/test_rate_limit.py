from app.core.rate_limit import is_rate_limited, rate_limit_middleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class FakeRedis:
    def __init__(self, value=None):
        self._value = value
        self.setex_called = False
        self.incr_called = False

    async def get(self, _bucket):
        return self._value

    async def setex(self, _bucket, _window, _value):
        self.setex_called = True
        self._value = "1"

    async def incr(self, _bucket):
        self.incr_called = True
        self._value = str(int(self._value) + 1)


def _make_request(redis, path="/api/v1/auth/login", host="127.0.0.1"):
    app = FastAPI()
    app.state.redis = redis
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": (host, 1234),
        "server": (host, 80),
        "scheme": "http",
        "app": app,
    }
    return Request(scope)


class TestIsRateLimited:
    async def test_disabled_returns_false(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "rate_limit_enabled", False)
        request = _make_request(FakeRedis())
        assert await is_rate_limited(request, "key", 60, 60) is False

    async def test_no_redis_returns_false(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "rate_limit_enabled", True)
        request = _make_request(None)
        assert await is_rate_limited(request, "key", 60, 60) is False

    async def test_first_request_sets_bucket(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "rate_limit_enabled", True)
        redis = FakeRedis()
        request = _make_request(redis)
        assert await is_rate_limited(request, "key", 60, 60) is False
        assert redis.setex_called is True

    async def test_under_limit_increments(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "rate_limit_enabled", True)
        redis = FakeRedis(value="3")
        request = _make_request(redis)
        assert await is_rate_limited(request, "key", 60, 60) is False
        assert redis.incr_called is True

    async def test_over_limit_rejected(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "rate_limit_enabled", True)
        redis = FakeRedis(value="60")
        request = _make_request(redis)
        assert await is_rate_limited(request, "key", 60, 60) is True

    async def test_exception_falls_open(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "rate_limit_enabled", True)

        class BoomRedis:
            async def get(self, _bucket):
                raise RuntimeError("connection refused")

        request = _make_request(BoomRedis())
        assert await is_rate_limited(request, "key", 60, 60) is False


class TestRateLimitMiddleware:
    async def test_passes_through_when_not_limited(self, monkeypatch):
        async def _not_limited(*a, **k):
            return False

        monkeypatch.setattr("app.core.rate_limit.is_rate_limited", _not_limited)

        async def call_next(request):
            return JSONResponse({"ok": True})

        request = _make_request(None, path="/api/v1/auth/login")
        response = await rate_limit_middleware(request, call_next)
        assert response.status_code == 200

    async def test_returns_429_when_limited(self, monkeypatch):
        async def _limited(*a, **k):
            return True

        monkeypatch.setattr("app.core.rate_limit.is_rate_limited", _limited)

        async def call_next(request):
            return JSONResponse({"ok": True})

        request = _make_request(None, path="/api/v1/auth/login")
        response = await rate_limit_middleware(request, call_next)
        assert response.status_code == 429
        assert response.body
        assert b"RATE_LIMITED" in response.body

    async def test_ignores_non_rate_limited_paths(self, monkeypatch):
        called = {"value": False}

        async def _is_limited(*a, **k):
            called["value"] = True
            return True

        monkeypatch.setattr("app.core.rate_limit.is_rate_limited", _is_limited)

        async def call_next(request):
            return JSONResponse({"ok": True})

        request = _make_request(None, path="/api/v1/jobs")
        response = await rate_limit_middleware(request, call_next)
        assert response.status_code == 200
        assert called["value"] is False

    async def test_org_rate_limit_429(self, monkeypatch):
        async def _not_limited(*a, **k):
            return False

        async def _org_limited(*a, **k):
            return True

        monkeypatch.setattr("app.core.rate_limit.is_rate_limited", _not_limited)
        monkeypatch.setattr("app.core.rate_limit.is_org_rate_limited", _org_limited)

        async def call_next(request):
            return JSONResponse({"ok": True})

        request = _make_request(None, path="/api/v1/organizations/1/members")
        response = await rate_limit_middleware(request, call_next)
        assert response.status_code == 429
        assert b"ORG_RATE_LIMITED" in response.body
