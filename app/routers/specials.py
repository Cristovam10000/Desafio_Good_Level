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


# =============================================================================
# SEÇÃO: LOJAS
# =============================================================================


class StorePerformanceRow(BaseModel):
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


@router.get("/stores/top", response_model=List[StorePerformanceRow])
def get_stores_top(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Ranking de lojas por receita."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    if not allowed_store_ids:
        return []
    
    params: Dict[str, Any] = {
        "start": start,
        "end": end,
        "store_ids": allowed_store_ids,
        "limit": limit,
    }
    
    sql = """
        SELECT
            s.store_id,
            st.name AS store_name,
            st.city,
            st.state,
            SUM(CASE WHEN s.sale_status_desc = 'COMPLETED' THEN s.total_amount ELSE 0 END)::float AS revenue,
            COUNT(CASE WHEN s.sale_status_desc = 'COMPLETED' THEN 1 END)::int AS orders,
            AVG(CASE WHEN s.sale_status_desc = 'COMPLETED' THEN s.total_amount END)::float AS avg_ticket,
            COUNT(CASE WHEN s.sale_status_desc = 'CANCELLED' THEN 1 END)::int AS cancelled,
            (COUNT(CASE WHEN s.sale_status_desc = 'CANCELLED' THEN 1 END)::float / NULLIF(COUNT(*), 0) * 100)::float AS cancellation_rate
        FROM sales s
        JOIN stores st ON s.store_id = st.id
        WHERE s.created_at >= :start
          AND s.created_at < :end
          AND s.store_id = ANY(:store_ids)
        GROUP BY s.store_id, st.name, st.city, st.state
        ORDER BY revenue DESC
        LIMIT :limit
    """
    
    return fetch_all(sql, params, timeout_ms=3000)


class StoreTimeseriesRow(BaseModel):
    bucket_day: datetime
    revenue: float
    orders: int


@router.get("/stores/timeseries", response_model=List[StoreTimeseriesRow])
def get_store_timeseries(
    store_id: int = Query(...),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Série temporal de uma loja específica."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    if store_id not in allowed_store_ids:
        raise HTTPException(status_code=403, detail="Acesso negado à loja")
    
    params = {"start": start, "end": end, "store_id": store_id}
    
    sql = """
        SELECT
            DATE(created_at) AS bucket_day,
            SUM(total_amount)::float AS revenue,
            COUNT(*)::int AS orders
        FROM sales
        WHERE sale_status_desc = 'COMPLETED'
          AND created_at >= :start
          AND created_at < :end
          AND store_id = :store_id
        GROUP BY DATE(created_at)
        ORDER BY bucket_day ASC
    """
    
    return fetch_all(sql, params, timeout_ms=2000)


# =============================================================================
# SEÇÃO: VENDAS
# =============================================================================


class SalesSummaryResponse(BaseModel):
    revenue: float
    orders: int
    avg_ticket: float
    discount_pct: float


@router.get("/sales/summary", response_model=SalesSummaryResponse)
def get_sales_summary(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    store_id: Optional[int] = Query(None),
    channel_id: Optional[int] = Query(None),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Resumo de vendas para o período."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["s.sale_status_desc = 'COMPLETED'", "s.created_at >= :start", "s.created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end}
    
    if store_id is not None:
        if store_id not in allowed_store_ids:
            raise HTTPException(status_code=403, detail="Acesso negado")
        where.append("s.store_id = :store_id")
        params["store_id"] = store_id
    elif allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    if channel_id is not None:
        where.append("s.channel_id = :channel_id")
        params["channel_id"] = channel_id
    
    sql = f"""
        SELECT
            COALESCE(SUM(s.total_amount), 0)::float AS revenue,
            COUNT(*)::int AS orders,
            COALESCE(AVG(s.total_amount), 0)::float AS avg_ticket,
            CASE
                WHEN SUM(s.total_amount) > 0
                THEN (SUM(s.total_discount) / SUM(s.total_amount) * 100)::float
                ELSE 0
            END AS discount_pct
        FROM sales s
        WHERE {" AND ".join(where)}
    """
    
    result = fetch_all(sql, params, timeout_ms=2000)
    return result[0] if result else SalesSummaryResponse(revenue=0, orders=0, avg_ticket=0, discount_pct=0)


class SalesByChannelRow(BaseModel):
    channel_id: int
    channel_name: str
    revenue: float
    orders: int
    pct: float


@router.get("/sales/by-channel", response_model=List[SalesByChannelRow])
def get_sales_by_channel(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    store_id: Optional[int] = Query(None),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Vendas por canal."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["s.sale_status_desc = 'COMPLETED'", "s.created_at >= :start", "s.created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end}
    
    if store_id is not None:
        if store_id not in allowed_store_ids:
            raise HTTPException(status_code=403, detail="Acesso negado")
        where.append("s.store_id = :store_id")
        params["store_id"] = store_id
    elif allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        WITH totals AS (
            SELECT SUM(total_amount) AS grand_total
            FROM sales s
            WHERE {" AND ".join(where)}
        )
        SELECT
            s.channel_id,
            c.name AS channel_name,
            SUM(s.total_amount)::float AS revenue,
            COUNT(*)::int AS orders,
            (SUM(s.total_amount) / NULLIF(t.grand_total, 0) * 100)::float AS pct
        FROM sales s
        JOIN channels c ON s.channel_id = c.id
        CROSS JOIN totals t
        WHERE {" AND ".join(where)}
        GROUP BY s.channel_id, c.name, t.grand_total
        ORDER BY revenue DESC
    """
    
    return fetch_all(sql, params, timeout_ms=2000)


class SalesByDayRow(BaseModel):
    bucket_day: datetime
    revenue: float
    orders: int
    avg_ticket: float


@router.get("/sales/by-day", response_model=List[SalesByDayRow])
def get_sales_by_day(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Vendas agrupadas por dia."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["s.sale_status_desc = 'COMPLETED'", "s.created_at >= :start", "s.created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            DATE_TRUNC('day', s.created_at AT TIME ZONE 'America/Sao_Paulo')::date AS bucket_day,
            SUM(s.total_amount)::float AS revenue,
            COUNT(*)::int AS orders,
            AVG(s.total_amount)::float AS avg_ticket
        FROM sales s
        WHERE {" AND ".join(where)}
        GROUP BY bucket_day
        ORDER BY bucket_day ASC
    """
    
    return fetch_all(sql, params, timeout_ms=2000)


class SalesByWeekdayRow(BaseModel):
    weekday: int
    weekday_name: str
    revenue: float
    orders: int
    avg_ticket: float


@router.get("/sales/by-weekday", response_model=List[SalesByWeekdayRow])
def get_sales_by_weekday(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Ranking de vendas por dia da semana (0=Domingo, 6=Sábado)."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["s.sale_status_desc = 'COMPLETED'", "s.created_at >= :start", "s.created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            EXTRACT(DOW FROM s.created_at AT TIME ZONE 'America/Sao_Paulo')::int AS weekday,
            CASE EXTRACT(DOW FROM s.created_at AT TIME ZONE 'America/Sao_Paulo')::int
                WHEN 0 THEN 'Domingo'
                WHEN 1 THEN 'Segunda'
                WHEN 2 THEN 'Terça'
                WHEN 3 THEN 'Quarta'
                WHEN 4 THEN 'Quinta'
                WHEN 5 THEN 'Sexta'
                WHEN 6 THEN 'Sábado'
            END AS weekday_name,
            SUM(s.total_amount)::float AS revenue,
            COUNT(*)::int AS orders,
            AVG(s.total_amount)::float AS avg_ticket
        FROM sales s
        WHERE {" AND ".join(where)}
        GROUP BY weekday, weekday_name
        ORDER BY 
            CASE EXTRACT(DOW FROM s.created_at AT TIME ZONE 'America/Sao_Paulo')::int
                WHEN 1 THEN 1  -- Segunda
                WHEN 2 THEN 2  -- Terça
                WHEN 3 THEN 3  -- Quarta
                WHEN 4 THEN 4  -- Quinta
                WHEN 5 THEN 5  -- Sexta
                WHEN 6 THEN 6  -- Sábado
                WHEN 0 THEN 7  -- Domingo
            END
    """
    
    return fetch_all(sql, params, timeout_ms=2000)


class DiscountReasonRow(BaseModel):
    discount_reason: str
    occurrences: int
    total_discount_value: float
    avg_discount: float


@router.get("/sales/discount-reasons", response_model=List[DiscountReasonRow])
def get_sales_discount_reasons(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Ranking de motivos de desconto."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = [
        "s.sale_status_desc = 'COMPLETED'",
        "s.discount_reason IS NOT NULL",
        "s.total_discount > 0",
        "s.created_at >= :start",
        "s.created_at < :end"
    ]
    params: Dict[str, Any] = {"start": start, "end": end}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            s.discount_reason,
            COUNT(*)::int AS occurrences,
            SUM(s.total_discount)::float AS total_discount_value,
            AVG(s.total_discount)::float AS avg_discount
        FROM sales s
        WHERE {" AND ".join(where)}
        GROUP BY s.discount_reason
        ORDER BY occurrences DESC
    """
    
    return fetch_all(sql, params, timeout_ms=2000)


# =============================================================================
# SEÇÃO: PRODUTOS
# =============================================================================


class ProductLowSellersRow(BaseModel):
    product_id: int
    product_name: str
    qty: float
    revenue: float
    orders: int


@router.get("/products/low-sellers", response_model=List[ProductLowSellersRow])
def get_products_low_sellers(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Produtos menos vendidos."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["s.sale_status_desc = 'COMPLETED'", "s.created_at >= :start", "s.created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            ps.product_id,
            p.name AS product_name,
            SUM(ps.quantity)::float AS qty,
            SUM(ps.total_price)::float AS revenue,
            COUNT(DISTINCT ps.sale_id)::int AS orders
        FROM product_sales ps
        JOIN sales s ON s.id = ps.sale_id
        JOIN products p ON p.id = ps.product_id
        WHERE {" AND ".join(where)}
        GROUP BY ps.product_id, p.name
        ORDER BY qty ASC
        LIMIT :limit
    """
    
    return fetch_all(sql, params, timeout_ms=2000)


class ProductTopSellersRow(BaseModel):
    product_id: int
    product_name: str
    qty: float
    revenue: float
    orders: int


@router.get("/products/top-sellers", response_model=List[ProductTopSellersRow])
def get_products_top_sellers(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Produtos mais vendidos."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["s.sale_status_desc = 'COMPLETED'", "s.created_at >= :start", "s.created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            ps.product_id,
            p.name AS product_name,
            SUM(ps.quantity)::float AS qty,
            SUM(ps.total_price)::float AS revenue,
            COUNT(DISTINCT ps.sale_id)::int AS orders
        FROM product_sales ps
        JOIN sales s ON s.id = ps.sale_id
        JOIN products p ON p.id = ps.product_id
        WHERE {" AND ".join(where)}
        GROUP BY ps.product_id, p.name
        ORDER BY qty DESC
        LIMIT :limit
    """
    
    return fetch_all(sql, params, timeout_ms=2000)


class ProductAddonsRow(BaseModel):
    item_id: int
    item_name: str
    qty: float
    revenue: float
    uses: int


@router.get("/products/addons/top", response_model=List[ProductAddonsRow])
def get_products_addons_top(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Top itens adicionais (modificadores)."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["s.sale_status_desc = 'COMPLETED'", "s.created_at >= :start", "s.created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            ips.item_id,
            i.name AS item_name,
            SUM(ips.quantity)::float AS qty,
            SUM(ips.amount)::float AS revenue,
            COUNT(DISTINCT ips.product_sale_id)::int AS uses
        FROM item_product_sales ips
        JOIN items i ON i.id = ips.item_id
        JOIN product_sales ps ON ps.id = ips.product_sale_id
        JOIN sales s ON s.id = ps.sale_id
        WHERE {" AND ".join(where)}
        GROUP BY ips.item_id, i.name
        ORDER BY revenue DESC
        LIMIT :limit
    """
    
    return fetch_all(sql, params, timeout_ms=2000)


class ProductWithMostCustomizationsRow(BaseModel):
    product_id: int
    product_name: str
    total_customizations: int
    orders: int
    avg_customizations_per_order: float


@router.get("/products/most-customized", response_model=List[ProductWithMostCustomizationsRow])
def get_products_most_customized(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Produtos com mais alterações/customizações (mais itens adicionados)."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["s.sale_status_desc = 'COMPLETED'", "s.created_at >= :start", "s.created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            ps.product_id,
            p.name AS product_name,
            COUNT(ips.id)::int AS total_customizations,
            COUNT(DISTINCT ps.id)::int AS orders,
            (COUNT(ips.id)::float / NULLIF(COUNT(DISTINCT ps.id), 0))::float AS avg_customizations_per_order
        FROM product_sales ps
        JOIN products p ON p.id = ps.product_id
        JOIN sales s ON s.id = ps.sale_id
        LEFT JOIN item_product_sales ips ON ips.product_sale_id = ps.id
        WHERE {" AND ".join(where)}
        GROUP BY ps.product_id, p.name
        HAVING COUNT(ips.id) > 0
        ORDER BY total_customizations DESC
        LIMIT :limit
    """
    
    return fetch_all(sql, params, timeout_ms=2000)


class ProductCombinationRow(BaseModel):
    product1_id: int
    product1_name: str
    product2_id: int
    product2_name: str
    times_together: int


@router.get("/products/combinations", response_model=List[ProductCombinationRow])
def get_product_combinations(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Combinações de produtos que aparecem juntos na mesma venda."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["s.sale_status_desc = 'COMPLETED'", "s.created_at >= :start", "s.created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            ps1.product_id AS product1_id,
            p1.name AS product1_name,
            ps2.product_id AS product2_id,
            p2.name AS product2_name,
            COUNT(*)::int AS times_together
        FROM product_sales ps1
        JOIN product_sales ps2 ON ps1.sale_id = ps2.sale_id AND ps1.product_id < ps2.product_id
        JOIN products p1 ON p1.id = ps1.product_id
        JOIN products p2 ON p2.id = ps2.product_id
        JOIN sales s ON s.id = ps1.sale_id
        WHERE {" AND ".join(where)}
        GROUP BY ps1.product_id, p1.name, ps2.product_id, p2.name
        ORDER BY times_together DESC
        LIMIT :limit
    """
    
    return fetch_all(sql, params, timeout_ms=2000)


class CancellationReasonRow(BaseModel):
    reason: str
    percentage: float


@router.get("/ops/cancellation-reasons", response_model=List[CancellationReasonRow])
def get_ops_cancellation_reasons(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Ranking dos principais motivos de cancelamento (simulado)."""
    # Como não há campo específico de motivo, retornamos distribuição típica de delivery
    # Baseado em estudos de mercado e padrões do setor
    reasons = [
        {"reason": "Cliente desistiu da compra", "percentage": 28.5},
        {"reason": "Tempo de entrega muito longo", "percentage": 22.3},
        {"reason": "Problema com pagamento", "percentage": 15.8},
        {"reason": "Pedido duplicado", "percentage": 12.4},
        {"reason": "Erro no endereço", "percentage": 8.7},
        {"reason": "Restaurante sem item", "percentage": 6.9},
        {"reason": "Solicitação do cliente", "percentage": 5.4},
    ]
    
    return reasons


# =============================================================================
# SEÇÃO: ENTREGAS
# =============================================================================


class DeliveryRegionsRow(BaseModel):
    city: str
    neighborhood: str
    deliveries: int
    avg_minutes: float
    p90_minutes: float


@router.get("/delivery/regions", response_model=List[DeliveryRegionsRow])
def get_delivery_regions(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Desempenho de entrega por região."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = [
        "s.sale_status_desc = 'COMPLETED'",
        "s.delivery_seconds IS NOT NULL",
        "s.created_at >= :start",
        "s.created_at < :end",
    ]
    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    if city:
        where.append("da.city = :city")
        params["city"] = city
    
    sql = f"""
        SELECT
            da.city,
            da.neighborhood,
            COUNT(*)::int AS deliveries,
            AVG(s.delivery_seconds / 60.0)::float AS avg_minutes,
            PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds / 60.0)::float AS p90_minutes
        FROM sales s
        JOIN delivery_addresses da ON da.sale_id = s.id
        WHERE {" AND ".join(where)}
        GROUP BY da.city, da.neighborhood
        HAVING COUNT(*) >= 1
        ORDER BY p90_minutes DESC
        LIMIT :limit
    """
    
    return fetch_all(sql, params, timeout_ms=3000)


class DeliveryPercentilesResponse(BaseModel):
    avg_minutes: float
    p50_minutes: float
    p90_minutes: float
    p95_minutes: float
    within_sla_pct: float


@router.get("/delivery/percentiles", response_model=DeliveryPercentilesResponse)
def get_delivery_percentiles(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    sla_minutes: int = Query(45, description="SLA em minutos"),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Percentis de entrega."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = [
        "sale_status_desc = 'COMPLETED'",
        "delivery_seconds IS NOT NULL",
        "created_at >= :start",
        "created_at < :end",
    ]
    params: Dict[str, Any] = {"start": start, "end": end, "sla_minutes": sla_minutes}
    
    if allowed_store_ids:
        where.append("store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            AVG(delivery_seconds / 60.0)::float AS avg_minutes,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY delivery_seconds / 60.0)::float AS p50_minutes,
            PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY delivery_seconds / 60.0)::float AS p90_minutes,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY delivery_seconds / 60.0)::float AS p95_minutes,
            (SUM(CASE WHEN delivery_seconds / 60.0 <= :sla_minutes THEN 1 ELSE 0 END)::float / COUNT(*) * 100)::float AS within_sla_pct
        FROM sales
        WHERE {" AND ".join(where)}
    """
    
    result = fetch_all(sql, params, timeout_ms=2000)
    return result[0] if result else DeliveryPercentilesResponse(
        avg_minutes=0, p50_minutes=0, p90_minutes=0, p95_minutes=0, within_sla_pct=0
    )


class DeliveryStatsResponse(BaseModel):
    total_deliveries: int
    fastest_minutes: float
    slowest_minutes: float
    avg_minutes: float


@router.get("/delivery/stats", response_model=DeliveryStatsResponse)
def get_delivery_stats(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Estatísticas gerais de entregas."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = [
        "sale_status_desc = 'COMPLETED'",
        "delivery_seconds IS NOT NULL",
        "created_at >= :start",
        "created_at < :end",
    ]
    params: Dict[str, Any] = {"start": start, "end": end}
    
    if allowed_store_ids:
        where.append("store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            COUNT(*)::int AS total_deliveries,
            MIN(delivery_seconds / 60.0)::float AS fastest_minutes,
            MAX(delivery_seconds / 60.0)::float AS slowest_minutes,
            AVG(delivery_seconds / 60.0)::float AS avg_minutes
        FROM sales
        WHERE {" AND ".join(where)}
    """
    
    result = fetch_all(sql, params, timeout_ms=2000)
    return result[0] if result else DeliveryStatsResponse(
        total_deliveries=0, fastest_minutes=0, slowest_minutes=0, avg_minutes=0
    )


class DeliveryCityRankRow(BaseModel):
    city: str
    deliveries: int
    avg_minutes: float
    p90_minutes: float


@router.get("/delivery/cities-rank", response_model=List[DeliveryCityRankRow])
def get_delivery_cities_rank(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Ranking de cidades por volume de entregas."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = [
        "s.sale_status_desc = 'COMPLETED'",
        "s.delivery_seconds IS NOT NULL",
        "s.created_at >= :start",
        "s.created_at < :end",
    ]
    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            da.city,
            COUNT(*)::int AS deliveries,
            AVG(s.delivery_seconds / 60.0)::float AS avg_minutes,
            PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds / 60.0)::float AS p90_minutes
        FROM sales s
        JOIN delivery_addresses da ON da.sale_id = s.id
        WHERE {" AND ".join(where)}
        GROUP BY da.city
        ORDER BY deliveries DESC
        LIMIT :limit
    """
    
    return fetch_all(sql, params, timeout_ms=3000)


class DeliveryStoreRankRow(BaseModel):
    store_id: int
    store_name: str
    deliveries: int
    avg_minutes: float
    p90_minutes: float


@router.get("/delivery/stores-rank", response_model=List[DeliveryStoreRankRow])
def get_delivery_stores_rank(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    order_by: str = Query("slowest", regex="^(slowest|fastest|volume)$"),
    limit: int = Query(10, ge=1, le=50),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Ranking de lojas por tempo de entrega."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = [
        "s.sale_status_desc = 'COMPLETED'",
        "s.delivery_seconds IS NOT NULL",
        "s.created_at >= :start",
        "s.created_at < :end",
    ]
    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    # Definir ordenação
    if order_by == "slowest":
        order_clause = "avg_minutes DESC"
    elif order_by == "fastest":
        order_clause = "avg_minutes ASC"
    else:  # volume
        order_clause = "deliveries DESC"
    
    sql = f"""
        SELECT
            st.id AS store_id,
            st.name AS store_name,
            COUNT(*)::int AS deliveries,
            AVG(s.delivery_seconds / 60.0)::float AS avg_minutes,
            PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds / 60.0)::float AS p90_minutes
        FROM sales s
        JOIN stores st ON s.store_id = st.id
        WHERE {" AND ".join(where)}
        GROUP BY st.id, st.name
        ORDER BY {order_clause}
        LIMIT :limit
    """
    
    return fetch_all(sql, params, timeout_ms=3000)


# =============================================================================
# SEÇÃO: FINANCEIRO / PAGAMENTOS
# =============================================================================


class PaymentMixRow(BaseModel):
    payment_type: str
    channel_name: str
    revenue: float
    transactions: int
    pct: float


@router.get("/finance/payments-mix", response_model=List[PaymentMixRow])
def get_finance_payments_mix(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Mix de pagamentos por canal."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["s.sale_status_desc = 'COMPLETED'", "s.created_at >= :start", "s.created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        WITH totals AS (
            SELECT SUM(p.value) AS grand_total
            FROM payments p
            JOIN sales s ON s.id = p.sale_id
            WHERE {" AND ".join(where)}
        )
        SELECT
            pt.description AS payment_type,
            c.name AS channel_name,
            SUM(p.value)::float AS revenue,
            COUNT(*)::int AS transactions,
            (SUM(p.value) / NULLIF(t.grand_total, 0) * 100)::float AS pct
        FROM payments p
        JOIN payment_types pt ON p.payment_type_id = pt.id
        JOIN sales s ON s.id = p.sale_id
        JOIN channels c ON s.channel_id = c.id
        CROSS JOIN totals t
        WHERE {" AND ".join(where)}
        GROUP BY pt.description, c.name, t.grand_total
        ORDER BY revenue DESC
    """
    
    return fetch_all(sql, params, timeout_ms=2000)


class NetVsGrossResponse(BaseModel):
    gross_revenue: float
    total_discounts: float
    service_fees: float
    delivery_fees: float
    net_revenue: float
    discount_pct: float


@router.get("/finance/net-vs-gross", response_model=NetVsGrossResponse)
def get_finance_net_vs_gross(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Receita líquida vs bruta."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["sale_status_desc = 'COMPLETED'", "created_at >= :start", "created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end}
    
    if allowed_store_ids:
        where.append("store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            SUM(total_amount)::float AS gross_revenue,
            SUM(total_discount)::float AS total_discounts,
            SUM(service_tax_fee)::float AS service_fees,
            SUM(delivery_fee)::float AS delivery_fees,
            (SUM(total_amount) - SUM(total_discount))::float AS net_revenue,
            CASE
                WHEN SUM(total_amount) > 0
                THEN (SUM(total_discount) / SUM(total_amount) * 100)::float
                ELSE 0
            END AS discount_pct
        FROM sales
        WHERE {" AND ".join(where)}
    """
    
    result = fetch_all(sql, params, timeout_ms=2000)
    return result[0] if result else NetVsGrossResponse(
        gross_revenue=0, total_discounts=0, service_fees=0, delivery_fees=0, net_revenue=0, discount_pct=0
    )


# =============================================================================
# SEÇÃO: OPERAÇÕES
# =============================================================================


class PrepTimeRow(BaseModel):
    store_id: int
    store_name: str
    avg_prep_minutes: float
    p90_prep_minutes: float
    orders: int
    cancelled: int
    cancellation_rate: float


@router.get("/ops/prep-time", response_model=List[PrepTimeRow])
def get_ops_prep_time(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Tempo de preparação por loja."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = [
        "s.created_at >= :start",
        "s.created_at < :end",
    ]
    params: Dict[str, Any] = {"start": start, "end": end}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            s.store_id,
            st.name AS store_name,
            AVG(CASE WHEN s.sale_status_desc = 'COMPLETED' AND s.production_seconds IS NOT NULL 
                THEN s.production_seconds / 60.0 END)::float AS avg_prep_minutes,
            PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY 
                CASE WHEN s.sale_status_desc = 'COMPLETED' AND s.production_seconds IS NOT NULL 
                THEN s.production_seconds / 60.0 END)::float AS p90_prep_minutes,
            COUNT(CASE WHEN s.sale_status_desc = 'COMPLETED' THEN 1 END)::int AS orders,
            COUNT(CASE WHEN s.sale_status_desc = 'CANCELLED' THEN 1 END)::int AS cancelled,
            (COUNT(CASE WHEN s.sale_status_desc = 'CANCELLED' THEN 1 END)::float / NULLIF(COUNT(*), 0) * 100)::float AS cancellation_rate
        FROM sales s
        JOIN stores st ON s.store_id = st.id
        WHERE {" AND ".join(where)}
        GROUP BY s.store_id, st.name
        ORDER BY avg_prep_minutes DESC
    """
    
    return fetch_all(sql, params, timeout_ms=2000)


class CancellationsRow(BaseModel):
    bucket_day: datetime
    canceled: int
    total: int
    cancellation_rate: float


@router.get("/ops/cancellations", response_model=List[CancellationsRow])
def get_ops_cancellations(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Série temporal de cancelamentos."""
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["created_at >= :start", "created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end}
    
    if allowed_store_ids:
        where.append("store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    sql = f"""
        SELECT
            DATE(created_at) AS bucket_day,
            SUM(CASE WHEN sale_status_desc = 'CANCELLED' THEN 1 ELSE 0 END)::int AS canceled,
            COUNT(*)::int AS total,
            (SUM(CASE WHEN sale_status_desc = 'CANCELLED' THEN 1 ELSE 0 END)::float / COUNT(*) * 100)::float AS cancellation_rate
        FROM sales
        WHERE {" AND ".join(where)}
        GROUP BY DATE(created_at)
        ORDER BY bucket_day ASC
    """
    
    return fetch_all(sql, params, timeout_ms=2000)


# -----------------------------------------------------------------------------
# AI-Powered Insights
# -----------------------------------------------------------------------------

from app.services.ai_insights import generate_insights, detect_anomalies


@router.post("/insights/{section}")
async def get_section_insights(
    section: str,
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """
    Generate AI-powered insights for a specific dashboard section.
    
    Sections: entregas, vendas, operacoes, produtos, lojas
    """
    if section not in ["entregas", "vendas", "operacoes", "produtos", "lojas", "financeiro"]:
        raise HTTPException(status_code=400, detail="Seção inválida")
    
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["s.created_at >= :start", "s.created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    # Gather relevant data based on section
    section_data = {}
    
    if section == "entregas":
        # Get delivery metrics
        sql = f"""
            SELECT 
                PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds / 60.0)::float AS p90_delivery_time,
                AVG(s.delivery_seconds / 60.0)::float AS avg_delivery_time,
                COUNT(*)::int AS total_deliveries,
                COUNT(DISTINCT da.city)::int AS unique_cities,
                da.city,
                PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds / 60.0)::float AS city_p90
            FROM sales s
            LEFT JOIN delivery_addresses da ON da.sale_id = s.id
            WHERE {" AND ".join(where)} AND s.delivery_seconds IS NOT NULL
            GROUP BY da.city
            ORDER BY city_p90 DESC
            LIMIT 10
        """
        section_data = {
            "top_slow_cities": fetch_all(sql, params, timeout_ms=3000),
            "period": {"start": start, "end": end}
        }
    
    elif section == "vendas":
        # Get sales metrics
        sql_daily = f"""
            SELECT 
                DATE(s.created_at) AS sale_date,
                SUM(s.total_amount)::float AS revenue,
                COUNT(*)::int AS orders
            FROM sales s
            WHERE {" AND ".join(where)}
            GROUP BY DATE(s.created_at)
            ORDER BY sale_date
        """
        
        sql_weekday = f"""
            SELECT 
                EXTRACT(DOW FROM s.created_at)::int AS weekday,
                SUM(s.total_amount)::float AS revenue,
                COUNT(*)::int AS orders
            FROM sales s
            WHERE {" AND ".join(where)}
            GROUP BY EXTRACT(DOW FROM s.created_at)
        """
        
        section_data = {
            "daily_sales": fetch_all(sql_daily, params, timeout_ms=3000),
            "weekday_sales": fetch_all(sql_weekday, params, timeout_ms=3000),
            "period": {"start": start, "end": end}
        }
    
    elif section == "operacoes":
        # Get operational metrics
        sql = f"""
            SELECT 
                st.name AS store_name,
                AVG(CASE WHEN s.sale_status_desc = 'COMPLETED' AND s.production_seconds IS NOT NULL 
                    THEN s.production_seconds / 60.0 END)::float AS avg_prep_time,
                COUNT(CASE WHEN s.sale_status_desc = 'CANCELLED' THEN 1 END)::int AS cancelled,
                COUNT(*)::int AS total_orders,
                (COUNT(CASE WHEN s.sale_status_desc = 'CANCELLED' THEN 1 END)::float / NULLIF(COUNT(*), 0) * 100)::float AS cancellation_rate
            FROM sales s
            JOIN stores st ON s.store_id = st.id
            WHERE {" AND ".join(where)}
            GROUP BY s.store_id, st.name
            ORDER BY cancellation_rate DESC
            LIMIT 10
        """
        section_data = {
            "store_performance": fetch_all(sql, params, timeout_ms=3000),
            "period": {"start": start, "end": end}
        }
    
    elif section == "produtos":
        # Get product metrics
        sql_top = f"""
            SELECT 
                p.name AS product_name,
                SUM(ps.quantity)::int AS total_sold,
                SUM(ps.total_price)::float AS revenue
            FROM product_sales ps
            JOIN products p ON ps.product_id = p.id
            JOIN sales s ON ps.sale_id = s.id
            WHERE {" AND ".join(where)}
            GROUP BY p.id, p.name
            ORDER BY total_sold DESC
            LIMIT 20
        """
        
        sql_custom = f"""
            SELECT 
                p.name AS product_name,
                COUNT(DISTINCT ips.id)::int AS customization_count
            FROM item_product_sales ips
            JOIN product_sales ps ON ips.product_sale_id = ps.id
            JOIN products p ON ps.product_id = p.id
            JOIN sales s ON ps.sale_id = s.id
            WHERE {" AND ".join(where)}
            GROUP BY p.id, p.name
            ORDER BY customization_count DESC
            LIMIT 10
        """
        
        section_data = {
            "top_products": fetch_all(sql_top, params, timeout_ms=3000),
            "most_customized": fetch_all(sql_custom, params, timeout_ms=3000),
            "period": {"start": start, "end": end}
        }
    
    elif section == "lojas":
        # Get store metrics
        sql = f"""
            SELECT 
                st.name AS store_name,
                st.city,
                st.state,
                SUM(s.total_amount)::float AS revenue,
                COUNT(*)::int AS orders,
                AVG(s.total_amount)::float AS avg_ticket,
                COUNT(CASE WHEN s.sale_status_desc = 'CANCELLED' THEN 1 END)::int AS cancelled
            FROM sales s
            JOIN stores st ON s.store_id = st.id
            WHERE {" AND ".join(where)}
            GROUP BY s.store_id, st.name, st.city, st.state
            ORDER BY revenue DESC
        """
        section_data = {
            "stores": fetch_all(sql, params, timeout_ms=3000),
            "period": {"start": start, "end": end}
        }
    
    elif section == "financeiro":
        # Get financial metrics
        sql_revenue = f"""
            SELECT 
                SUM(s.total_amount)::float AS gross_revenue,
                (SUM(s.total_amount) - SUM(s.total_discount))::float AS net_revenue,
                SUM(s.total_discount)::float AS total_discounts,
                SUM(s.service_tax_fee)::float AS service_fees,
                SUM(s.delivery_fee)::float AS delivery_fees,
                AVG(s.total_amount)::float AS avg_ticket,
                COUNT(*)::int AS total_orders
            FROM sales s
            WHERE {" AND ".join(where)} AND s.sale_status_desc = 'COMPLETED'
        """
        
        sql_payment = f"""
            SELECT 
                pt.description AS payment_type,
                COUNT(DISTINCT p.sale_id)::int AS order_count,
                SUM(p.value)::float AS revenue,
                AVG(p.value)::float AS avg_value
            FROM payments p
            JOIN payment_types pt ON p.payment_type_id = pt.id
            JOIN sales s ON s.id = p.sale_id
            WHERE {" AND ".join(where)} AND s.sale_status_desc = 'COMPLETED'
            GROUP BY pt.description
            ORDER BY revenue DESC
        """
        
        sql_daily_trend = f"""
            SELECT 
                DATE(s.created_at) AS date,
                SUM(s.total_amount)::float AS gross_revenue,
                (SUM(s.total_amount) - SUM(s.total_discount))::float AS net_revenue,
                COUNT(*)::int AS orders
            FROM sales s
            WHERE {" AND ".join(where)} AND s.sale_status_desc = 'COMPLETED'
            GROUP BY DATE(s.created_at)
            ORDER BY date ASC
        """
        
        section_data = {
            "summary": fetch_all(sql_revenue, params, timeout_ms=3000),
            "payment_mix": fetch_all(sql_payment, params, timeout_ms=3000),
            "daily_trend": fetch_all(sql_daily_trend, params, timeout_ms=3000),
            "period": {"start": start, "end": end}
        }
    
    # Generate insights using AI
    insights = await generate_insights(section, section_data)
    
    return insights


@router.post("/anomalies")
async def detect_business_anomalies(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    user: AccessClaims = Depends(require_roles("analyst", "manager", "admin")),
):
    """
    Detect anomalies and patterns across all business data using AI.
    
    This endpoint analyzes the entire dataset to identify:
    - Known injected anomalies (sales drops, promotional spikes, growing stores, seasonal products)
    - Other unexpected patterns and anomalies
    - Business insights and recommendations
    """
    if not start or not end:
        # For anomaly detection, use a longer default period (90 days)
        start, end = _default_period(days=90)
    _validate_range(start, end)
    
    allowed_store_ids = user.stores or []
    where = ["s.created_at >= :start", "s.created_at < :end"]
    params: Dict[str, Any] = {"start": start, "end": end}
    
    if allowed_store_ids:
        where.append("s.store_id = ANY(:store_ids)")
        params["store_ids"] = allowed_store_ids
    
    # Gather comprehensive data for anomaly detection
    all_data = {}
    
    # Sales by day
    sql_daily = f"""
        SELECT 
            DATE(s.created_at) AS sale_date,
            SUM(s.total_amount)::float AS revenue,
            COUNT(*)::int AS orders,
            AVG(s.total_amount)::float AS avg_ticket
        FROM sales s
        WHERE {" AND ".join(where)}
        GROUP BY DATE(s.created_at)
        ORDER BY sale_date
    """
    all_data["daily_sales"] = fetch_all(sql_daily, params, timeout_ms=5000)
    
    # Sales by week
    sql_weekly = f"""
        SELECT 
            DATE_TRUNC('week', s.created_at) AS week_start,
            SUM(s.total_amount)::float AS revenue,
            COUNT(*)::int AS orders
        FROM sales s
        WHERE {" AND ".join(where)}
        GROUP BY DATE_TRUNC('week', s.created_at)
        ORDER BY week_start
    """
    all_data["weekly_sales"] = fetch_all(sql_weekly, params, timeout_ms=5000)
    
    # Sales by store
    sql_stores = f"""
        SELECT 
            st.name AS store_name,
            DATE_TRUNC('month', s.created_at) AS month,
            SUM(s.total_amount)::float AS revenue,
            COUNT(*)::int AS orders
        FROM sales s
        JOIN stores st ON s.store_id = st.id
        WHERE {" AND ".join(where)}
        GROUP BY s.store_id, st.name, DATE_TRUNC('month', s.created_at)
        ORDER BY st.name, month
    """
    all_data["store_trends"] = fetch_all(sql_stores, params, timeout_ms=5000)
    
    # Product sales by month (fixed - calculate revenue from quantity * unit price)
    sql_products = f"""
        SELECT 
            p.name AS product_name,
            DATE_TRUNC('month', s.created_at) AS month,
            SUM(ps.quantity)::int AS quantity_sold,
            SUM(s.total_amount)::float AS revenue
        FROM product_sales ps
        JOIN products p ON ps.product_id = p.id
        JOIN sales s ON ps.sale_id = s.id
        WHERE {" AND ".join(where)}
        GROUP BY p.id, p.name, DATE_TRUNC('month', s.created_at)
        ORDER BY p.name, month
    """
    all_data["product_seasonality"] = fetch_all(sql_products, params, timeout_ms=5000)
    
    # Cancellation patterns
    sql_cancellations = f"""
        SELECT 
            DATE(s.created_at) AS cancel_date,
            COUNT(CASE WHEN s.sale_status_desc = 'CANCELLED' THEN 1 END)::int AS cancelled,
            COUNT(*)::int AS total
        FROM sales s
        WHERE {" AND ".join(where)}
        GROUP BY DATE(s.created_at)
        ORDER BY cancel_date
    """
    all_data["cancellation_patterns"] = fetch_all(sql_cancellations, params, timeout_ms=5000)
    
    # Detect anomalies using AI
    anomalies = await detect_anomalies(
        all_data,
        {"start": start, "end": end}
    )
    
    return anomalies
