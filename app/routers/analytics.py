
from __future__ import annotations

import json
import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.security import (require_roles, AccessClaims, get_share_context)
from app.domain.catalog import (QueryIn, build_cube_query, catalog_doc)
from app.infra.cube_client import cube_load, CubeError


router = APIRouter(prefix="/analytics", tags=["analytics"])


# -----------------------------------------------------------------------------
# Helpers de cache HTTP (ETag + SWR)
# -----------------------------------------------------------------------------

def _make_etag(body_bytes: bytes) -> str:
    return hashlib.md5(body_bytes).hexdigest()


def _cache_headers(response: JSONResponse, etag: str) -> None:
    response.headers["ETag"] = etag
    response.headers[
        "Cache-Control"
    ] = f"max-age={settings.CACHE_MAX_AGE}, stale-while-revalidate={settings.CACHE_SWR}"
    response.headers["Vary"] = "Authorization"


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.get("/catalog")
def get_catalog( _user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin"))):
    doc = catalog_doc()
    return {
        "measures": doc.measures,
        "dimensions": doc.dimensions,
        "grains": doc.grains,
        "default_time_dimension": doc.default_time_dimension,
    }


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
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()

    # 5) ETag + SWR: se If-None-Match bate, devolve 304
    etag = _make_etag(body)
    inm = request.headers.get("If-None-Match")
    if inm and inm == etag:
        resp = JSONResponse(status_code=304, content=None)
        _cache_headers(resp, etag)
        return resp

    # Caso contrário, devolve 200 com corpo + headers de cache
    resp = JSONResponse(status_code=200, content=payload)
    _cache_headers(resp, etag)
    return resp
