from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.infra.db import fetch_all
# from app.core.security import require_roles, AccessClaims

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
    """
    Retorna o ranking de produtos por quantidade vendida.

    Observacoes:
    - SQL parametrizado para evitar injection.
    - Periodo padrao: ultimos 30 dias ate agora (UTC) quando nao informado.
    - Suporta filtros opcionais de loja/canal e paginacao offset/limit.
    - Aplica timeout defensivo de 1500 ms para proteger o worker.
    """
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
