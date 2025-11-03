"""Delivery domain endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.security import AccessClaims, require_roles
from app.services.dependencies import get_delivery_service
from app.services.delivery_service import DeliveryService


router = APIRouter(prefix="/delivery", tags=["delivery"])


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _parse_iso8601(value: str) -> datetime:
    """Parse ISO8601 strings (aceitando sufixo Z) e normaliza para UTC."""
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Data/hora inválida: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _default_period(days: int = 30) -> tuple[datetime, datetime]:
    """Retorna intervalo padrão (últimos *days*) em datetime UTC."""
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now


def _validate_user_store_access(store_id: Optional[int], user_stores: list[int]) -> None:
    """Validate if user has access to the requested store."""
    # Se user_stores está vazio, usuário tem acesso a todas as lojas (admin)
    if not user_stores:
        return
    # Se store_id foi especificado, verificar se usuário tem acesso
    if store_id is not None and store_id not in user_stores:
        raise HTTPException(status_code=403, detail="Acesso negado à loja especificada")


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------


class DeliveryMetricsResponse(BaseModel):
    """Delivery metrics response model."""
    total_deliveries: int
    avg_minutes: float
    p50_minutes: float
    p90_minutes: float
    p95_minutes: float
    within_sla_count: int
    within_sla_pct: float


class DeliveryCityRankRow(BaseModel):
    """Delivery city rank response model."""
    city: str
    deliveries: int
    avg_minutes: float
    p90_minutes: float


class DeliveryNeighborhoodRow(BaseModel):
    """Delivery neighborhood response model."""
    neighborhood: str
    deliveries: int
    avg_minutes: float
    p90_minutes: float


class DeliveryRegionsRow(BaseModel):
    """Delivery regions response model."""
    city: str
    neighborhood: str
    deliveries: int
    avg_minutes: float
    p90_minutes: float


class DeliveryPercentilesResponse(BaseModel):
    """Delivery percentiles response model."""
    avg_minutes: float
    p50_minutes: float
    p90_minutes: float
    p95_minutes: float
    within_sla_pct: float


class DeliveryStatsResponse(BaseModel):
    """Delivery stats response model."""
    total_deliveries: int
    fastest_minutes: float
    slowest_minutes: float
    avg_minutes: float


class DeliveryStoreRankRow(BaseModel):
    """Delivery store rank response model."""
    store_id: int
    store_name: str
    deliveries: int
    avg_minutes: float
    p90_minutes: float


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.get("/metrics", response_model=DeliveryMetricsResponse)
def get_delivery_metrics(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: DeliveryService = Depends(get_delivery_service),
):
    """Métricas gerais de entrega."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Validate store access
    allowed_store_ids = user.stores or []
    _validate_user_store_access(store_id, allowed_store_ids)
    
    # Apply filters
    store_ids = [store_id] if store_id else allowed_store_ids or None
    channel_ids = [channel_id] if channel_id else None

    # Get data from service
    metrics = service.get_metrics(start_dt, end_dt, store_ids, channel_ids)

    if metrics is None:
        return DeliveryMetricsResponse(
            total_deliveries=0,
            avg_minutes=0.0,
            p50_minutes=0.0,
            p90_minutes=0.0,
            p95_minutes=0.0,
            within_sla_count=0,
            within_sla_pct=0.0,
        )

    return DeliveryMetricsResponse(
        total_deliveries=metrics.total_deliveries,
        avg_minutes=float(metrics.avg_delivery_minutes),
        p50_minutes=float(metrics.p50_delivery_minutes),
        p90_minutes=float(metrics.p90_delivery_minutes),
        p95_minutes=float(metrics.p95_delivery_minutes),
        within_sla_count=metrics.within_sla_count,
        within_sla_pct=float(metrics.within_sla_percentage),
    )


@router.get("/cities-rank", response_model=list[DeliveryCityRankRow])
def get_delivery_cities_rank(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    limit: int = Query(10, ge=1, le=100, description="Quantidade de cidades no ranking"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: DeliveryService = Depends(get_delivery_service),
):
    """Ranking de cidades por volume de entregas."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Validate store access
    allowed_store_ids = user.stores or []
    _validate_user_store_access(store_id, allowed_store_ids)
    
    # Apply filters
    store_ids = [store_id] if store_id else allowed_store_ids or None
    channel_ids = [channel_id] if channel_id else None

    # Get data from service
    cities = service.get_by_city(start_dt, end_dt, store_ids, channel_ids, limit)

    return [
        DeliveryCityRankRow(
            city=c.city,
            deliveries=c.total_deliveries,
            avg_minutes=float(c.avg_delivery_minutes),
            p90_minutes=float(c.p90_delivery_minutes),
        )
        for c in cities
    ]


@router.get("/neighborhoods", response_model=list[DeliveryNeighborhoodRow])
def get_delivery_neighborhoods(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    limit: int = Query(10, ge=1, le=100, description="Quantidade de bairros no ranking"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: DeliveryService = Depends(get_delivery_service),
):
    """Ranking de bairros por volume de entregas."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Validate store access
    allowed_store_ids = user.stores or []
    _validate_user_store_access(store_id, allowed_store_ids)
    
    # Apply filters
    store_ids = [store_id] if store_id else allowed_store_ids or None
    channel_ids = [channel_id] if channel_id else None

    # Get data from service
    neighborhoods = service.get_by_neighborhood(start_dt, end_dt, store_ids, channel_ids, limit)

    return [
        DeliveryNeighborhoodRow(
            neighborhood=n.neighborhood or "",
            deliveries=n.total_deliveries,
            avg_minutes=float(n.avg_delivery_minutes),
            p90_minutes=float(n.p90_delivery_minutes),
        )
        for n in neighborhoods
    ]


@router.get("/regions", response_model=list[DeliveryRegionsRow])
def get_delivery_regions(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    city: Optional[str] = Query(None, description="Filtrar por cidade"),
    limit: int = Query(50, ge=1, le=500, description="Quantidade de regiões no ranking"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: DeliveryService = Depends(get_delivery_service),
):
    """Desempenho de entrega por região."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Apply filters
    allowed_store_ids = user.stores or []
    _validate_user_store_access(store_id, allowed_store_ids)
    store_ids = [store_id] if store_id else allowed_store_ids or None
    channel_ids = [channel_id] if channel_id else None

    # Get data from service
    regions = service.get_regions(start_dt, end_dt, store_ids, channel_ids, city, limit)

    return [DeliveryRegionsRow(**r) for r in regions]


@router.get("/percentiles", response_model=DeliveryPercentilesResponse)
def get_delivery_percentiles(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    sla_minutes: int = Query(45, description="SLA em minutos"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: DeliveryService = Depends(get_delivery_service),
):
    """Percentis de entrega."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Validate store access
    allowed_store_ids = user.stores or []
    _validate_user_store_access(store_id, allowed_store_ids)
    
    # Apply filters
    store_ids = [store_id] if store_id else allowed_store_ids or None
    channel_ids = [channel_id] if channel_id else None

    # Get data from service
    data = service.get_percentiles(start_dt, end_dt, store_ids, channel_ids, sla_minutes)

    return DeliveryPercentilesResponse(**data)


@router.get("/stats", response_model=DeliveryStatsResponse)
def get_delivery_stats(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: DeliveryService = Depends(get_delivery_service),
):
    """Estatísticas gerais de entregas."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Validate store access
    allowed_store_ids = user.stores or []
    _validate_user_store_access(store_id, allowed_store_ids)
    
    # Apply filters
    store_ids = [store_id] if store_id else allowed_store_ids or None
    channel_ids = [channel_id] if channel_id else None

    # Get data from service
    data = service.get_stats(start_dt, end_dt, store_ids, channel_ids)

    return DeliveryStatsResponse(**data)


@router.get("/stores-rank", response_model=list[DeliveryStoreRankRow])
def get_delivery_stores_rank(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    order_by: str = Query("slowest", description="Ordenação: 'slowest' (mais lentas) ou 'fastest' (mais rápidas)"),
    limit: int = Query(10, ge=1, le=50, description="Quantidade de lojas no ranking"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: DeliveryService = Depends(get_delivery_service),
):
    """Ranking de lojas por tempo de entrega."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Validate store access
    allowed_store_ids = user.stores or []
    _validate_user_store_access(store_id, allowed_store_ids)
    
    # Apply filters
    store_ids = [store_id] if store_id else allowed_store_ids or None
    channel_ids = [channel_id] if channel_id else None

    # Get data from service
    stores = service.get_stores_rank(start_dt, end_dt, store_ids, channel_ids, limit)

    return [DeliveryStoreRankRow(**s) for s in stores]
