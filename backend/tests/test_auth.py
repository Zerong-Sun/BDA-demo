import pytest
from fastapi.testclient import TestClient

from backend.app.auth.service import hash_password, validate_password_strength


def test_validate_password_strength_accepts_mixed():
    validate_password_strength("admin1234")


def test_validate_password_strength_rejects_short():
    with pytest.raises(ValueError, match="weak_password"):
        validate_password_strength("abc1")


def test_hash_password_roundtrip():
    hashed = hash_password("admin1234")
    assert hashed != "admin1234"


def test_auth_login_invalid_credentials(client: TestClient):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401
