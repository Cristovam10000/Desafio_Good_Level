"""Sales domain endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.security import AccessClaims, require_roles
from app.services.dependencies import get_sales_service
from app.services.sales_service import SalesService


router = APIRouter(prefix="/sales", tags=["sales"])


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
    if store_id is not None and store_id not in user_stores:
        raise HTTPException(status_code=403, detail="Acesso negado à loja especificada")


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------


class SalesSummaryResponse(BaseModel):
    """Sales summary response model."""
    revenue: float
    orders: int
    avg_ticket: float
    discount_pct: float


class SalesByChannelRow(BaseModel):
    """Sales by channel response model."""
    channel_id: int
    channel_name: str
    revenue: float
    orders: int
    pct: float


class SalesByDayRow(BaseModel):
    """Sales by day response model."""
    bucket_day: str
    revenue: float
    orders: int
    avg_ticket: float


class SalesHourRow(BaseModel):
    """Sales by hour response model."""
    hour: int
    revenue: float
    orders: int


class DiscountReasonRow(BaseModel):
    """Discount reason response model."""
    discount_reason: str
    occurrences: int
    total_discount_value: float
    avg_discount: float


class SalesByWeekdayRow(BaseModel):
    """Sales by weekday response model."""
    weekday: int
    weekday_name: str
    revenue: float
    orders: int
    avg_ticket: float


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.get("/summary", response_model=SalesSummaryResponse)
def get_sales_summary(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: SalesService = Depends(get_sales_service),
):
    """Resumo de vendas para o período."""
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
    summary = service.get_summary(start_dt, end_dt, store_ids, channel_ids)

    if summary is None:
        return SalesSummaryResponse(revenue=0.0, orders=0, avg_ticket=0.0, discount_pct=0.0)

    return SalesSummaryResponse(
        revenue=float(summary.total_revenue),
        orders=summary.total_sales,
        avg_ticket=float(summary.average_ticket),
        discount_pct=float(summary.discount_rate),
    )


@router.get("/by-channel", response_model=list[SalesByChannelRow])
def get_sales_by_channel(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: SalesService = Depends(get_sales_service),
):
    """Vendas por canal."""
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

    # Get data from service
    channel_data = service.get_by_channel(start_dt, end_dt, store_ids, None)

    total_revenue = sum(float(data.total_revenue) for data in channel_data)

    return [
        SalesByChannelRow(
            channel_id=data.channel_id,
            channel_name=data.channel_name,
            revenue=float(data.total_revenue),
            orders=data.total_sales,
            pct=(float(data.total_revenue) / total_revenue * 100) if total_revenue else 0.0,
        )
        for data in channel_data
    ]


@router.get("/by-day", response_model=list[SalesByDayRow])
def get_sales_by_day(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: SalesService = Depends(get_sales_service),
):
    """Vendas por dia."""
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
    daily_data = service.get_by_day(start_dt, end_dt, store_ids, channel_ids)

    return [
        SalesByDayRow(
            bucket_day=data.day_iso,
            revenue=float(data.total_revenue),
            orders=data.order_count,
            avg_ticket=float(data.avg_ticket),
        )
        for data in daily_data
    ]


@router.get("/by-hour", response_model=list[SalesHourRow])
def get_sales_by_hour(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: SalesService = Depends(get_sales_service),
):
    """Vendas por hora do dia."""
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
    hourly_data = service.get_by_hour(start_dt, end_dt, store_ids, channel_ids)

    return [
        SalesHourRow(
            hour=row.hour,
            revenue=float(row.total_revenue),
            orders=row.order_count,
        )
        for row in hourly_data
    ]


@router.get("/discount-reasons", response_model=list[DiscountReasonRow])
def get_discount_reasons(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    limit: int = Query(10, ge=1, le=100, description="Quantidade de motivos no ranking"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: SalesService = Depends(get_sales_service),
):
    """Top motivos de desconto."""
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
    reasons = service.get_discount_reasons(start_dt, end_dt, store_ids, channel_ids, limit)

    result: list[DiscountReasonRow] = []
    for row in reasons:
        total = float(row.total_discount)
        qty = row.quantity
        result.append(
            DiscountReasonRow(
                discount_reason=row.reason,
                occurrences=qty,
                total_discount_value=total,
                avg_discount=total / qty if qty else 0.0,
            )
        )
    return result


@router.get("/by-weekday", response_model=list[SalesByWeekdayRow])
def get_sales_by_weekday(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: SalesService = Depends(get_sales_service),
):
    """Vendas por dia da semana."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Apply filters
    allowed_store_ids = user.stores or []

    # Get data from service
    weekday_data = service.get_by_weekday(start_dt, end_dt, allowed_store_ids or None)

    return [SalesByWeekdayRow(**row) for row in weekday_data]

