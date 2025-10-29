from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.infra.db import get_session, fetch_all
# from app.core.security import require_roles, AccessClaims

router = APIRouter(
    prefix="/specials",
    tags=["specials"]  
)


class TopProductOut(BaseModel):
    product_id: int
    product_name: str
    qty: float  


@router.get("/top-products", response_model=List[TopProductOut])
def top_products(
    # Limite de linhas retornadas (default 10)
    limit: int = Query(10, ge=1, le=100, description="Quantidade de produtos no ranking"),
    # Filtros de período (ISO 8601: '2024-01-01' ou '2024-01-01T00:00:00')
    start: Optional[str] = Query(None, description="Data/hora inicial (inclusive)"),
    end: Optional[str] = Query(None, description="Data/hora final (exclusivo)"),
    # Filtros opcionais de loja e canal
    store_id: Optional[int] = Query(None, description="Filtrar por loja específica"),
    channel_id: Optional[int] = Query(None, description="Filtrar por canal específico"),
    # user: AccessClaims = Depends(require_roles("analyst", "manager", "admin")),  # habilite se quiser proteger
    db: Session = Depends(get_session),
):

    # Construímos o WHERE de forma segura, acumulando cláusulas e params
    where_clauses = ["s.sale_status_desc = 'COMPLETED'"]
    params = {"limit": limit}

    if start and end:
        where_clauses.append("s.created_at >= :start AND s.created_at < :end")
        params["start"] = start
        params["end"] = end

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
    ORDER BY qty DESC
    LIMIT :limit
    """


    rows = fetch_all(sql, params)
    return rows
