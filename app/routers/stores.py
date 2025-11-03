"""Stores domain endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.security import AccessClaims, require_roles
from app.services.dependencies import get_store_service
from app.services.store_service import StoreService


router = APIRouter(prefix="/stores", tags=["stores"])


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _parse_iso8601(value: str) -> datetime:
    """Parse ISO8601 strings (aceitando sufixo Z) e normaliza para UTC."""
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Data/hora invÃƒÂ¡lida: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _default_period(days: int = 30) -> tuple[datetime, datetime]:
    """Retorna intervalo padrÃƒÂ£o (ÃƒÂºltimos *days*) em datetime UTC."""
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------


class StoreRow(BaseModel):
    """Store list response model."""
    id: int
    name: str
    city: str
    state: str
    is_active: bool


class StorePerformanceRow(BaseModel):
    """Store performance response model (compatÃ­vel com /specials)."""
    store_id: int
    store_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    revenue: float
    orders: int
    avg_ticket: float
    cancelled: int
    cancellation_rate: float
    growth_pct: Optional[float] = None
    avg_prep_minutes: Optional[float] = None
    p90_prep_minutes: Optional[float] = None


class StoreTimeseriesRow(BaseModel):
    """Store timeseries response model."""
    bucket_day: str
    revenue: float
    orders: int


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.get("", response_model=list[StoreRow])
def get_stores(
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: StoreService = Depends(get_store_service),
):
    """Lista todas as lojas acessÃƒÂ­veis ao usuÃƒÂ¡rio."""
    allowed_store_ids = user.stores or []
    
    stores = service.get_all(allowed_store_ids or None)

    return [
        StoreRow(
            id=s["id"],
            name=s["name"],
            city=s.get("city") or "",
            state=s.get("state") or "",
            is_active=bool(s.get("is_active", True)),
        )
        for s in stores
    ]


@router.get("/performance", response_model=list[StorePerformanceRow])
def get_stores_performance(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal especÃƒÂ­fico"),
    include_prep_time: bool = Query(False, description="Incluir tempo de preparo mÃƒÂ©dio"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: StoreService = Depends(get_store_service),
):
    """Performance das lojas no perÃƒÂ­odo."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Apply filters
    allowed_store_ids = user.stores or []
    channel_ids = [channel_id] if channel_id else None

    # Get data from service
    store_lookup = {row["id"]: row for row in service.get_all(allowed_store_ids or None)}
    metrics = service.get_metrics(start_dt, end_dt, allowed_store_ids, channel_ids, include_prep_time)

    return [
        StorePerformanceRow(
            store_id=m.store_id,
            store_name=m.store_name,
            city=store_lookup.get(m.store_id, {}).get("city"),
            state=store_lookup.get(m.store_id, {}).get("state"),
            revenue=float(m.total_revenue),
            orders=m.total_sales,
            avg_ticket=float(m.total_revenue / m.total_sales) if m.total_sales else 0.0,
            cancelled=m.cancelled_sales,
            cancellation_rate=float(m.cancellation_rate),
            growth_pct=None,
            avg_prep_minutes=float(m.avg_prep_minutes) if m.avg_prep_minutes is not None else None,
            p90_prep_minutes=float(m.p90_prep_minutes) if m.p90_prep_minutes is not None else None,
        )
        for m in metrics
    ]


@router.get("/timeseries", response_model=list[StoreTimeseriesRow])
def get_store_timeseries(
    store_id: int = Query(..., description="ID da loja"),
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: StoreService = Depends(get_store_service),
):
    """SÃƒÂ©rie temporal de uma loja especÃƒÂ­fica."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Validate store access
    allowed_store_ids = user.stores or []
    if store_id not in allowed_store_ids:
        raise HTTPException(status_code=403, detail="Acesso negado ÃƒÂ  loja")

    # Get data from service
    data = service.get_timeseries(store_id, start_dt, end_dt)

    return [
        StoreTimeseriesRow(
            bucket_day=str(row["bucket_day"]),
            revenue=row["revenue"],
            orders=row["orders"],
        )
        for row in data
    ]
