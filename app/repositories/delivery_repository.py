"""
Repositório de entregas.
Centraliza todo acesso a dados relacionados a entregas.
"""

from typing import Optional

from app.infra.db import fetch_all, fetch_one
from app.domain.filters import DataFilters
from app.domain.models import DeliveryMetrics, CityDeliveryMetrics


class DeliveryRepository:
    """
    Repositório para acesso a dados de entregas.
    Encapsula toda lógica SQL relacionada a entregas.
    """
    
    @staticmethod
    def get_metrics(
        filters: DataFilters,
        sla_threshold_minutes: int = 60
    ) -> Optional[DeliveryMetrics]:
        """
        Obtém métricas agregadas de entregas.
        
        Args:
            filters: Filtros a aplicar
            sla_threshold_minutes: Limite de tempo para considerar dentro do SLA
            
        Returns:
            Métricas de entrega ou None se não houver dados
        """
        base_query = f"""
            SELECT 
                COUNT(*) as total_deliveries,
                COALESCE(AVG(s.delivery_seconds) / 60.0, 0) as avg_delivery_minutes,
                COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY s.delivery_seconds) / 60.0, 0) as p50_delivery_minutes,
                COALESCE(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds) / 60.0, 0) as p90_delivery_minutes,
                COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY s.delivery_seconds) / 60.0, 0) as p95_delivery_minutes,
                COUNT(*) FILTER (WHERE s.delivery_seconds / 60.0 <= {sla_threshold_minutes}) as within_sla_count
            FROM sales s
        """
        
        query, params = filters.apply_to_query(base_query)
        query += " AND s.delivery_seconds IS NOT NULL"
        
        result = fetch_one(query, params, timeout_ms=5000)
        
        if not result or result["total_deliveries"] == 0:
            return None
        
        return DeliveryMetrics(
            total_deliveries=result["total_deliveries"],
            avg_delivery_minutes=float(result["avg_delivery_minutes"]),
            p50_delivery_minutes=float(result["p50_delivery_minutes"]),
            p90_delivery_minutes=float(result["p90_delivery_minutes"]),
            p95_delivery_minutes=float(result["p95_delivery_minutes"]),
            within_sla_count=result["within_sla_count"],
            sla_threshold_minutes=sla_threshold_minutes,
        )
    
    @staticmethod
    def get_by_city(
        filters: DataFilters,
        limit: int = 20
    ) -> list[CityDeliveryMetrics]:
        """
        Obtém métricas de entrega por cidade.
        
        Args:
            filters: Filtros a aplicar
            limit: Número máximo de cidades
            
        Returns:
            Lista de métricas por cidade
        """
        base_query = """
            SELECT 
                da.city,
                COUNT(*) as total_deliveries,
                COALESCE(AVG(s.delivery_seconds) / 60.0, 0) as avg_delivery_minutes,
                COALESCE(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds) / 60.0, 0) as p90_delivery_minutes
            FROM sales s
            JOIN delivery_addresses da ON da.sale_id = s.id
        """
        
        query, params = filters.apply_to_query(base_query)
        query += """
            AND s.delivery_seconds IS NOT NULL
            GROUP BY da.city
            ORDER BY total_deliveries DESC
            LIMIT :limit
        """
        params["limit"] = limit
        
        result = fetch_all(query, params, timeout_ms=5000)
        
        return [
            CityDeliveryMetrics(
                city=row["city"],
                total_deliveries=row["total_deliveries"],
                avg_delivery_minutes=float(row["avg_delivery_minutes"]),
                p90_delivery_minutes=float(row["p90_delivery_minutes"]),
            )
            for row in result
        ]
    
    @staticmethod
    def get_by_neighborhood(
        filters: DataFilters,
        city: Optional[str] = None,
        limit: int = 20
    ) -> list[CityDeliveryMetrics]:
        """
        Obtém métricas de entrega por bairro.
        
        Args:
            filters: Filtros a aplicar
            city: Filtrar por cidade específica
            limit: Número máximo de bairros
            
        Returns:
            Lista de métricas por bairro
        """
        base_query = """
            SELECT 
                da.city,
                da.neighborhood,
                COUNT(*) as total_deliveries,
                COALESCE(AVG(s.delivery_seconds) / 60.0, 0) as avg_delivery_minutes,
                COALESCE(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds) / 60.0, 0) as p90_delivery_minutes
            FROM sales s
            JOIN delivery_addresses da ON da.sale_id = s.id
        """
        
        query, params = filters.apply_to_query(base_query)
        query += " AND s.delivery_seconds IS NOT NULL"
        
        if city:
            query += " AND da.city = :city"
            params["city"] = city
        
        query += """
            GROUP BY da.city, da.neighborhood
            ORDER BY p90_delivery_minutes DESC
            LIMIT :limit
        """
        params["limit"] = limit
        
        result = fetch_all(query, params, timeout_ms=5000)
        
        return [
            CityDeliveryMetrics(
                city=row["city"],
                neighborhood=row["neighborhood"],
                total_deliveries=row["total_deliveries"],
                avg_delivery_minutes=float(row["avg_delivery_minutes"]),
                p90_delivery_minutes=float(row["p90_delivery_minutes"]),
            )
            for row in result
        ]
    
    @staticmethod
    def get_regions(
        filters: DataFilters,
        city: Optional[str] = None,
        limit: int = 50
    ) -> list[dict]:
        """
        Obtém desempenho de entrega por região (cidade + bairro).
        """
        base_query = """
            SELECT
                da.city,
                da.neighborhood,
                COUNT(*)::int AS deliveries,
                AVG(s.delivery_seconds / 60.0)::float AS avg_minutes,
                PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds / 60.0)::float AS p90_minutes
            FROM sales s
            JOIN delivery_addresses da ON da.sale_id = s.id
        """
        
        query, params = filters.apply_to_query(base_query)
        query += " AND s.delivery_seconds IS NOT NULL"
        
        if city:
            query += " AND da.city = :city"
            params["city"] = city
        
        query += """
            GROUP BY da.city, da.neighborhood
            ORDER BY deliveries DESC
            LIMIT :limit
        """
        params["limit"] = limit
        
        return fetch_all(query, params, timeout_ms=3000)
    
    @staticmethod
    def get_percentiles(
        filters: DataFilters,
        sla_minutes: int = 45
    ) -> dict:
        """
        Obtém percentis de tempo de entrega.
        """
        base_query = """
            SELECT
                AVG(s.delivery_seconds / 60.0)::float AS avg_minutes,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY s.delivery_seconds / 60.0)::float AS p50_minutes,
                PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds / 60.0)::float AS p90_minutes,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY s.delivery_seconds / 60.0)::float AS p95_minutes,
                (
                    SUM(CASE WHEN s.delivery_seconds / 60.0 <= :sla_minutes THEN 1 ELSE 0 END)::float
                    / NULLIF(COUNT(*), 0) * 100
                )::float AS within_sla_pct
            FROM sales s
        """
        
        query, params = filters.apply_to_query(base_query)
        query += " AND s.delivery_seconds IS NOT NULL"
        params["sla_minutes"] = sla_minutes
        
        result = fetch_all(query, params, timeout_ms=2000)
        return result[0] if result else {
            "avg_minutes": 0.0,
            "p50_minutes": 0.0,
            "p90_minutes": 0.0,
            "p95_minutes": 0.0,
            "within_sla_pct": 0.0,
        }
    
    @staticmethod
    def get_stats(
        filters: DataFilters,
    ) -> dict:
        """
        Obtém estatísticas gerais de entrega.
        """
        base_query = """
            SELECT
                COUNT(*)::int AS total_deliveries,
                MIN(s.delivery_seconds / 60.0)::float AS fastest_minutes,
                MAX(s.delivery_seconds / 60.0)::float AS slowest_minutes,
                AVG(s.delivery_seconds / 60.0)::float AS avg_minutes
            FROM sales s
        """
        
        query, params = filters.apply_to_query(base_query)
        query += " AND s.delivery_seconds IS NOT NULL"
        
        result = fetch_all(query, params, timeout_ms=2000)
        return result[0] if result else {
            "total_deliveries": 0,
            "fastest_minutes": 0.0,
            "slowest_minutes": 0.0,
            "avg_minutes": 0.0,
        }
    
    @staticmethod
    def get_stores_rank(
        filters: DataFilters,
        limit: int = 10
    ) -> list[dict]:
        """
        Obtém ranking de desempenho de entrega por loja.
        """
        base_query = """
            SELECT
                s.store_id,
                st.name AS store_name,
                COUNT(*)::int AS deliveries,
                AVG(s.delivery_seconds / 60.0)::float AS avg_minutes,
                PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds / 60.0)::float AS p90_minutes
            FROM sales s
            JOIN stores st ON s.store_id = st.id
        """
        
        query, params = filters.apply_to_query(base_query)
        query += """
            AND s.delivery_seconds IS NOT NULL
            GROUP BY s.store_id, st.name
            ORDER BY deliveries DESC
            LIMIT :limit
        """
        params["limit"] = limit
        
        return fetch_all(query, params, timeout_ms=3000)
