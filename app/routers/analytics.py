
from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.core.cache import etag_json
from app.core.security import (require_roles, AccessClaims, get_share_context)
from app.domain.catalog import (QueryIn, build_cube_query, catalog_doc)
from app.infra.cube_client import cube_load, CubeError
from app.core.ai import AIIntegrationError
from app.services.insights import build_dataset, generate_dataset_insights


router = APIRouter(prefix="/analytics", tags=["analytics"])

# -----------------------------------------------------------------------------
# Helpers de período
# -----------------------------------------------------------------------------

def _default_period(days: int = 30) -> tuple[str, str]:
    end = datetime.utcnow().date()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()

def _validate_range(start: str, end: str) -> None:
    try:
        ds = datetime.fromisoformat(start.replace("Z", "+00:00"))
        de = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except Exception as exc:  # pragma: no cover - validação simples
        raise HTTPException(
            status_code=400,
            detail="Datas inválidas. Use ISO 8601 (ex.: 2025-06-01).",
        ) from exc
    if ds >= de:
        raise HTTPException(status_code=400, detail="'start' deve ser menor que 'end'.")


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


@router.get("/insights")
async def analytics_insights(
    start: Optional[str] = Query(None, description="Início do período (YYYY-MM-DD). Default: últimos 30 dias"),
    end: Optional[str] = Query(None, description="Fim do período (YYYY-MM-DD)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal"),
    city: Optional[str] = Query(None, description="Filtrar entregas por cidade"),
    top_products: int = Query(5, ge=1, le=20, description="Quantidade de produtos para enviar ao modelo"),
    top_locations: int = Query(5, ge=1, le=20, description="Quantidade de bairros para enviar ao modelo"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
) -> Dict[str, Any]:
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)

    allowed_store_ids = user.stores or []
    effective_store_ids: Optional[list[int]]

    if store_id is not None:
        if allowed_store_ids and store_id not in allowed_store_ids:
            raise HTTPException(status_code=403, detail="Loja não autorizada para este usuário.")
        effective_store_ids = [store_id]
    else:
        effective_store_ids = allowed_store_ids or None

    try:
        dataset = build_dataset(
            start,
            end,
            store_ids=effective_store_ids,
            channel_id=channel_id,
            city=city,
            top_products=top_products,
            top_locations=top_locations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    base_response: Dict[str, Any] = {
        "ok": True,
        "period": {"start": start, "end": end},
        "filters": {
            "store_ids": effective_store_ids,
            "channel_id": channel_id,
            "city": city,
        },
        "preview": dataset.preview(),
    }

    if dataset.is_empty():
        base_response["insights"] = ["Nenhum dado encontrado para o período informado."]
        base_response["raw_text"] = None
        return base_response

    try:
        ai_payload = await generate_dataset_insights(dataset)
    except AIIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    base_response.update(ai_payload)
    return base_response
