"""Authentication endpoints used by the frontend application."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.core.security import (
    AccessClaims,
    create_access_token,
    create_refresh_token,
    require_roles,
)
from app.domain.users import DemoUser, get_demo_user_by_email, get_demo_user_by_id


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    roles: list[str]
    stores: list[int]


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut


def _ensure_credentials(email: str, password: str) -> DemoUser:
    user = get_demo_user_by_email(email)
    if not user or user.password != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
        )
    return user


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    user = _ensure_credentials(payload.email, payload.password)

    access_token = create_access_token(
        user_id=user.id,
        roles=user.roles,
        stores=user.stores,
    )
    refresh_token = create_refresh_token(user_id=user.id)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_MINUTES * 60,
        user=UserOut(
            id=user.id,
            email=user.email,
            name=user.name,
            roles=user.roles,
            stores=user.stores,
        ),
    )


@router.get("/me", response_model=UserOut)
def me(claims: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin"))) -> UserOut:
    user = get_demo_user_by_id(claims.sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        roles=user.roles,
        stores=user.stores,
    )

