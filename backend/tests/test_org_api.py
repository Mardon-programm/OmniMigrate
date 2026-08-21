"""Tests for organizations API, audit log, RBAC, and org rate limiting."""

from __future__ import annotations

from tests.conftest import auth_headers, make_user

ORG_URL = "/api/v1/organizations/"


_org_counter = 0


async def _create_org(client, headers, slug=None, name=None):
    global _org_counter
    _org_counter += 1
    slug = slug or f"org-{_org_counter}"
    name = name or f"Org {_org_counter}"
    resp = await client.post(
        ORG_URL,
        json={"name": name, "slug": slug, "description": "desc"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


async def _make_and_headers(client, db, email="u@test.com"):
    user = await make_user(db, email=email, role="client")
    return user, auth_headers(user.id)


class TestOrgCRUD:
    async def test_create_org(self, client, db_session):
        user = await make_user(db_session, email="owner@test.com")
        headers = auth_headers(user.id)
        org = await _create_org(client, headers)
        assert org["name"].startswith("Org ")
        assert org["is_active"] is True

    async def test_create_org_duplicate_slug(self, client, db_session):
        user = await make_user(db_session, email="owner@test.com")
        headers = auth_headers(user.id)
        await _create_org(client, headers, slug="dup", name="Dup First")
        resp = await client.post(
            ORG_URL,
            json={"name": "Dup Second", "slug": "dup"},
            headers=headers,
        )
        assert resp.status_code == 409

    async def test_get_org(self, client, db_session):
        user = await make_user(db_session, email="owner@test.com")
        headers = auth_headers(user.id)
        org = await _create_org(client, headers)
        resp = await client.get(f"{ORG_URL}{org['id']}", headers=headers)
        assert resp.status_code == 200

    async def test_get_org_non_member(self, client, db_session):
        user = await make_user(db_session, email="owner@test.com")
        headers = auth_headers(user.id)
        org = await _create_org(client, headers)
        _, out_h = await _make_and_headers(client, db_session, "o@t.com")
        resp = await client.get(f"{ORG_URL}{org['id']}", headers=out_h)
        assert resp.status_code == 403

    async def test_get_org_platform_admin(self, client, db_session):
        admin = await make_user(db_session, email="adm@t.com", role="admin")
        a_h = auth_headers(admin.id)
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        resp = await client.get(f"{ORG_URL}{org['id']}", headers=a_h)
        assert resp.status_code == 200

    async def test_get_org_not_found(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        resp = await client.get(f"{ORG_URL}9999", headers=auth_headers(user.id))
        assert resp.status_code == 404

    async def test_update_org(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        resp = await client.patch(
            f"{ORG_URL}{org['id']}",
            json={"name": "New"},
            headers=h,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    async def test_update_org_non_admin(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        _, mh = await _make_and_headers(client, db_session, "m@t.com")
        resp = await client.patch(
            f"{ORG_URL}{org['id']}",
            json={"name": "X"},
            headers=mh,
        )
        assert resp.status_code == 403

    async def test_update_org_not_found(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        resp = await client.patch(
            f"{ORG_URL}9999",
            json={"name": "X"},
            headers=h,
        )
        assert resp.status_code == 404

    async def test_deactivate_org(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        resp = await client.patch(
            f"{ORG_URL}{org['id']}",
            json={"is_active": False},
            headers=h,
        )
        assert resp.json()["is_active"] is False


class TestOrgMembers:
    async def test_add_member(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        member, _ = await _make_and_headers(client, db_session, "m@t.com")
        resp = await client.post(
            f"{ORG_URL}{org['id']}/members",
            json={"user_id": member.id, "role": "member"},
            headers=h,
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "member"

    async def test_add_duplicate_member(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        member, _ = await _make_and_headers(client, db_session, "m@t.com")
        await client.post(
            f"{ORG_URL}{org['id']}/members",
            json={"user_id": member.id, "role": "member"},
            headers=h,
        )
        resp = await client.post(
            f"{ORG_URL}{org['id']}/members",
            json={"user_id": member.id, "role": "admin"},
            headers=h,
        )
        assert resp.status_code == 409

    async def test_list_members(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        resp = await client.get(f"{ORG_URL}{org['id']}/members", headers=h)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_update_member_role(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        member, _ = await _make_and_headers(client, db_session, "m@t.com")
        add_resp = await client.post(
            f"{ORG_URL}{org['id']}/members",
            json={"user_id": member.id, "role": "viewer"},
            headers=h,
        )
        mid = add_resp.json()["id"]
        resp = await client.patch(
            f"{ORG_URL}{org['id']}/members/{mid}",
            json={"role": "admin"},
            headers=h,
        )
        assert resp.json()["role"] == "admin"

    async def test_remove_member(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        member, _ = await _make_and_headers(client, db_session, "m@t.com")
        add_resp = await client.post(
            f"{ORG_URL}{org['id']}/members",
            json={"user_id": member.id, "role": "member"},
            headers=h,
        )
        mid = add_resp.json()["id"]
        resp = await client.delete(
            f"{ORG_URL}{org['id']}/members/{mid}",
            headers=h,
        )
        assert resp.status_code == 204

    async def test_remove_nonexistent_member(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        resp = await client.delete(
            f"{ORG_URL}{org['id']}/members/9999",
            headers=h,
        )
        assert resp.status_code == 404

    async def test_remove_owner_forbidden(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        mr = await client.get(f"{ORG_URL}{org['id']}/members", headers=h)
        owner_m = next(m for m in mr.json() if m["role"] == "owner")
        resp = await client.delete(
            f"{ORG_URL}{org['id']}/members/{owner_m['id']}",
            headers=h,
        )
        assert resp.status_code == 400

    async def test_member_cannot_add(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        member, mh = await _make_and_headers(client, db_session, "m@t.com")
        await client.post(
            f"{ORG_URL}{org['id']}/members",
            json={"user_id": member.id, "role": "member"},
            headers=h,
        )
        other, _oh = await _make_and_headers(client, db_session, "o@t.com")
        resp = await client.post(
            f"{ORG_URL}{org['id']}/members",
            json={"user_id": other.id, "role": "viewer"},
            headers=mh,
        )
        assert resp.status_code == 403

    async def test_list_members_non_member(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        _, oh = await _make_and_headers(client, db_session, "x@t.com")
        resp = await client.get(f"{ORG_URL}{org['id']}/members", headers=oh)
        assert resp.status_code == 403


class TestAuditLogs:
    async def test_audit_on_create(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        resp = await client.get(
            f"{ORG_URL}{org['id']}/audit-logs",
            headers=h,
        )
        logs = resp.json()
        assert len(logs) >= 1
        assert logs[0]["action"] == "org.create"

    async def test_audit_on_member_add(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        member, _ = await _make_and_headers(client, db_session, "m@t.com")
        await client.post(
            f"{ORG_URL}{org['id']}/members",
            json={"user_id": member.id, "role": "member"},
            headers=h,
        )
        resp = await client.get(
            f"{ORG_URL}{org['id']}/audit-logs",
            headers=h,
        )
        actions = [log["action"] for log in resp.json()]
        assert "org.member.add" in actions

    async def test_audit_on_update(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        await client.patch(
            f"{ORG_URL}{org['id']}",
            json={"name": "Upd"},
            headers=h,
        )
        resp = await client.get(
            f"{ORG_URL}{org['id']}/audit-logs",
            headers=h,
        )
        actions = [log["action"] for log in resp.json()]
        assert "org.update" in actions

    async def test_audit_limit_offset(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        resp = await client.get(
            f"{ORG_URL}{org['id']}/audit-logs?limit=1&offset=0",
            headers=h,
        )
        assert resp.status_code == 200
        assert len(resp.json()) <= 1

    async def test_audit_non_member_forbidden(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        _, oh = await _make_and_headers(client, db_session, "x@t.com")
        resp = await client.get(
            f"{ORG_URL}{org['id']}/audit-logs",
            headers=oh,
        )
        assert resp.status_code == 403

    async def test_audit_on_member_remove(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        member, _ = await _make_and_headers(client, db_session, "m@t.com")
        add_resp = await client.post(
            f"{ORG_URL}{org['id']}/members",
            json={"user_id": member.id, "role": "viewer"},
            headers=h,
        )
        mid = add_resp.json()["id"]
        await client.delete(f"{ORG_URL}{org['id']}/members/{mid}", headers=h)
        resp = await client.get(
            f"{ORG_URL}{org['id']}/audit-logs",
            headers=h,
        )
        actions = [log["action"] for log in resp.json()]
        assert "org.member.remove" in actions

    async def test_audit_on_member_update(self, client, db_session):
        user = await make_user(db_session, email="ow@t.com")
        h = auth_headers(user.id)
        org = await _create_org(client, h)
        member, _ = await _make_and_headers(client, db_session, "m@t.com")
        add_resp = await client.post(
            f"{ORG_URL}{org['id']}/members",
            json={"user_id": member.id, "role": "viewer"},
            headers=h,
        )
        mid = add_resp.json()["id"]
        await client.patch(
            f"{ORG_URL}{org['id']}/members/{mid}",
            json={"is_active": False},
            headers=h,
        )
        resp = await client.get(
            f"{ORG_URL}{org['id']}/audit-logs",
            headers=h,
        )
        actions = [log["action"] for log in resp.json()]
        assert "org.member.update" in actions
