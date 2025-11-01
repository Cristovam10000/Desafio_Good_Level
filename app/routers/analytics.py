"""
Refactored analytics endpoints following Clean Code principles.
Eliminated massive duplication by using service classes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel

from app.core.ai import AIIntegrationError
from app.core.cache import etag_json
from app.core.security import AccessClaims, require_roles
from app.services.analytics_services import (
    AnalyticsFilters,
    AnalyticsServiceFactory,
    BaseAnalyticsService,
)
from app.services.anomaly_detector import AnomalyDetectorError, detect_anomalies
from app.services.insights import build_dataset, generate_dataset_insights

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ------------------------------------------------------------------------------
# Request/Response Models
# ------------------------------------------------------------------------------


class AnalyticsQuery(BaseModel):
    """Query parameters for analytics endpoints."""
    start: str
    end: str
    store_ids: Optional[List[int]] = None
    channel_ids: Optional[List[int]] = None


# ------------------------------------------------------------------------------
# Analytics Endpoints
# ------------------------------------------------------------------------------


def _execute_analytics_query(
    service_type: str,
    filters: AnalyticsFilters,
    request: Request,
) -> dict:
    """Execute analytics query using service pattern."""
    service = AnalyticsServiceFactory.create_service(service_type, filters)
    data = service.execute_query()
    response = service.build_response(data)

    return etag_json(request, response.model_dump())


@router.get("/top-additions")
def get_top_additions(
    request: Request,
    start: str = Query(..., description="Data inicial (ISO format)"),
    end: str = Query(..., description="Data final (ISO format)"),
    store_ids: Optional[List[int]] = Query(None, description="IDs das lojas"),
    channel_ids: Optional[List[int]] = Query(None, description="IDs dos canais"),
    _: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
) -> dict:
    """
    Top produtos adicionados ao carrinho por período.
    Retorna produtos mais adicionados com quantidade e receita.
    """
    filters = AnalyticsFilters.from_params(start, end, store_ids, channel_ids)
    return _execute_analytics_query("top-additions", filters, request)


@router.get("/top-removals")
def get_top_removals(
    request: Request,
    start: str = Query(..., description="Data inicial (ISO format)"),
    end: str = Query(..., description="Data final (ISO format)"),
    store_ids: Optional[List[int]] = Query(None, description="IDs das lojas"),
    channel_ids: Optional[List[int]] = Query(None, description="IDs dos canais"),
    _: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
) -> dict:
    """
    Top produtos removidos do carrinho por período.
    Retorna produtos mais removidos com quantidade perdida e receita perdida.
    """
    filters = AnalyticsFilters.from_params(start, end, store_ids, channel_ids)
    return _execute_analytics_query("top-removals", filters, request)


@router.get("/delivery-time-by-region")
def get_delivery_time_by_region(
    request: Request,
    start: str = Query(..., description="Data inicial (ISO format)"),
    end: str = Query(..., description="Data final (ISO format)"),
    store_ids: Optional[List[int]] = Query(None, description="IDs das lojas"),
    channel_ids: Optional[List[int]] = Query(None, description="IDs dos canais"),
    _: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
) -> dict:
    """
    Tempo de entrega por região.
    Retorna estatísticas de entrega (média e P90) por cidade/bairro.
    """
    filters = AnalyticsFilters.from_params(start, end, store_ids, channel_ids)
    return _execute_analytics_query("delivery-time-by-region", filters, request)


@router.get("/payment-mix-by-channel")
def get_payment_mix_by_channel(
    request: Request,
    start: str = Query(..., description="Data inicial (ISO format)"),
    end: str = Query(..., description="Data final (ISO format)"),
    store_ids: Optional[List[int]] = Query(None, description="IDs das lojas"),
    channel_ids: Optional[List[int]] = Query(None, description="IDs dos canais"),
    _: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
) -> dict:
    """
    Mix de métodos de pagamento por canal.
    Retorna distribuição de pagamentos por método e canal.
    """
    filters = AnalyticsFilters.from_params(start, end, store_ids, channel_ids)
    return _execute_analytics_query("payment-mix-by-channel", filters, request)


# ------------------------------------------------------------------------------
# AI Insights Endpoint
# ------------------------------------------------------------------------------


def _default_period(days: int = 30) -> tuple[str, str]:
    """Generate default period for insights."""
    from datetime import datetime, timedelta
    end = datetime.now()
    start = end - timedelta(days=days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _validate_range(start: str, end: str) -> None:
    """Validate date range."""
    from datetime import datetime
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
        if start_date > end_date:
            raise ValueError("Data inicial deve ser menor que data final")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/metrics")
async def analytics_metrics(
    request: Request,
    start: Optional[str] = Query(None, description="Início do período (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="Fim do período (YYYY-MM-DD)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja"),
    channel_ids: Optional[str] = Query(None, description="Lista de canais separados por vírgula"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
) -> Response:
    """
    Endpoint OTIMIZADO que retorna apenas os dados agregados (sales_daily) 
    SEM chamar a IA do Gemini. Muito mais rápido para o dashboard.
    """
    logging.info(f"[metrics] Iniciando - start={start}, end={end}, user={user.sub}")
    
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
            city=None,
            top_products=5,
            top_locations=5,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.error(f"Erro ao construir dataset: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(exc)}") from exc

    response_payload: Dict[str, Any] = {
        "ok": True,
        "period": {"start": start, "end": end},
        "preview": dataset.preview(),
        "totals": {
            "revenue": float(dataset.sales_daily["revenue"].sum()),
            "orders": int(dataset.sales_daily["orders"].sum()),
            "items_value": float(dataset.sales_daily["items_value"].sum()),
            "discounts": float(dataset.sales_daily["discounts"].sum()),
            "avg_ticket": float(dataset.sales_daily["avg_ticket"].mean()) if len(dataset.sales_daily) > 0 else 0.0,
        },
    }

    # Cache agressivo (5 minutos) pois não tem IA
    return etag_json(request, response_payload, max_age=300, swr=600)


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


# ------------------------------------------------------------------------------
# Anomaly Detection Endpoint
# ------------------------------------------------------------------------------


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
        from datetime import datetime, timedelta
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