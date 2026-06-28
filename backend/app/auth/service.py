from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..db import get_connection
from ..settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

ROLES = frozenset({"admin", "researcher", "viewer"})

MIN_PASSWORD_LENGTH = 8


def validate_password_strength(password: str) -> None:
    """Enforce a minimum length and basic complexity.

    Raises ``ValueError('weak_password')`` when the password fails the policy:
    at least 8 characters and a mix of letters and digits.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError("weak_password")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise ValueError("weak_password")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict[str, Any], expires_minutes: int | None = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(
        minutes=expires_minutes or settings.bda_jwt_expire_minutes
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.bda_jwt_secret, algorithm=settings.bda_jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.bda_jwt_secret, algorithms=[settings.bda_jwt_algorithm])


def get_user_by_username(connection: sqlite3.Connection, username: str) -> dict | None:
    from ..repositories.base import decode_row

    row = connection.execute(
        "SELECT * FROM users WHERE username = ? AND enabled = 1",
        (username,),
    ).fetchone()
    return decode_row(row)


def create_user(
    connection: sqlite3.Connection,
    *,
    username: str,
    password: str,
    role: str = "researcher",
    display_name: str | None = None,
) -> dict:
    if role not in ROLES:
        raise ValueError("invalid_role")
    validate_password_strength(password)
    if get_user_by_username(connection, username):
        raise ValueError("username_taken")
    user_id = f"user_{uuid.uuid4().hex[:10]}"
    connection.execute(
        """
        INSERT INTO users (user_id, username, password_hash, role, display_name, enabled, created_at)
        VALUES (?, ?, ?, ?, ?, 1, ?)
        """,
        (
            user_id,
            username,
            hash_password(password),
            role,
            display_name or username,
            datetime.now(UTC).isoformat(),
        ),
    )
    return get_user_by_username(connection, username) or {}


def authenticate_user(connection: sqlite3.Connection, username: str, password: str) -> dict | None:
    user = get_user_by_username(connection, username)
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return user


def list_users(connection: sqlite3.Connection) -> list[dict]:
    from ..repositories.base import decode_rows

    rows = connection.execute(
        "SELECT user_id, username, role, display_name, enabled, created_at FROM users"
    ).fetchall()
    return decode_rows(rows)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    connection: sqlite3.Connection = Depends(get_connection),
) -> dict | None:
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        username = payload.get("sub")
        if not username:
            return None
        return get_user_by_username(connection, username)
    except JWTError:
        return None


def get_current_user(user: dict | None = Depends(get_current_user_optional)) -> dict:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    return user


def require_role(*roles: str):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user

    return checker


def verify_project_access(connection: sqlite3.Connection, user: dict, project_id: str) -> bool:
    if user.get("role") == "admin":
        return True
    row = connection.execute(
        "SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ? LIMIT 1",
        (project_id, user["user_id"]),
    ).fetchone()
    if row:
        return True
    if user.get("role") in ("researcher", "viewer"):
        org_row = connection.execute(
            """
            SELECT 1 FROM projects p
            JOIN organization_members om ON om.organization_id = p.organization_id
            WHERE p.project_id = ? AND om.user_id = ?
            LIMIT 1
            """,
            (project_id, user["user_id"]),
        ).fetchone()
        return org_row is not None
    return False
