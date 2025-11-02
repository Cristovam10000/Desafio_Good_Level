"""Products domain endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.security import AccessClaims, require_roles
from app.services.product_service import ProductService


router = APIRouter(prefix="/products", tags=["products"])


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


class ProductTopSellersRow(BaseModel):
    """Top sellers response model."""
    product_id: int
    product_name: str
    qty: float
    revenue: float
    orders: int


class ProductLowSellersRow(BaseModel):
    """Low sellers response model."""
    product_id: int
    product_name: str
    qty: float
    revenue: float
    orders: int


class ProductWithMostCustomizationsRow(BaseModel):
    """Most customized products response model."""
    product_id: int
    product_name: str
    total_customizations: int
    orders: int
    avg_customizations_per_order: float


class ProductAddonsRow(BaseModel):
    """Product addons response model."""
    item_id: int
    item_name: str
    qty: float
    revenue: float
    uses: int


class ProductCombinationRow(BaseModel):
    """Product combinations response model."""
    product1_id: int
    product1_name: str
    product2_id: int
    product2_name: str
    times_together: int


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.get("/top-sellers", response_model=list[ProductTopSellersRow])
def get_top_sellers(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    limit: int = Query(10, ge=1, le=100, description="Quantidade de produtos no ranking"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Top produtos mais vendidos."""
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
    service = ProductService()
    products = service.get_top_sellers(start_dt, end_dt, store_ids, channel_ids, limit)

    return [
        ProductTopSellersRow(
            product_id=p.product_id,
            product_name=p.product_name,
            qty=float(p.total_quantity),
            revenue=float(p.total_revenue),
            orders=p.total_sales,
        )
        for p in products
    ]


@router.get("/low-sellers", response_model=list[ProductLowSellersRow])
def get_low_sellers(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    limit: int = Query(10, ge=1, le=100, description="Quantidade de produtos no ranking"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Produtos com menor volume de vendas."""
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
    service = ProductService()
    products = service.get_low_sellers(start_dt, end_dt, store_ids, channel_ids, limit)

    return [
        ProductLowSellersRow(
            product_id=p.product_id,
            product_name=p.product_name,
            qty=float(p.total_quantity),
            revenue=float(p.total_revenue),
            orders=p.total_sales,
        )
        for p in products
    ]


@router.get("/most-customized", response_model=list[ProductWithMostCustomizationsRow])
def get_most_customized(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    limit: int = Query(10, ge=1, le=100, description="Quantidade de produtos no ranking"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Produtos com mais customizações."""
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
    service = ProductService()
    products = service.get_most_customized(start_dt, end_dt, store_ids, channel_ids, limit)

    return [
        ProductWithMostCustomizationsRow(
            product_id=p["product_id"],
            product_name=p["product_name"],
            total_customizations=p["customization_count"],
            orders=p["total_sales"],
            avg_customizations_per_order=float(p.get("avg_customizations_per_order", 0.0)),
        )
        for p in products
    ]


@router.get("/addons/top", response_model=list[ProductAddonsRow])
def get_top_addons(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    limit: int = Query(10, ge=1, le=100, description="Quantidade de itens no ranking"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Top itens adicionais (modificadores)."""
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
    service = ProductService()
    addons = service.get_top_addons(start_dt, end_dt, store_ids, channel_ids, limit)

    return [
        ProductAddonsRow(
            item_id=addon["item_id"],
            item_name=addon["item_name"],
            qty=addon["qty"],
            revenue=addon["revenue"],
            uses=addon["uses"],
        )
        for addon in addons
    ]


@router.get("/combinations", response_model=list[ProductCombinationRow])
def get_combinations(
    start: Optional[str] = Query(None, description="Data/hora inicial (ISO8601)"),
    end: Optional[str] = Query(None, description="Data/hora final (ISO8601)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    limit: int = Query(20, ge=1, le=100, description="Quantidade de combinações no ranking"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Produtos frequentemente comprados juntos."""
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
    service = ProductService()
    combinations = service.get_combinations(start_dt, end_dt, store_ids, limit)

    return [ProductCombinationRow(**combo) for combo in combinations]
