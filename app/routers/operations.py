"""Operations domain endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.security import AccessClaims, require_roles
from app.services.operations_service import OperationsService


router = APIRouter(prefix="/ops", tags=["operations"])


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


class PrepTimeRow(BaseModel):
    """Prep time metrics response model."""
    store_id: int
    store_name: str
    avg_prep_minutes: float
    p90_prep_minutes: float
    orders: int
    cancelled: int
    cancellation_rate: float


class CancellationsRow(BaseModel):
    """Cancellations timeseries response model."""
    bucket_day: datetime
    canceled: int
    total: int
    cancellation_rate: float


class CancellationReasonRow(BaseModel):
    """Cancellation reason response model."""
    reason: str
    percentage: float


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.get("/prep-time", response_model=list[PrepTimeRow])
def get_prep_time(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Tempo de preparação por loja."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Apply filters
    allowed_store_ids = user.stores or []

    # Get data from service
    service = OperationsService()
    data = service.get_prep_time_by_store(start_dt, end_dt, allowed_store_ids or None)

    return [PrepTimeRow(**row) for row in data]


@router.get("/cancellations", response_model=list[CancellationsRow])
def get_cancellations(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Série temporal de cancelamentos."""
    # Parse dates
    if start and end:
        start_dt = _parse_iso8601(start)
        end_dt = _parse_iso8601(end)
    else:
        start_dt, end_dt = _default_period(days=30)

    # Apply filters
    allowed_store_ids = user.stores or []

    # Get data from service
    service = OperationsService()
    data = service.get_cancellations_timeseries(start_dt, end_dt, allowed_store_ids or None)

    return [CancellationsRow(**row) for row in data]


@router.get("/cancellation-reasons", response_model=list[CancellationReasonRow])
def get_cancellation_reasons(
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """
    Ranking dos principais motivos de cancelamento.
    
    Nota: Como não há campo específico de motivo no banco de dados,
    retorna distribuição típica baseada em estudos de mercado.
    """
    service = OperationsService()
    data = service.get_cancellation_reasons()

    return [CancellationReasonRow(**row) for row in data]
