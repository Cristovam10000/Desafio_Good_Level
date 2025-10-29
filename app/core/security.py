from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field, ValidationError
from app.core.config import settings

# -----------------------------------------------------------------------------
# 1) Hash e verificação de senhas
# -----------------------------------------------------------------------------

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated= "auto")

def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)

# -----------------------------------------------------------------------------
# 2) Modelos de payload (claims) dos tokens
# -----------------------------------------------------------------------------

tokenType = Literal["access", "refresh", "share"]

class BaseClaims(BaseModel):
    sub: str
    type: tokenType
    exp: int

class AccessClaims(BaseModel):
    roles: List[str] = Field(default_factory=list)
    stores: List[int] = Field(default_factory=list)

class RefreshClaims(BaseModel):
    pass

class ShareClaims(BaseModel):
    q: Dict[str, Any]
    stores: List[int] = Field(default_factory=list)
    mode: str = "view"

# -----------------------------------------------------------------------------
# 3) Helpers internos para emitir e decodificar JWT
# -----------------------------------------------------------------------------

_ALG = settings.JWT_ALGORITHM
bearer_scheme = HTTPBearer(auto_error=True)

def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)

def _exp_in(minutes: int) -> int:
    return int((_utcnow() + timedelta(minutes=minutes)).timestamp())

def _encode(payload: Dict[str, Any], secret: str) -> str:
    return jwt.encode(payload, secret, algorithm=_ALG)

def _decode(token: str, secret: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, secret, algorithms=[_ALG])
    except JWTError:
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado."
        )
    
# -----------------------------------------------------------------------------
# 4) Emissão de tokens (access, refresh, share)
# ----------------------------------------------------------------------------- 

def create_access_token(*, user_id: str, roles: List[str], stores: List[int]) -> str:
    claims = AccessClaims(
        sub=user_id,
        type="access",
        exp=_exp_in(settings.ACCESS_TOKEN_MINUTES),
        roles=roles,
        stores=stores
    )
    return _encode(claims.model_dump(), settings.JWT_SECRET)

def create_refresh_token(*, user_id: str) -> str:
    claims = RefreshClaims(
        sub=user_id,
        type="refresh",
        exp=_exp_in(settings.REFRESH_TOKEN_MINUTES)
    )
    return _encode(claims.model_dump(), settings.JWT_REFRESH_SECRET)

def create_share_token(*, query_lock: Dict[str, Any], stores: List[int]) -> str:
    claims = ShareClaims(
        sub="share",
        type="share",
        exp=_exp_in(settings.ACCESS_TOKEN_MINUTES),
        q=query_lock,
        stores=stores,
        mode="view"
    )
    return _encode(claims.model_dump(), settings.JWT_SHARE_SECRET)


# -----------------------------------------------------------------------------
# 5) Decodificação/validação de tokens por tipo
# ---------------------------------------------------------------

def decode_access_token(token:str) -> AccessClaims:
    data = _decode(token, settings.JWT_SECRET)
    try:
        return AccessClaims(**data)
    except ValidationError:
        raise HTTPException(status_code=401, detail="Token de acesso inválido.")

def decode_refresh_token(token:str) -> RefreshClaims:
    data = _decode(token, settings.JWT_REFRESH_SECRET)
    try:
        return RefreshClaims(**data)
    except ValidationError:
        raise HTTPException(status_code=401, detail="Re")

def decode_share_token(token:str) -> ShareClaims:
    data = _decode(token, settings.JWT_SHARE_SECRET)
    try:
        return ShareClaims(**data)
    except ValidationError:
        raise HTTPException(status_code=401, detail="Share token inválido.")

# -----------------------------------------------------------------------------
# 6) Dependências do FastAPI para autenticação/autorização
# -----------------------------------------------------------------------------

def get_current_acess(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> AccessClaims:
    token = creds.credentials
    claims = decode_access_token(token)
    return claims

def require_roles(*allowed_roles: str):
    def _dep(claims: AccessClaims = Depends(get_current_acess)) -> AccessClaims:
        roles = set(map(str.lower, claims.roles or []))
        allowed = set(map(str.lower, allowed_roles))
        if roles.isdisjoint(allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão negada."
            )
        return claims
    return _dep

def get_share_context(token: Optional[str] = None,) -> Optional[ShareClaims]:
    if not token:
        return None
    return decode_share_token(token)