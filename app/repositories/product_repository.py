"""
Repositório de produtos.
Centraliza todo acesso a dados relacionados a produtos.
"""

from typing import Optional

from app.infra.db import fetch_all
from app.domain.filters import DataFilters
from app.domain.models import ProductMetrics


class ProductRepository:
    """
    Repositório para acesso a dados de produtos.
    Encapsula toda lógica SQL relacionada a produtos.
    """
    
    @staticmethod
    def get_top_sellers(
        filters: DataFilters,
        limit: int = 20
    ) -> list[ProductMetrics]:
        """
        Obtém produtos mais vendidos.
        
        Args:
            filters: Filtros a aplicar
            limit: Número máximo de produtos
            
        Returns:
            Lista de métricas de produtos ordenada por receita
        """
        base_query = """
            SELECT 
                p.id as product_id,
                p.name as product_name,
                COALESCE(SUM(ps.quantity), 0) as total_quantity,
                COUNT(DISTINCT s.id) as total_sales,
                COALESCE(SUM(ps.total_price), 0) as total_revenue
            FROM sales s
            JOIN product_sales ps ON ps.sale_id = s.id
            JOIN products p ON p.id = ps.product_id
        """
        
        query, params = filters.apply_to_query(base_query)
        query += """
            GROUP BY p.id, p.name
            ORDER BY total_revenue DESC
            LIMIT :limit
        """
        params["limit"] = limit
        
        result = fetch_all(query, params, timeout_ms=5000)
        
        return [
            ProductMetrics(
                product_id=row["product_id"],
                product_name=row["product_name"],
                total_quantity=row["total_quantity"],
                total_sales=row["total_sales"],
                total_revenue=row["total_revenue"],
            )
            for row in result
        ]
    
    @staticmethod
    def get_low_sellers(
        filters: DataFilters,
        limit: int = 20
    ) -> list[ProductMetrics]:
        """
        Obtém produtos menos vendidos.
        
        Args:
            filters: Filtros a aplicar
            limit: Número máximo de produtos
            
        Returns:
            Lista de métricas de produtos ordenada por receita (crescente)
        """
        base_query = """
            SELECT 
                p.id as product_id,
                p.name as product_name,
                COALESCE(SUM(ps.quantity), 0) as total_quantity,
                COUNT(DISTINCT s.id) as total_sales,
                COALESCE(SUM(ps.total_price), 0) as total_revenue
            FROM sales s
            JOIN product_sales ps ON ps.sale_id = s.id
            JOIN products p ON p.id = ps.product_id
        """
        
        query, params = filters.apply_to_query(base_query)
        query += """
            GROUP BY p.id, p.name
            HAVING COUNT(DISTINCT s.id) > 0
            ORDER BY total_revenue ASC
            LIMIT :limit
        """
        params["limit"] = limit
        
        result = fetch_all(query, params, timeout_ms=5000)
        
        return [
            ProductMetrics(
                product_id=row["product_id"],
                product_name=row["product_name"],
                total_quantity=row["total_quantity"],
                total_sales=row["total_sales"],
                total_revenue=row["total_revenue"],
            )
            for row in result
        ]
    
    @staticmethod
    def get_most_customized(
        filters: DataFilters,
        limit: int = 20
    ) -> list[dict]:
        """
        Obtém produtos com mais customizações.
        
        Args:
            filters: Filtros a aplicar
            limit: Número máximo de produtos
            
        Returns:
            Lista de produtos com contagem de customizações
        """
        base_query = """
            SELECT 
                p.id as product_id,
                p.name as product_name,
                COUNT(*) as customization_count,
                COUNT(DISTINCT s.id) as total_sales,
                CASE 
                    WHEN COUNT(DISTINCT s.id) > 0 
                    THEN COUNT(*)::float / COUNT(DISTINCT s.id)::float
                    ELSE 0 
                END as avg_customizations_per_order
            FROM sales s
            JOIN product_sales ps ON ps.sale_id = s.id
            JOIN products p ON p.id = ps.product_id
            JOIN item_product_sales pa ON pa.product_sale_id = ps.id
        """
        
        query, params = filters.apply_to_query(base_query)
        query += """
            GROUP BY p.id, p.name
            ORDER BY customization_count DESC
            LIMIT :limit
        """
        params["limit"] = limit
        
        return fetch_all(query, params, timeout_ms=5000)

