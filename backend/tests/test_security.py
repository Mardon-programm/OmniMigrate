from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hashing_roundtrip():
    hashed = hash_password("super-secret-123")
    assert hashed != "super-secret-123"
    assert verify_password("super-secret-123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    token = create_access_token(42, "client")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "42"
    assert payload["role"] == "client"


def test_refresh_token_type_enforced():
    token = create_refresh_token(7)
    payload = decode_token(token, expected_type="refresh")
    assert payload["sub"] == "7"


def test_access_token_rejected_as_refresh():
    token = create_access_token(1, "admin")
    try:
        decode_token(token, expected_type="refresh")
    except Exception:
        return
    raise AssertionError("Expected token type mismatch to raise")


def test_diff_utils():
    from app.services.diff_utils import diff_stats, generate_diff

    old_code = "print 'hi'\n"
    new_code = "print('hi')\n"
    diff = generate_diff(old_code, new_code)
    assert "legacy/source.py" in diff
    assert "modern/source.py" in diff
    stats = diff_stats(diff)
    assert stats.additions >= 1
    assert stats.deletions >= 1


def test_health_endpoint():
    import pytest

    pytest.skip("Integration test requires a running application instance")
