from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.security import (
    require_roles,
    AccessClaims,
    create_share_token,
    decode_share_token,
)
from app.domain.catalog import QueryIn

router = APIRouter(prefix="/share", tags=["share"])


# -----------------------------------------------------------------------------
# Models (entrada/saída)
# -----------------------------------------------------------------------------

class ShareCreateIn(BaseModel):
    q: QueryIn
    stores: Optional[List[int]] = Field(default=None, description="Subconjunto de lojas do usuário")


class ShareCreateOut(BaseModel):
    token: str
    link_path: str = "/analytics"
    link_with_token: str


class ShareInspectOut(BaseModel):
    ok: bool
    exp: int
    stores: List[int]
    q: dict


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _validate_subset(user_store_ids: List[int], requested: Optional[List[int]]) -> List[int]:
    base = set(user_store_ids or [])
    if requested is None:
        return sorted(base)
    req = set(requested)
    if not req.issubset(base):
        raise HTTPException(status_code=403, detail="Escopo de lojas inválido: não é subconjunto do usuário.")
    return sorted(req)


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.post("", response_model=ShareCreateOut)
def create_share(body: ShareCreateIn, user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin"))):

    # 1) Validação de QueryIn já é garantida pelo Pydantic (catalog.py).
    stores = _validate_subset(user_store_ids=user.stores or [], requested=body.stores)

    # 2) Emitir JWT de share travando q + stores
    token = create_share_token(query_lock=body.q.model_dump(by_alias=True), stores=stores)

    # 3) Devolver token e um caminho pronto para ser anexado na UI
    link_path = "/analytics"
    link_with_token = f"{link_path}?share_token={token}"
    return ShareCreateOut(token=token, link_path=link_path, link_with_token=link_with_token)


@router.get("/validate", response_model=ShareInspectOut)
def validate_share(share_token: str = Query(..., description="JWT de link compartilhado")):
    try:
        claims = decode_share_token(share_token)
    except HTTPException:
        raise
    return ShareInspectOut(
        ok=True,
        exp=claims.exp,
        stores=claims.stores or [],
        q=claims.q,
    )
