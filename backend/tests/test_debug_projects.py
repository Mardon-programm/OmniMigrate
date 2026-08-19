class TestDebug:
    async def test_create_debug(self, client, db_session):
        from tests.conftest import make_user

        user = await make_user(db_session, email="dbg@example.com")
        resp = await client.post(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {_token(user)}"},
            json={"name": "Debug", "source_language": "python"},
        )
        print("STATUS:", resp.status_code)
        print("BODY:", resp.text[:200])

    def _unused(self):
        pass


def _token(user):
    from app.core.security import create_access_token

    return create_access_token(user.id, user.role.value)
