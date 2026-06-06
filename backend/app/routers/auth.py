import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth.service import (
    authenticate_user,
    create_access_token,
    create_user,
    get_current_user,
    list_users,
    require_role,
)
from ..db import get_connection
from ..utils.response import envelope

router = APIRouter(prefix="/auth")


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "researcher"
    display_name: str | None = None


@router.post("/login")
def login(payload: LoginRequest, connection: sqlite3.Connection = Depends(get_connection)):
    user = authenticate_user(connection, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    token = create_access_token({"sub": user["username"], "role": user["role"], "uid": user["user_id"]})
    return envelope({
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"],
            "display_name": user.get("display_name"),
        },
    })


@router.post("/refresh")
def refresh_token(user: dict = Depends(get_current_user)):
    token = create_access_token({"sub": user["username"], "role": user["role"], "uid": user["user_id"]})
    return envelope({"access_token": token, "token_type": "bearer"})


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return envelope({
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "display_name": user.get("display_name"),
    })


users_router = APIRouter(prefix="/users")


@users_router.get("")
def get_users(
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    return envelope(list_users(connection))


@users_router.post("")
def post_user(
    payload: CreateUserRequest,
    connection: sqlite3.Connection = Depends(get_connection),
    _admin: dict = Depends(require_role("admin")),
):
    try:
        user = create_user(
            connection,
            username=payload.username,
            password=payload.password,
            role=payload.role,
            display_name=payload.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope({
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "display_name": user.get("display_name"),
    })

router.include_router(users_router)
