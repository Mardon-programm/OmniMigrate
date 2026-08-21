"""Tests for Phase 1 security features: organizations, audit log, token encryption, SSRF, RBAC."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.token_encryption import decrypt_token, encrypt_token


class TestTokenEncryption:
    def test_roundtrip(self):
        original = "ghp_abc123secret"
        encrypted = encrypt_token(original)
        assert encrypted != original
        assert decrypt_token(encrypted) == original

    def test_different_tokens_different_ciphertext(self):
        a = encrypt_token("token_a")
        b = encrypt_token("token_b")
        assert a != b

    def test_empty_string(self):
        encrypted = encrypt_token("")
        assert decrypt_token(encrypted) == ""

    def test_unicode_token(self):
        original = "ghp_unicode_тест_🔑"
        encrypted = encrypt_token(original)
        assert decrypt_token(encrypted) == original

    def test_decrypt_tampered_ciphertext_raises(self):
        from cryptography.fernet import InvalidToken

        encrypted = encrypt_token("valid")
        tampered = encrypted[:-5] + "XXXXX"
        with pytest.raises(InvalidToken):
            decrypt_token(tampered)


class TestSSRF:
    def test_allows_github_https(self):
        from app.services.ssrf import validate_url_for_clone

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("140.82.121.4", 0)),
            ]
            result = validate_url_for_clone("https://github.com/owner/repo.git")
            assert result == "https://github.com/owner/repo.git"

    def test_blocks_private_ip(self):
        from app.services.git_sandbox import GitOperationError
        from app.services.ssrf import validate_url_for_clone

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("192.168.1.1", 0)),
            ]
            with pytest.raises(GitOperationError, match="private/internal"):
                validate_url_for_clone("https://evil.internal/repo.git")

    def test_blocks_localhost(self):
        from app.services.git_sandbox import GitOperationError
        from app.services.ssrf import validate_url_for_clone

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("127.0.0.1", 0)),
            ]
            with pytest.raises(GitOperationError, match="private/internal"):
                validate_url_for_clone("https://localhost/repo.git")

    def test_blocks_10_x(self):
        from app.services.git_sandbox import GitOperationError
        from app.services.ssrf import validate_url_for_clone

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("10.0.0.1", 0)),
            ]
            with pytest.raises(GitOperationError, match="private/internal"):
                validate_url_for_clone("https://internal.corp/repo.git")

    def test_blocks_169_254(self):
        from app.services.git_sandbox import GitOperationError
        from app.services.ssrf import validate_url_for_clone

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("169.254.169.254", 0)),
            ]
            with pytest.raises(GitOperationError, match="private/internal"):
                validate_url_for_clone("https://metadata/repo.git")

    def test_blocks_bad_scheme(self):
        from app.services.git_sandbox import GitOperationError
        from app.services.ssrf import validate_url_for_clone

        with pytest.raises(GitOperationError, match="not allowed"):
            validate_url_for_clone("file:///etc/passwd")

    def test_blocks_no_hostname(self):
        from app.services.git_sandbox import GitOperationError
        from app.services.ssrf import validate_url_for_clone

        with pytest.raises(GitOperationError, match="no hostname"):
            validate_url_for_clone("https://")

    def test_blocks_dns_failure(self):
        import socket as _socket

        from app.services.git_sandbox import GitOperationError
        from app.services.ssrf import validate_url_for_clone

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.side_effect = _socket.gaierror("DNS resolution failed")
            with pytest.raises(GitOperationError, match="DNS"):
                validate_url_for_clone("https://nonexistent.example/repo.git")

    def test_blocks_empty_dns_result(self):
        from app.services.git_sandbox import GitOperationError
        from app.services.ssrf import validate_url_for_clone

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = []
            with pytest.raises(GitOperationError, match="no results"):
                validate_url_for_clone("https://nonexistent.example/repo.git")

    def test_blocks_link_local_ipv6(self):
        from app.services.git_sandbox import GitOperationError
        from app.services.ssrf import validate_url_for_clone

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (30, 1, 6, "", ("fe80::1", 0, 0, 0)),
            ]
            with pytest.raises(GitOperationError, match="private/internal"):
                validate_url_for_clone("https://ipv6-local/repo.git")

    def test_deduplicates_duplicate_ips(self):
        from app.services.ssrf import validate_url_for_clone

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("140.82.121.4", 0)),
                (2, 1, 6, "", ("140.82.121.4", 0)),
            ]
            result = validate_url_for_clone("https://github.com/owner/repo.git")
            assert result == "https://github.com/owner/repo.git"

    def test_blocks_172_16_x(self):
        from app.services.git_sandbox import GitOperationError
        from app.services.ssrf import validate_url_for_clone

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("172.16.0.1", 0)),
            ]
            with pytest.raises(GitOperationError, match="private/internal"):
                validate_url_for_clone("https://internal.corp/repo.git")


class TestOrgRBAC:
    def test_has_min_role_owner(self):
        from app.services.rbac import OrgRole, has_min_role

        assert has_min_role(OrgRole.owner, OrgRole.admin)
        assert has_min_role(OrgRole.owner, OrgRole.member)
        assert has_min_role(OrgRole.owner, OrgRole.viewer)

    def test_has_min_role_viewer(self):
        from app.services.rbac import OrgRole, has_min_role

        assert has_min_role(OrgRole.viewer, OrgRole.viewer)
        assert not has_min_role(OrgRole.viewer, OrgRole.member)

    def test_has_min_role_none(self):
        from app.services.rbac import OrgRole, has_min_role

        assert not has_min_role(None, OrgRole.viewer)

    def test_hierarchy_order(self):
        from app.services.rbac import ORG_ROLE_HIERARCHY, OrgRole

        assert ORG_ROLE_HIERARCHY[OrgRole.owner] > ORG_ROLE_HIERARCHY[OrgRole.admin]
        assert ORG_ROLE_HIERARCHY[OrgRole.admin] > ORG_ROLE_HIERARCHY[OrgRole.member]
        assert ORG_ROLE_HIERARCHY[OrgRole.member] > ORG_ROLE_HIERARCHY[OrgRole.viewer]


class TestOrgRateLimit:
    @pytest.mark.asyncio
    async def test_disabled_returns_false(self):
        from app.core.rate_limit import is_org_rate_limited

        with patch("app.core.rate_limit.settings") as s:
            s.rate_limit_enabled = False
            mock_req = MagicMock()
            result = await is_org_rate_limited(mock_req, org_id=1, limit=10, window=60)
            assert result is False

    @pytest.mark.asyncio
    async def test_no_redis_returns_false(self):
        from app.core.rate_limit import is_org_rate_limited

        with patch("app.core.rate_limit.settings") as s:
            s.rate_limit_enabled = True
            mock_req = MagicMock()
            mock_req.app.state.redis = None
            result = await is_org_rate_limited(mock_req, org_id=1, limit=10, window=60)
            assert result is False

    @pytest.mark.asyncio
    async def test_first_request_returns_false(self):
        from app.core.rate_limit import is_org_rate_limited

        with patch("app.core.rate_limit.settings") as s:
            s.rate_limit_enabled = True
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_req = MagicMock()
            mock_req.app.state.redis = mock_redis
            result = await is_org_rate_limited(mock_req, org_id=1, limit=10, window=60)
            assert result is False
            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_under_limit_returns_false(self):
        from app.core.rate_limit import is_org_rate_limited

        with patch("app.core.rate_limit.settings") as s:
            s.rate_limit_enabled = True
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value="5")
            mock_req = MagicMock()
            mock_req.app.state.redis = mock_redis
            result = await is_org_rate_limited(mock_req, org_id=1, limit=10, window=60)
            assert result is False
            mock_redis.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_at_limit_returns_true(self):
        from app.core.rate_limit import is_org_rate_limited

        with patch("app.core.rate_limit.settings") as s:
            s.rate_limit_enabled = True
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value="10")
            mock_req = MagicMock()
            mock_req.app.state.redis = mock_redis
            result = await is_org_rate_limited(mock_req, org_id=1, limit=10, window=60)
            assert result is True

    @pytest.mark.asyncio
    async def test_redis_error_returns_false(self):
        from app.core.rate_limit import is_org_rate_limited

        with patch("app.core.rate_limit.settings") as s:
            s.rate_limit_enabled = True
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(side_effect=RuntimeError("redis down"))
            mock_req = MagicMock()
            mock_req.app.state.redis = mock_redis
            result = await is_org_rate_limited(mock_req, org_id=1, limit=10, window=60)
            assert result is False


class TestGetOrgRole:
    @pytest.mark.asyncio
    async def test_returns_role_when_member(self, db_session):
        from app.models.organization import Organization, OrganizationMember, OrgRole
        from app.models.user import User, UserRole
        from app.services.rbac import get_org_role

        user = User(
            email="rbactest@test.com",
            hashed_password="x",
            full_name="RBAC Test",
            role=UserRole.engineer,
        )
        db_session.add(user)
        await db_session.flush()
        org = Organization(name="Rbac Org", slug="rbac-org")
        db_session.add(org)
        await db_session.flush()
        member = OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=OrgRole.admin,
        )
        db_session.add(member)
        await db_session.flush()
        role = await get_org_role(db_session, user.id, org.id)
        assert role == OrgRole.admin

    @pytest.mark.asyncio
    async def test_returns_none_when_not_member(self, db_session):
        from app.services.rbac import get_org_role

        role = await get_org_role(db_session, 9999, 9999)
        assert role is None


class TestListAuditLogs:
    @pytest.mark.asyncio
    async def test_list_with_user_filter(self, db_session):
        from app.models.organization import AuditLog, Organization
        from app.models.user import User, UserRole
        from app.services.audit_log import list_audit_logs

        user = User(
            email="auditlist@test.com",
            hashed_password="x",
            full_name="AL",
            role=UserRole.engineer,
        )
        db_session.add(user)
        await db_session.flush()
        org = Organization(name="Audit Org", slug="audit-org")
        db_session.add(org)
        await db_session.flush()
        entry = AuditLog(
            action="test.action",
            resource_type="test",
            user_id=user.id,
            organization_id=org.id,
        )
        db_session.add(entry)
        await db_session.flush()
        results = await list_audit_logs(db_session, user_id=user.id)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_list_with_action_filter(self, db_session):
        from app.models.organization import AuditLog, Organization
        from app.services.audit_log import list_audit_logs

        org = Organization(name="Audit Org2", slug="audit-org2")
        db_session.add(org)
        await db_session.flush()
        e1 = AuditLog(action="foo", resource_type="x", organization_id=org.id)
        e2 = AuditLog(action="bar", resource_type="x", organization_id=org.id)
        db_session.add_all([e1, e2])
        await db_session.flush()
        results = await list_audit_logs(db_session, action="foo")
        assert len(results) == 1
        assert results[0].action == "foo"

    @pytest.mark.asyncio
    async def test_list_with_resource_type_filter(self, db_session):
        from app.models.organization import AuditLog, Organization
        from app.services.audit_log import list_audit_logs

        org = Organization(name="Audit Org3", slug="audit-org3")
        db_session.add(org)
        await db_session.flush()
        e1 = AuditLog(action="a", resource_type="project", organization_id=org.id)
        e2 = AuditLog(action="a", resource_type="organization", organization_id=org.id)
        db_session.add_all([e1, e2])
        await db_session.flush()
        results = await list_audit_logs(db_session, resource_type="project")
        assert len(results) == 1
        assert results[0].resource_type == "project"
