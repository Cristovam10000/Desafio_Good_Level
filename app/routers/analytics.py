
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.core.cache import etag_json
from app.core.security import (require_roles, AccessClaims, get_share_context)
from app.domain.catalog import (QueryIn, build_cube_query, catalog_doc)
from app.infra.cube_client import cube_load, CubeError


router = APIRouter(prefix="/analytics", tags=["analytics"])


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.get("/catalog")
def get_catalog(
    request: Request,
    _user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    doc = catalog_doc()
    payload = {
        "measures": doc.measures,
        "dimensions": doc.dimensions,
        "grains": doc.grains,
        "default_time_dimension": doc.default_time_dimension,
    }
    return etag_json(request, payload)


@router.get("")
async def analytics(
    request: Request,
    q: QueryIn = Depends(),
    share_token: Optional[str] = Query(None, description="JWT de link compartilhado"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):

    # 1) Share link tem prioridade: ignora q e usa claims.q travado
    share = get_share_context(share_token)
    if share:
        try:
            q = QueryIn.model_validate(share.q)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Share token com query inválida: {e}")

        user_store_ids = share.stores or []
    else:
        user_store_ids = user.stores or []

    # 2) Monta a query final do Cube (allow-list do catálogo garante segurança)
    try:
        cube_query = build_cube_query(q, user_store_ids=user_store_ids)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3) Chama o Cube com resiliência (timeout/retries no cliente)
    try:
        cube_result = await cube_load(cube_query, request_id=request.headers.get("X-Request-Id"))
    except CubeError as ce:
        raise HTTPException(
            status_code=ce.status_code if 400 <= ce.status_code < 600 else 502,
            detail={"message": ce.message, "details": ce.details},
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Falha ao consultar Cube: {e}")

    # 4) Monta a resposta final (incluindo a query efetiva para transparência)
    payload = {
        "ok": True,
        "query_effective": cube_query,
        "result": cube_result,
    }

    return etag_json(request, payload)
