"""Endpoints m├®tricos espec├¡ficos (materialized views + fallback em tabelas)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import ProgrammingError

from app.core.security import AccessClaims, require_roles
from app.infra.db import fetch_all, refresh_materialized_views


router = APIRouter(prefix="/specials", tags=["specials"])


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _parse_iso8601(value: str) -> datetime:
    """Parse ISO8601 strings (aceitando sufixo Z) e normaliza para UTC."""
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Data/hora inv├ílida: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _default_period(days: int = 30) -> tuple[str, str]:
    """Retorna intervalo padr├úo (├║ltimos *days*) em string ISO datetime."""
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat(), now.isoformat()


def _validate_range(start: str, end: str) -> None:
    start_dt = _parse_iso8601(start)
    end_dt = _parse_iso8601(end)
    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="'start' deve ser menor que 'end'.")


def _parse_channel_ids(raw: Optional[str], single: Optional[int] = None) -> Optional[list[int]]:
    ids: list[int] = []
    if raw:
        for chunk in raw.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                ids.append(int(chunk))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="channel_ids deve conter apenas números separados por vírgula.") from exc
    if single is not None:
        if single not in ids:
            ids.append(single)
    return ids or None


# -----------------------------------------------------------------------------
# Top products
# -----------------------------------------------------------------------------


class TopProductOut(BaseModel):
    product_id: int
    product_name: str
    qty: float


@router.get("/top-products", response_model=List[TopProductOut])
def top_products(
    limit: int = Query(10, ge=1, le=100, description="Quantidade de produtos no ranking"),
    start: Optional[str] = Query(None, description="Data/hora inicial (inclusive)"),
    end: Optional[str] = Query(None, description="Data/hora final (exclusivo)"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    channel_ids: Optional[str] = Query(None, description="Lista de canais separados por vírgula"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """
    Ranking simples de produtos vendidos diretamente das tabelas transacionais.
    Mantido como fallback leve (sem depender de MV específica).
    Filtra automaticamente pelas lojas do usuário autenticado.
    """
    where_clauses = ["s.sale_status_desc = 'COMPLETED'"]
    params: Dict[str, Any] = {"limit": limit, "offset": offset}

    end_dt = _parse_iso8601(end) if end else datetime.now(timezone.utc)
    start_dt = _parse_iso8601(start) if start else end_dt - timedelta(days=30)

    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="'start' deve ser anterior a 'end'.")

    where_clauses.append("s.created_at >= :start AND s.created_at < :end")
    params["start"] = start_dt.isoformat()
    params["end"] = end_dt.isoformat()

    # FILTRO POR LOJAS DO USUÁRIO (OBRIGATÓRIO)
    allowed_store_ids = user.stores or []
    if store_id is not None:
        if store_id not in allowed_store_ids:
            raise HTTPException(status_code=403, detail="Acesso negado à loja especificada")
        where_clauses.append("s.store_id = :store_id")
        params["store_id"] = store_id
    elif allowed_store_ids:
        where_clauses.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    channel_ids_list = _parse_channel_ids(channel_ids, channel_id)
    if channel_ids_list:
        where_clauses.append("s.channel_id = ANY(:channel_ids)")
        params["channel_ids"] = channel_ids_list

    sql = f"""
        SELECT
            ps.product_id,
            p.name AS product_name,
            SUM(ps.quantity)::float AS qty
        FROM product_sales ps
        JOIN sales s      ON s.id = ps.sale_id
        JOIN products p   ON p.id = ps.product_id
        WHERE {" AND ".join(where_clauses)}
        GROUP BY ps.product_id, p.name
        ORDER BY qty DESC, ps.product_id ASC
        LIMIT :limit OFFSET :offset
    """

    return fetch_all(sql, params, timeout_ms=1500)


# -----------------------------------------------------------------------------
# Sales por hora (MV ou fallback)
# -----------------------------------------------------------------------------


class SalesHourRow(BaseModel):
    bucket_hour: datetime
    store_id: Optional[int] = None
    channel_id: Optional[int] = None
    orders: Optional[int] = None
    revenue: Optional[float] = None
    amount_items: Optional[float] = None
    discounts: Optional[float] = None
    service_tax_fee: Optional[float] = None
    avg_ticket: Optional[float] = None


@router.get("/sales-hour", response_model=List[SalesHourRow])
def sales_hour(
    start: Optional[str] = Query(None, description="ISO8601 início (default: agora-30d)"),
    end: Optional[str] = Query(None, description="ISO8601 fim (default: agora)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal"),
    channel_ids: Optional[str] = Query(None, description="Lista de canais separados por vírgula"),
    limit: int = Query(10000, ge=1, le=100000),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Consulta `mv_sales_hour`; se ausente, agrega diretamente de `sales`. Filtra pelas lojas do usuário."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)

    where = ["bucket_hour >= :start", "bucket_hour < :end"]
    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit}
    
    # FILTRO POR LOJAS DO USUÁRIO (OBRIGATÓRIO)
    allowed_store_ids = user.stores or []
    if store_id is not None:
        if store_id not in allowed_store_ids:
            raise HTTPException(status_code=403, detail="Acesso negado à loja especificada")
        where.append("store_id = :store_id")
        params["store_id"] = store_id
    elif allowed_store_ids:
        where.append("store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    channel_ids_list = _parse_channel_ids(channel_ids, channel_id)
    if channel_ids_list:
        where.append("channel_id = ANY(:channel_ids)")
        params["channel_ids"] = channel_ids_list

    sql_mv = f"""
        SELECT
          bucket_hour,
          store_id,
          channel_id,
          orders,
          revenue,
          amount_items,
          discounts,
          service_tax_fee,
          CASE WHEN orders > 0 THEN revenue / orders ELSE NULL END AS avg_ticket
        FROM mv_sales_hour
        WHERE {" AND ".join(where)}
        ORDER BY bucket_hour ASC
        LIMIT :limit
    """
    try:
        return fetch_all(sql_mv, params, timeout_ms=1500)
    except ProgrammingError as exc:
        if "UndefinedTable" not in str(exc):
            raise

    where_raw = [
        "s.sale_status_desc = 'COMPLETED'",
        "s.created_at >= :start",
        "s.created_at < :end",
    ]
    if store_id is not None:
        where_raw.append("s.store_id = :store_id")
    elif allowed_store_ids:
        where_raw.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    if channel_ids_list:
        where_raw.append("s.channel_id = ANY(:channel_ids)")

    sql_raw = f"""
        SELECT
          date_trunc('hour', s.created_at) AS bucket_hour,
          s.store_id,
          s.channel_id,
          COUNT(*)::int AS orders,
          COALESCE(SUM(s.total_amount), 0)::float AS revenue,
          COALESCE(SUM(s.total_amount_items), 0)::float AS amount_items,
          COALESCE(SUM(s.total_discount), 0)::float AS discounts,
          COALESCE(SUM(s.service_tax_fee), 0)::float AS service_tax_fee,
          CASE WHEN COUNT(*) > 0 THEN (SUM(s.total_amount) / COUNT(*))::float ELSE NULL END AS avg_ticket
        FROM sales s
        WHERE {" AND ".join(where_raw)}
        GROUP BY 1,2,3
        ORDER BY 1 ASC
        LIMIT :limit
    """
    return fetch_all(sql_raw, params, timeout_ms=3000)


# -----------------------------------------------------------------------------
# Ranking de produtos (MV agregada)
# -----------------------------------------------------------------------------


class ProductTopRow(BaseModel):
    product_id: int
    product_name: str
    qty: float
    revenue: float
    orders: int


@router.get("/product-top", response_model=List[ProductTopRow])
def product_top(
    start: Optional[str] = Query(None, description="ISO8601 início (default: agora-30d)"),
    end: Optional[str] = Query(None, description="ISO8601 fim (default: agora)"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja"),
    limit: int = Query(50, ge=1, le=500),
    order_by: str = Query("revenue", pattern="^(revenue|qty|orders)$", description="Campo de ordenação"),
    direction: str = Query("DESC", pattern="^(ASC|DESC)$"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Ranking de produtos usando MV ou fallback. Filtra pelas lojas do usuário."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)

    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit}
    
    # FILTRO POR LOJAS DO USUÁRIO (OBRIGATÓRIO)
    allowed_store_ids = user.stores or []
    if store_id is not None:
        if store_id not in allowed_store_ids:
            raise HTTPException(status_code=403, detail="Acesso negado à loja especificada")
    
    # MV não tem store_id, então sempre usa fallback quando precisa filtrar por loja
    where_raw = [
        "s.sale_status_desc = 'COMPLETED'",
        "DATE(s.created_at) >= CAST(:start AS date)",
        "DATE(s.created_at) < CAST(:end AS date)",
    ]
    if store_id is not None:
        where_raw.append("s.store_id = :store_id")
        params["store_id"] = store_id
    elif allowed_store_ids:
        where_raw.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql_fallback = f"""
        SELECT
            ps.product_id,
            MAX(p.name) AS product_name,
            SUM(ps.quantity)::float AS qty,
            SUM(s.total_amount)::float AS revenue,
            COUNT(DISTINCT s.id)::int AS orders
        FROM product_sales ps
        JOIN sales s ON s.id = ps.sale_id
        JOIN products p ON p.id = ps.product_id
        WHERE {" AND ".join(where_raw)}
        GROUP BY ps.product_id
        ORDER BY {order_by} {direction}
        LIMIT :limit
    """
    
    return fetch_all(sql_fallback, params, timeout_ms=3000)
    
    sql_fallback = f"""
        SELECT
            ps.product_id,
            MAX(p.name) AS product_name,
            SUM(ps.quantity)::float AS qty,
            SUM(s.total_amount)::float AS revenue,
            COUNT(DISTINCT s.id)::int AS orders
        FROM product_sales ps
        JOIN sales s ON s.id = ps.sale_id
        JOIN products p ON p.id = ps.product_id
        WHERE {" AND ".join(where_raw)}
        GROUP BY ps.product_id
        ORDER BY {order_by} {direction}
        LIMIT :limit
    """
    
    return fetch_all(sql_fallback, params, timeout_ms=3000)


# -----------------------------------------------------------------------------
# Delivery P90
# -----------------------------------------------------------------------------


class DeliveryP90Row(BaseModel):
    bucket_day: datetime
    city: str
    neighborhood: str
    deliveries: int
    avg_delivery_minutes: float
    p90_delivery_minutes: float


@router.get("/delivery-p90", response_model=List[DeliveryP90Row])
def delivery_p90(
    start: Optional[str] = Query(None, description="ISO8601 início (default: agora-30d)"),
    end: Optional[str] = Query(None, description="ISO8601 fim (default: agora)"),
    city: Optional[str] = Query(None, description="Filtrar por cidade"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja"),
    min_deliveries: int = Query(20, ge=1, le=1000, description="Mínimo de entregas p/ exibir linha"),
    limit: int = Query(200, ge=1, le=5000),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Estatísticas de entrega P90. Filtra pelas lojas do usuário."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)

    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit, "min_deliveries": min_deliveries}
    
    # FILTRO POR LOJAS DO USUÁRIO (OBRIGATÓRIO)
    allowed_store_ids = user.stores or []
    if store_id is not None:
        if store_id not in allowed_store_ids:
            raise HTTPException(status_code=403, detail="Acesso negado à loja especificada")
    
    # MV não tem store_id, então sempre usa fallback quando precisa filtrar por loja
    where_raw = [
        "s.sale_status_desc = 'COMPLETED'",
        "s.delivery_seconds IS NOT NULL",
        "DATE(s.created_at) >= CAST(:start AS date)",
        "DATE(s.created_at) < CAST(:end AS date)",
    ]
    if store_id is not None:
        where_raw.append("s.store_id = :store_id")
        params["store_id"] = store_id
    elif allowed_store_ids:
        where_raw.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    if city:
        where_raw.append("da.city = :city")
        params["city"] = city
    
    sql_fallback = f"""
        SELECT
          DATE(s.created_at) AS bucket_day,
          da.city,
          da.neighborhood,
          COUNT(*)::int AS deliveries,
          AVG((s.delivery_seconds/60.0))::float AS avg_delivery_minutes,
          PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY (s.delivery_seconds/60.0))::float AS p90_delivery_minutes
        FROM sales s
        JOIN delivery_addresses da ON da.sale_id = s.id
        WHERE {" AND ".join(where_raw)}
        GROUP BY da.city, da.neighborhood, DATE(s.created_at)
        HAVING COUNT(*) >= :min_deliveries
        ORDER BY p90_delivery_minutes DESC
        LIMIT :limit
    """
    
    return fetch_all(sql_fallback, params, timeout_ms=3000)


# -----------------------------------------------------------------------------
# Channels metadata
# -----------------------------------------------------------------------------


class ChannelRow(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    type: Optional[str] = None


@router.get("/channels", response_model=List[ChannelRow])
def list_channels():
    sql = """
        SELECT
          id,
          name,
          description,
          type
        FROM channels
        ORDER BY name ASC
    """
    return fetch_all(sql, timeout_ms=1000)


# -----------------------------------------------------------------------------
# Stores metadata
# -----------------------------------------------------------------------------


class StoreRow(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    is_active: bool


@router.get("/stores", response_model=List[StoreRow])
def list_stores(
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Lista as lojas às quais o usuário tem acesso."""
    allowed_store_ids = user.stores or []
    
    if not allowed_store_ids:
        return []
    
    sql = """
        SELECT
          id,
          name,
          city,
          state,
          is_active
        FROM stores
        WHERE id = ANY(:store_ids)
        ORDER BY id ASC
    """
    return fetch_all(sql, {"store_ids": allowed_store_ids}, timeout_ms=1000)


# -----------------------------------------------------------------------------
# Data Range Endpoint
# -----------------------------------------------------------------------------


class DataRangeResponse(BaseModel):
    """Response model for data range endpoint."""
    ok: bool = True
    start_date: str
    end_date: str


@router.get("/data-range", response_model=DataRangeResponse)
def get_data_range():
    """
    Retorna o período completo de dados disponível no sistema.
    Consulta as datas mínima e máxima da tabela de vendas.
    """
    sql = """
        SELECT 
            MIN(created_at)::date AS start_date,
            MAX(created_at)::date AS end_date
        FROM sales
    """
    result = fetch_all(sql, timeout_ms=2000)
    
    if not result or not result[0]:
        raise HTTPException(
            status_code=404,
            detail="Nenhum dado encontrado no sistema"
        )
    
    row = result[0]
    return DataRangeResponse(
        start_date=str(row["start_date"]),
        end_date=str(row["end_date"])
    )


# -----------------------------------------------------------------------------
# Refresh manual das materialized views
# -----------------------------------------------------------------------------


class RefreshOut(BaseModel):
    ok: bool = True
    refreshed: List[str]


@router.post("/refresh-mv", response_model=RefreshOut)
def refresh_mv(
    which: Optional[List[str]] = Query(None, description="Lista de MVs para refresh. Vazio = todas."),
):
    """Permite for├ºar o REFRESH (concurrent) das MVs utilizadas pelos endpoints."""
    known = {"mv_sales_hour", "mv_product_day", "mv_delivery_p90"}
    requested = known if not which else set(which)
    invalid = requested - known
    if invalid:
        raise HTTPException(status_code=400, detail=f"MVs inv├ílidas: {sorted(invalid)}")

    for name in sorted(requested):
        refresh_materialized_views(name, concurrently=True)

    return RefreshOut(refreshed=sorted(requested))
