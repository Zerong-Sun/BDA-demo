import pytest
from backend.app.auth.service import (
    authenticate_user,
    hash_password,
    validate_password_strength,
    verify_password,
)
from backend.app.db import connect, release_connection
from fastapi.testclient import TestClient


def test_validate_password_strength_accepts_mixed():
    validate_password_strength("admin1234")


def test_validate_password_strength_rejects_short():
    with pytest.raises(ValueError, match="weak_password"):
        validate_password_strength("abc1")


def test_validate_password_strength_rejects_no_digits():
    with pytest.raises(ValueError, match="weak_password"):
        validate_password_strength("abcdefgh")


def test_hash_password_roundtrip():
    hashed = hash_password("admin1234")
    assert hashed != "admin1234"
    assert verify_password("admin1234", hashed)


def test_auth_login_invalid_credentials(client: TestClient):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_authenticate_user_with_seeded_admin():
    connection = connect()
    try:
        user = authenticate_user(connection, "admin", "admin123")
        assert user is not None
        assert user["role"] == "admin"
        assert authenticate_user(connection, "admin", "wrong") is None
    finally:
        release_connection(connection)
