"""
Repositório de lojas.
Centraliza todo acesso a dados relacionados a lojas.
"""

from typing import Optional, Sequence

from app.infra.db import fetch_all
from app.domain.filters import DataFilters
from app.domain.models import StoreMetrics


class StoreRepository:
    """
    Repositório para acesso a dados de lojas.
    Encapsula toda lógica SQL relacionada a lojas.
    """
    
    @staticmethod
    def get_all(store_ids: Optional[Sequence[int]] = None) -> list[dict]:
        """
        Obtém lista de todas as lojas.
        
        Returns:
            Lista de lojas com id e nome
        """
        params: dict[str, list[int]] = {}
        query = """
            SELECT id, name, city, state, is_active
            FROM stores
        """
        if store_ids:
            query += " WHERE id = ANY(:store_ids)"
            params["store_ids"] = list(store_ids)
        query += " ORDER BY name"
        return fetch_all(query, params or None, timeout_ms=2000)
    
    @staticmethod
    def get_metrics(
        filters: DataFilters,
        include_prep_time: bool = False
    ) -> list[StoreMetrics]:
        """
        Obtém métricas por loja.
        
        Args:
            filters: Filtros a aplicar
            include_prep_time: Se deve incluir tempo de preparo
            
        Returns:
            Lista de métricas por loja
        """
        prep_time_select = ""
        prep_time_group = ""
        
        if include_prep_time:
            prep_time_select = """,
                COALESCE(AVG(
                    CASE 
                        WHEN s.sale_status_desc = 'COMPLETED' AND s.production_seconds IS NOT NULL 
                        THEN s.production_seconds / 60.0 
                    END
                ), 0) as avg_prep_minutes,
                COALESCE(PERCENTILE_CONT(0.9) WITHIN GROUP (
                    ORDER BY CASE 
                        WHEN s.sale_status_desc = 'COMPLETED' AND s.production_seconds IS NOT NULL 
                        THEN s.production_seconds 
                    END
                ) / 60.0, 0) as p90_prep_minutes
            """
        
        base_query = f"""
            SELECT 
                st.id as store_id,
                st.name as store_name,
                COUNT(*) FILTER (WHERE s.sale_status_desc = 'COMPLETED') as total_sales,
                COALESCE(SUM(s.total_amount) FILTER (WHERE s.sale_status_desc = 'COMPLETED'), 0) as total_revenue,
                COUNT(*) FILTER (WHERE s.sale_status_desc = 'CANCELLED') as cancelled_sales
                {prep_time_select}
            FROM sales s
            JOIN stores st ON st.id = s.store_id
        """
        
        # Adaptar filtros para não filtrar por status (queremos COMPLETED e CANCELLED)
        conditions = [
            "s.created_at >= :start_date",
            "s.created_at < :end_date",
        ]
        
        params = {
            "start_date": filters.start_date.isoformat(),
            "end_date": filters.end_date.isoformat(),
        }
        
        if filters.store_ids:
            conditions.append("s.store_id = ANY(:store_ids)")
            params["store_ids"] = list(filters.store_ids)
        
        if filters.channel_ids:
            conditions.append("s.channel_id = ANY(:channel_ids)")
            params["channel_ids"] = list(filters.channel_ids)
        
        where_clause = " AND ".join(conditions)
        query = f"{base_query} WHERE {where_clause}"
        query += " GROUP BY st.id, st.name ORDER BY total_revenue DESC"
        
        result = fetch_all(query, params, timeout_ms=5000)
        
        return [
            StoreMetrics(
                store_id=row["store_id"],
                store_name=row["store_name"],
                total_sales=row["total_sales"],
                total_revenue=row["total_revenue"],
                cancelled_sales=row["cancelled_sales"],
                avg_prep_minutes=float(row["avg_prep_minutes"]) if include_prep_time else None,
                p90_prep_minutes=float(row["p90_prep_minutes"]) if include_prep_time else None,
            )
            for row in result
        ]
