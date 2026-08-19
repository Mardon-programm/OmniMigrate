import pytest
from app.core.deps import get_current_user, get_user_or_none, require_roles
from app.core.security import create_access_token
from app.models import UserRole
from tests.conftest import make_user


class TestGetCurrentUser:
    async def test_valid_token_returns_user(self, db_session):
        user = await make_user(db_session, email="dep@example.com")
        token = create_access_token(user.id, user.role.value)

        class _FakeDepends:
            pass

        session = db_session
        current = await get_current_user(session, token)
        assert current.id == user.id

    async def test_missing_token_rejected(self, db_session):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await get_current_user(db_session, None)
        assert exc.value.status_code == 401

    async def test_invalid_token_rejected(self, db_session):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await get_current_user(db_session, "not-a-valid-jwt")
        assert exc.value.status_code == 401

    async def test_unknown_user_rejected(self, db_session):
        from fastapi import HTTPException

        token = create_access_token(424242, "client")
        with pytest.raises(HTTPException) as exc:
            await get_current_user(db_session, token)
        assert exc.value.status_code == 401

    async def test_inactive_user_rejected(self, db_session):
        from fastapi import HTTPException

        user = await make_user(db_session, email="depin@example.com", is_active=False)
        token = create_access_token(user.id, user.role.value)
        with pytest.raises(HTTPException) as exc:
            await get_current_user(db_session, token)
        assert exc.value.status_code == 401


class TestRequireRoles:
    def test_allowed_role_passes(self):
        from app.models import User

        user = User(role=UserRole.admin)
        dep = require_roles(UserRole.admin)
        assert dep(user) is user

    def test_wrong_role_raises(self):
        from app.models import User
        from fastapi import HTTPException

        user = User(role=UserRole.client)
        dep = require_roles(UserRole.admin)
        with pytest.raises(HTTPException) as exc:
            dep(user)
        assert exc.value.status_code == 403

    def test_any_role_in_set_passes(self):
        from app.models import User

        user = User(role=UserRole.engineer)
        dep = require_roles(UserRole.admin, UserRole.engineer)
        assert dep(user) is user


class TestGetUserOrNone:
    async def test_returns_user(self, db_session):
        user = await make_user(db_session, email="gon@example.com")
        found = await get_user_or_none(db_session, user.id)
        assert found is not None
        assert found.id == user.id

    async def test_returns_none_for_missing(self, db_session):
        assert await get_user_or_none(db_session, 9999) is None
