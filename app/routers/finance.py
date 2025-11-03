"""Finance domain endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.security import AccessClaims, require_roles
from app.services.finance_service import FinanceService


router = APIRouter(prefix="/finance", tags=["finance"])


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


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------


class PaymentMixRow(BaseModel):
    """Payment mix response model."""
    payment_type: str
    channel_name: str
    revenue: float
    transactions: int
    pct: float


class NetVsGrossResponse(BaseModel):
    """Net vs gross revenue response model."""
    gross_revenue: float
    total_discounts: float
    service_fees: float
    delivery_fees: float
    net_revenue: float
    discount_pct: float


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.get("/payments-mix", response_model=list[PaymentMixRow])
def get_payments_mix(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    channel_id: Optional[int] = Query(None, description="ID do canal para filtrar"),
    store_id: Optional[int] = Query(None, description="ID da loja para filtrar"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Mix de pagamentos por canal."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Apply filters
    allowed_store_ids = user.stores or []
    
    # Combine user permissions with request filters
    store_ids_filter = None
    if store_id is not None:
        # User requested specific store - apply if allowed
        if not allowed_store_ids or store_id in allowed_store_ids:
            store_ids_filter = [store_id]
    elif allowed_store_ids:
        # No specific store requested, but user has restrictions
        store_ids_filter = allowed_store_ids
    
    channel_ids_filter = [channel_id] if channel_id is not None else None

    # Get data from service
    service = FinanceService()
    data = service.get_payments_mix(start_dt, end_dt, store_ids_filter, channel_ids_filter)

    return [PaymentMixRow(**row) for row in data]


@router.get("/net-vs-gross", response_model=NetVsGrossResponse)
def get_net_vs_gross(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    channel_id: Optional[int] = Query(None, description="ID do canal para filtrar"),
    store_id: Optional[int] = Query(None, description="ID da loja para filtrar"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Receita líquida vs bruta."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Apply filters
    allowed_store_ids = user.stores or []
    
    # Combine user permissions with request filters
    store_ids_filter = None
    if store_id is not None:
        # User requested specific store - apply if allowed
        if not allowed_store_ids or store_id in allowed_store_ids:
            store_ids_filter = [store_id]
    elif allowed_store_ids:
        # No specific store requested, but user has restrictions
        store_ids_filter = allowed_store_ids
    
    channel_ids_filter = [channel_id] if channel_id is not None else None

    # Get data from service
    service = FinanceService()
    data = service.get_net_vs_gross(start_dt, end_dt, store_ids_filter, channel_ids_filter)

    return NetVsGrossResponse(**data)
