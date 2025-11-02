"""Utility endpoints router.

This module keeps a few legacy helpers (data range, MV refresh,
top products, etc.) that the frontend still consumes while the new
domain routers are adopted.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import AccessClaims, require_roles
from app.domain.models import (
    DataRangeResult,
    DeliveryP90Row,
    ProductTopRow,
    SalesByHourRow,
    TopProductsRow,
)
from app.services.utils_service import UtilsService

router = APIRouter(prefix="/utils", tags=["utils"])


@router.get("/data-range", response_model=DataRangeResult)
def get_data_range(
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
) -> DataRangeResult:
    """Return the min/max datetime available in the sales table."""
    result = UtilsService.get_data_range()
    if not result:
        raise HTTPException(status_code=404, detail="Nenhum dado encontrado")
    return result  # type: ignore[return-value]


@router.post("/refresh-mv")
def refresh_materialized_views(
    user: AccessClaims = Depends(require_roles("admin")),
) -> dict:
    """Trigger refresh of materialized views used by legacy endpoints."""
    return UtilsService.refresh_materialized_views()


@router.get("/top-products", response_model=List[TopProductsRow])
def get_top_products(
    start: datetime,
    end: datetime,
    limit: int = Query(10, ge=1, le=100, description="Quantidade de produtos"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
) -> List[TopProductsRow]:
    """[LEGACY] Top products by quantity."""
    allowed_store_ids = user.stores or []
    store_ids = [store_id] if store_id else allowed_store_ids or None
    return UtilsService.get_top_products(limit, start, end, store_ids)


@router.get("/product-top", response_model=List[ProductTopRow])
def get_product_top(
    start: datetime,
    end: datetime,
    limit: int = Query(10, ge=1, le=100, description="Quantidade de produtos"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
) -> List[ProductTopRow]:
    """[LEGACY] Top products by revenue."""
    allowed_store_ids = user.stores or []
    store_ids = [store_id] if store_id else allowed_store_ids or None
    return UtilsService.get_product_top(limit, start, end, store_ids)


@router.get("/sales-hour", response_model=List[SalesByHourRow])
def get_sales_hour(
    start: datetime,
    end: datetime,
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
) -> List[SalesByHourRow]:
    """[LEGACY] Sales aggregated by hour of day."""
    allowed_store_ids = user.stores or []
    store_ids = [store_id] if store_id else allowed_store_ids or None
    channel_ids = [channel_id] if channel_id else None
    return UtilsService.get_sales_hour(start, end, store_ids, channel_ids)


@router.get("/delivery-p90", response_model=List[DeliveryP90Row])
def get_delivery_p90(
    start: datetime,
    end: datetime,
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
) -> List[DeliveryP90Row]:
    """[LEGACY] Delivery P90 grouped by store."""
    allowed_store_ids = user.stores or []
    store_ids = [store_id] if store_id else allowed_store_ids or None
    return UtilsService.get_delivery_p90(start, end, store_ids)
