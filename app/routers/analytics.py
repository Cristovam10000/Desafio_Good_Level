"""Analytics endpoints that orchestrate Cube queries and AI insights."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from app.core.ai import AIIntegrationError
from app.core.cache import etag_json
from app.core.security import AccessClaims, get_share_context, require_roles
from app.domain.catalog import QueryIn, build_cube_query, catalog_doc
from app.infra.cube_client import CubeError, cube_load
from app.services.insights import build_dataset, generate_dataset_insights
from app.services.anomaly_detector import detect_anomalies, AnomalyDetectorError


router = APIRouter(prefix="/analytics", tags=["analytics"])


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _default_period(days: int = 30) -> tuple[str, str]:
    """Return ISO dates representing the last *days* days."""
    end = datetime.utcnow().date()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def _validate_range(start: str, end: str) -> None:
    """Ensure the provided ISO dates form a valid, ordered interval."""
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - straightforward validation
        raise HTTPException(
            status_code=400,
            detail="Datas inválidas. Use ISO 8601 (ex.: 2025-06-01).",
        ) from exc
    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="'start' deve ser menor que 'end'.")


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.get("/catalog")
def get_catalog(
    request: Request,
    _: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Expose the allow-list of measures/dimensions made available by the Cube."""
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
    query_input: QueryIn = Depends(),
    share_token: Optional[str] = Query(None, description="JWT de link compartilhado"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """
    Execute a dynamic Cube query defined by `query_input`, optionally overridden by
    a shared link (`share_token`). Always restricts the scope to the stores present
    in the caller's access token.
    """

    if share_token:
        share = get_share_context(share_token)
        if share:
            try:
                query_input = QueryIn.model_validate(share.q)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Share token com query inválida: {exc}")
            user_store_ids = share.stores or []
        else:
            user_store_ids = user.stores or []
    else:
        user_store_ids = user.stores or []

    try:
        cube_query = build_cube_query(query_input, user_store_ids=user_store_ids)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        cube_response = await cube_load(cube_query, request_id=request.headers.get("X-Request-Id"))
    except CubeError as cube_exc:
        raise HTTPException(
            status_code=cube_exc.status_code if 400 <= cube_exc.status_code < 600 else 502,
            detail={"message": cube_exc.message, "details": cube_exc.details},
        )
    except Exception as exc:  # pragma: no cover - defensive path
        raise HTTPException(status_code=502, detail=f"Falha ao consultar Cube: {exc}")

    payload = {
        "ok": True,
        "query_effective": cube_query,
        "result": cube_response,
    }
    return etag_json(request, payload)


@router.get("/insights")
async def analytics_insights(
    request: Request,
    start: Optional[str] = Query(None, description="Início do período (YYYY-MM-DD). Default: últimos 30 dias"),
    end: Optional[str] = Query(None, description="Fim do período (YYYY-MM-DD)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal"),
    channel_ids: Optional[str] = Query(None, description="Lista de canais separados por vírgula"),
    city: Optional[str] = Query(None, description="Filtrar entregas por cidade"),
    top_products: int = Query(5, ge=1, le=20, description="Quantidade de produtos para enviar ao modelo"),
    top_locations: int = Query(5, ge=1, le=20, description="Quantidade de bairros para enviar ao modelo"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
) -> Response:
    """
    Constrói datasets agregados (MVs ou fallback) e solicita insights textuais ao
    Gemini. Retorna também uma prévia dos dados enviados ao modelo.
    """
    logging.info(f"[insights] Iniciando - start={start}, end={end}, user={user.sub}")
    
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)

    allowed_store_ids = user.stores or []
    channel_ids_list: Optional[list[int]] = None
    if channel_ids:
        try:
            parsed = [int(value.strip()) for value in channel_ids.split(",") if value.strip()]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="channel_ids deve conter apenas números separados por vírgula.") from exc
        channel_ids_list = parsed or None

    if channel_id is not None:
        if channel_ids_list is None:
            channel_ids_list = [channel_id]
        elif channel_id not in channel_ids_list:
            channel_ids_list.append(channel_id)

    if channel_ids_list:
        channel_ids_list = sorted(set(channel_ids_list))

    if store_id is not None:
        if allowed_store_ids and store_id not in allowed_store_ids:
            raise HTTPException(status_code=403, detail="Loja não autorizada para este usuário.")
        effective_store_ids: Optional[list[int]] = [store_id]
    else:
        effective_store_ids = allowed_store_ids or None

    try:
        dataset = build_dataset(
            start,
            end,
            store_ids=effective_store_ids,
            channel_ids=channel_ids_list,
            city=city,
            top_products=top_products,
            top_locations=top_locations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.error(f"Erro ao construir dataset: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(exc)}") from exc

    response_payload: Dict[str, Any] = {
        "ok": True,
        "period": {"start": start, "end": end},
        "filters": {
            "store_ids": effective_store_ids,
            "channel_id": channel_id,
            "channel_ids": channel_ids_list,
            "city": city,
        },
        "preview": dataset.preview(),
    }

    if dataset.is_empty():
        response_payload["insights"] = ["Nenhum dado encontrado para o período informado."]
        response_payload["raw_text"] = None
        return etag_json(request, response_payload, max_age=300, swr=600)

    try:
        ai_payload = await generate_dataset_insights(dataset)
    except AIIntegrationError as exc:
        logging.warning("AI insights indisponiveis: %s", exc)
        response_payload["ok"] = False
        response_payload["insights"] = [
            "Insights automaticos indisponiveis no momento. Configure a camada de IA para habilita-los."
        ]
        response_payload["raw_text"] = None
        response_payload["insights_error"] = str(exc)
        return etag_json(request, response_payload, max_age=60, swr=120)

    response_payload.update(ai_payload)
    # Cache mais agressivo para insights (5 minutos com SWR de 10 minutos)
    return etag_json(request, response_payload, max_age=300, swr=600)


@router.get("/anomalies")
async def detect_sales_anomalies(
    request: Request,
    start: Optional[str] = Query(None, description="Início do período (YYYY-MM-DD). Default: últimos 90 dias"),
    end: Optional[str] = Query(None, description="Fim do período (YYYY-MM-DD)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja"),
    channel_ids: Optional[str] = Query(None, description="Lista de canais separados por vírgula"),
    user: AccessClaims = Depends(require_roles("analyst", "manager", "admin")),
) -> Dict[str, Any]:
    """
    Detecta anomalias específicas nos dados de vendas:
    - Queda semanal (~30%)
    - Pico promocional (3x)
    - Crescimento linear (5%/mês)
    - Sazonalidade de produtos (80%+)
    """
    logging.info(f"[anomalies] Iniciando detecção - start={start}, end={end}, user={user.sub}")
    
    if not start or not end:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=90)
        start = start_date.isoformat()
        end = end_date.isoformat()
    
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    channel_ids_list: Optional[list[int]] = None
    
    if channel_ids:
        try:
            parsed = [int(value.strip()) for value in channel_ids.split(",") if value.strip()]
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="channel_ids deve conter apenas números separados por vírgula."
            ) from exc
        channel_ids_list = parsed or None
    
    if store_id is not None:
        if allowed_store_ids and store_id not in allowed_store_ids:
            raise HTTPException(status_code=403, detail="Loja não autorizada para este usuário.")
        effective_store_ids: Optional[list[int]] = [store_id]
    else:
        effective_store_ids = allowed_store_ids or None
    
    try:
        result = await detect_anomalies(
            start,
            end,
            store_ids=effective_store_ids,
            channel_ids=channel_ids_list,
        )
    except AnomalyDetectorError as exc:
        logging.warning("Detecção de anomalias indisponível: %s", exc)
        return etag_json(
            request,
            {
                "ok": False,
                "error": str(exc),
                "anomalies_found": 0,
                "results": {},
            },
            max_age=60,
            swr=120,
        )
    
    result["ok"] = True
    # Cache de 2 minutos com SWR de 5 minutos (dados mais dinâmicos)
    return etag_json(request, result, max_age=120, swr=300)
