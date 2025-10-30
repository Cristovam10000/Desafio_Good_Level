from datetime import datetime, timedelta, timezone
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.infra.db import fetch_all
from datetime import datetime, timedelta

# reuse: Depends, Query, Optional, List já vêm de cima
from app.infra.db import fetch_all, refresh_materialized_views
from sqlalchemy.exc import ProgrammingError



router = APIRouter(
    prefix="/specials",
    tags=["specials"],
)


class TopProductOut(BaseModel):
    product_id: int
    product_name: str
    qty: float


def _parse_iso8601(value: str) -> datetime:
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Data/hora invalida: {value}") from exc
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get("/top-products", response_model=List[TopProductOut])
def top_products(
    limit: int = Query(10, ge=1, le=100, description="Quantidade de produtos no ranking"),
    start: Optional[str] = Query(None, description="Data/hora inicial (inclusive)"),
    end: Optional[str] = Query(None, description="Data/hora final (exclusivo)"),
    offset: int = Query(0, ge=0, description="Offset para paginacao"),
    store_id: Optional[int] = Query(None, description="Filtrar por loja especifica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal especifico"),
    # user: AccessClaims = Depends(require_roles("analyst", "manager", "admin")),
):
    
    where_clauses = ["s.sale_status_desc = 'COMPLETED'"]
    params = {"limit": limit, "offset": offset}

    end_dt = _parse_iso8601(end) if end else datetime.now(timezone.utc)
    start_dt = _parse_iso8601(start) if start else end_dt - timedelta(days=30)

    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="start deve ser anterior a end.")

    where_clauses.append("s.created_at >= :start AND s.created_at < :end")
    params["start"] = start_dt.isoformat()
    params["end"] = end_dt.isoformat()

    if store_id is not None:
        where_clauses.append("s.store_id = :store_id")
        params["store_id"] = store_id

    if channel_id is not None:
        where_clauses.append("s.channel_id = :channel_id")
        params["channel_id"] = channel_id

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

    rows = fetch_all(sql, params, timeout_ms=1500)
    return rows

# --- acrescente estes imports no topo, se ainda não tiver:

# -----------------------------
# Helpers de período (defaults)
# -----------------------------

def _default_period(days: int = 30) -> tuple[str, str]:
    """
    Se o cliente não enviar período, usamos últimos N dias.
    Retornamos ISO str (YYYY-MM-DD HH:MM:SS) para parametrizar no SQL.
    """
    now = datetime.now()
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(minute=0, second=0, microsecond=0)  # fecha na hora atual
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")

def _validate_range(start: str, end: str) -> None:
    try:
        ds = datetime.fromisoformat(start.replace("Z", ""))
        de = datetime.fromisoformat(end.replace("Z", ""))
    except Exception:
        raise HTTPException(status_code=400, detail="Datas inválidas. Use ISO 8601 (ex.: 2024-06-01 ou 2024-06-01T00:00:00)")
    if ds >= de:
        raise HTTPException(status_code=400, detail="'start' deve ser menor que 'end'.")

# ---------------------------------------
# 1) Série temporal (mv_sales_hour)
# ---------------------------------------

class SalesHourRow(BaseModel):
    bucket_hour: datetime
    store_id: int | None = None
    channel_id: int | None = None
    orders: int | None = None
    revenue: float | None = None
    amount_items: float | None = None
    discounts: float | None = None
    service_tax_fee: float | None = None
    avg_ticket: float | None = None  # calculado no SELECT

@router.get("/sales-hour", response_model=List[SalesHourRow], tags=["specials"])
def sales_hour(
    # período
    start: Optional[str] = Query(None, description="ISO8601 início (default: agora-30d)"),
    end: Optional[str] = Query(None, description="ISO8601 fim (default: agora)"),
    # filtros
    store_id: Optional[int] = Query(None, description="Filtrar por loja"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal"),
    # outros
    limit: int = Query(10000, ge=1, le=100000),
):
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)

    where = ["bucket_hour >= :start", "bucket_hour < :end"]
    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit}

    if store_id is not None:
        where.append("store_id = :store_id")
        params["store_id"] = store_id
    if channel_id is not None:
        where.append("channel_id = :channel_id")
        params["channel_id"] = channel_id

    sql = f"""
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
    # Tenta MV; se não existir, cai para fallback em tabelas brutas
    try:
        rows = fetch_all(sql, params, timeout_ms=1500)
        return rows
    except ProgrammingError as e:
        # UndefinedTable indica que a MV ainda não foi criada
        if "UndefinedTable" not in str(e):
            raise

    # Fallback: agrega direto de sales por hora (pode ser um pouco mais pesado)
    where_raw = [
        "s.sale_status_desc = 'COMPLETED'",
        "s.created_at >= :start",
        "s.created_at < :end",
    ]
    if store_id is not None:
        where_raw.append("s.store_id = :store_id")
    if channel_id is not None:
        where_raw.append("s.channel_id = :channel_id")

    sql_fallback = f"""
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

    return fetch_all(sql_fallback, params, timeout_ms=3000)

# ---------------------------------------
# 2) Ranking de produtos (mv_product_day)
# ---------------------------------------

class ProductTopRow(BaseModel):
    product_id: int
    product_name: str
    qty: float
    revenue: float
    orders: int

@router.get("/product-top", response_model=List[ProductTopRow], tags=["specials"])
def product_top(
    start: Optional[str] = Query(None, description="ISO8601 início (default: agora-30d)"),
    end: Optional[str] = Query(None, description="ISO8601 fim (default: agora)"),
    store_id: Optional[int] = Query(None, description="(Opcional) restringir a uma loja — se você tiver criado mv por loja"),
    limit: int = Query(50, ge=1, le=500),
    order_by: str = Query("revenue", pattern="^(revenue|qty|orders)$", description="Campo de ordenação"),
    direction: str = Query("DESC", pattern="^(ASC|DESC)$"),
):
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)

    # A mv_product_day que criamos é por dia×produto (sem loja).
    # Se quiser ranking por loja, crie outra MV com store_id.
    where = ["bucket_day >= CAST(:start AS date)", "bucket_day < CAST(:end AS date)"]
    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit}

    # Caso você tenha evoluído a MV para ter store_id, destrave aqui:
    if store_id is not None:
        where.append("store_id = :store_id")
        params["store_id"] = store_id

    # Agregamos em cima da MV (somando o período) e ordenamos
    sql = f"""
    SELECT
        product_id,
        MAX(product_name) AS product_name,
        SUM(qty)::float   AS qty,
        SUM(revenue)::float AS revenue,
        SUM(orders)::int  AS orders
    FROM mv_product_day
    WHERE {" AND ".join(where)}
    GROUP BY product_id
    ORDER BY {order_by} {direction}
    LIMIT :limit
    """
    rows = fetch_all(sql, params, timeout_ms=1500)
    return rows

# ---------------------------------------
# 3) Delivery p90 por bairro (mv_delivery_p90)
# ---------------------------------------

class DeliveryP90Row(BaseModel):
    bucket_day: datetime
    city: str
    neighborhood: str
    deliveries: int
    avg_delivery_minutes: float
    p90_delivery_minutes: float

@router.get("/delivery-p90", response_model=List[DeliveryP90Row], tags=["specials"])
def delivery_p90(
    start: Optional[str] = Query(None, description="ISO8601 início (default: agora-30d)"),
    end: Optional[str] = Query(None, description="ISO8601 fim (default: agora)"),
    city: Optional[str] = Query(None, description="Filtrar por cidade"),
    min_deliveries: int = Query(20, ge=1, le=1000, description="Mínimo de entregas no período p/ exibir linha"),
    limit: int = Query(200, ge=1, le=5000),
):
    if not start or not end:
        start, end = _default_period(days=30)
    _validate_range(start, end)

    where = ["bucket_day >= CAST(:start AS date)", "bucket_day < CAST(:end AS date)"]
    params: Dict[str, Any] = {"start": start, "end": end, "limit": limit, "min_deliveries": min_deliveries}

    if city:
        where.append("city = :city")
        params["city"] = city

    # Agregamos no período e filtramos por volume mínimo
    sql = f"""
    SELECT
      MAX(bucket_day) AS bucket_day,  -- opcional: última data no range
      city,
      neighborhood,
      SUM(deliveries)::int                      AS deliveries,
      AVG(avg_delivery_minutes)::float          AS avg_delivery_minutes,
      PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY p90_delivery_minutes)::float AS p90_delivery_minutes
    FROM mv_delivery_p90
    WHERE {" AND ".join(where)}
    GROUP BY city, neighborhood
    HAVING SUM(deliveries) >= :min_deliveries
    ORDER BY p90_delivery_minutes DESC
    LIMIT :limit
    """
    rows = fetch_all(sql, params, timeout_ms=2000)
    return rows

# ---------------------------------------
# 4) (Opcional) Refresh manual de MVs
# ---------------------------------------

class RefreshOut(BaseModel):
    ok: bool = True
    refreshed: List[str]

@router.post("/refresh-mv", response_model=RefreshOut, tags=["specials"])
def refresh_mv(
    which: Optional[List[str]] = Query(None, description="Lista de MVs para refresh. Vazio = todas."),
    # user: AccessClaims = Depends(require_roles("admin")),  # habilite se quiser proteger
):
    known = {
        "mv_sales_hour",
        "mv_product_day",
        "mv_delivery_p90",
    }
    todo = known if not which else set(which)
    invalid = todo - known
    if invalid:
        raise HTTPException(status_code=400, detail=f"MVs inválidas: {sorted(invalid)}")

    for name in sorted(todo):
        # CONCURRENTLY não pode rodar em transação; nossa helper já cuida
        refresh_materialized_views(name, concurrently=True)

    return RefreshOut(refreshed=sorted(todo))
