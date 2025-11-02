"""
Repositório de vendas.
Centraliza todo acesso a dados relacionados a vendas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Sequence

from app.infra.db import fetch_all, fetch_one
from app.domain.filters import DataFilters
from app.domain.models import (
    SalesSummary,
    ChannelMetrics,
    DailySalesMetrics,
    HourlySalesMetrics,
    DiscountReasonMetrics,
)


class SalesRepository:
    """
    Repositório para acesso a dados de vendas.
    Encapsula toda lógica SQL relacionada a vendas.
    """
    
    @staticmethod
    def get_summary(filters: DataFilters) -> Optional[SalesSummary]:
        """
        Obtém resumo agregado de vendas.
        
        Args:
            filters: Filtros a aplicar
            
        Returns:
            Resumo de vendas ou None se não houver dados
        """
        base_query = """
            SELECT 
                COUNT(*) as total_sales,
                COALESCE(SUM(s.total_amount), 0) as total_revenue,
                COALESCE(AVG(s.total_amount), 0) as average_ticket,
                COALESCE(SUM(s.total_discount), 0) as total_discount
            FROM sales s
        """
        
        query, params = filters.apply_to_query(base_query)
        
        result = fetch_one(query, params, timeout_ms=5000)
        
        if not result or result["total_sales"] == 0:
            return None
        
        return SalesSummary(
            total_sales=result["total_sales"],
            total_revenue=Decimal(str(result["total_revenue"])),
            average_ticket=Decimal(str(result["average_ticket"])),
            total_discount=Decimal(str(result["total_discount"])),
        )
    
    @staticmethod
    def get_by_day(filters: DataFilters) -> list[DailySalesMetrics]:
        """
        Obtém vendas agregadas por dia.
        
        Args:
            filters: Filtros a aplicar
            
        Returns:
            Lista de métricas diárias de vendas
        """
        base_query = """
            SELECT 
                DATE_TRUNC('day', s.created_at AT TIME ZONE 'America/Sao_Paulo')::date as bucket_day,
                COALESCE(SUM(s.total_amount), 0) as total_revenue,
                COUNT(*) as order_count,
                COALESCE(AVG(s.total_amount), 0) as avg_ticket
            FROM sales s
        """
        
        query, params = filters.apply_to_query(base_query)
        query += " GROUP BY bucket_day ORDER BY bucket_day"
        
        result = fetch_all(query, params, timeout_ms=5000)
        
        return [
            DailySalesMetrics(
                day=row["bucket_day"],
                total_revenue=Decimal(str(row["total_revenue"])),
                order_count=row["order_count"],
                avg_ticket=Decimal(str(row["avg_ticket"])),
            )
            for row in result
        ]
    
    @staticmethod
    def get_by_channel(filters: DataFilters) -> list[ChannelMetrics]:
        """
        Obtém vendas agregadas por canal.
        
        Args:
            filters: Filtros a aplicar
            
        Returns:
            Lista de métricas por canal
        """
        base_query = """
            SELECT 
                s.channel_id,
                c.name as channel_name,
                COUNT(*) as total_sales,
                COALESCE(SUM(s.total_amount), 0) as total_revenue,
                COALESCE(AVG(s.total_amount), 0) as avg_ticket
            FROM sales s
            JOIN channels c ON c.id = s.channel_id
        """
        
        query, params = filters.apply_to_query(base_query)
        query += " GROUP BY s.channel_id, c.name ORDER BY total_revenue DESC"
        
        result = fetch_all(query, params, timeout_ms=5000)
        
        return [
            ChannelMetrics(
                channel_id=row["channel_id"],
                channel_name=row["channel_name"],
                total_sales=row["total_sales"],
                total_revenue=Decimal(str(row["total_revenue"])),
                avg_ticket=Decimal(str(row["avg_ticket"])),
            )
            for row in result
        ]
    
    @staticmethod
    def get_by_hour(filters: DataFilters) -> list[HourlySalesMetrics]:
        """
        Obtém vendas agregadas por hora do dia.
        
        Args:
            filters: Filtros a aplicar
            
        Returns:
            Lista de métricas por hora
        """
        base_query = """
            SELECT 
                EXTRACT(HOUR FROM s.created_at AT TIME ZONE 'America/Sao_Paulo')::int as hour_bucket,
                COALESCE(SUM(s.total_amount), 0) as total_revenue,
                COUNT(*) as order_count
            FROM sales s
        """
        
        query, params = filters.apply_to_query(base_query)
        query += " GROUP BY hour_bucket ORDER BY hour_bucket"
        
        result = fetch_all(query, params, timeout_ms=5000)
        
        return [
            HourlySalesMetrics(
                hour=int(row["hour_bucket"]),
                total_revenue=Decimal(str(row["total_revenue"])),
                order_count=row["order_count"],
            )
            for row in result
        ]
    
    @staticmethod
    def get_discount_reasons(
        filters: DataFilters, 
        limit: int = 10
    ) -> list[DiscountReasonMetrics]:
        """
        Obtém motivos de desconto mais frequentes.
        
        Args:
            filters: Filtros a aplicar
            limit: Número máximo de resultados
            
        Returns:
            Lista de motivos com contagens
        """
        base_query = """
            SELECT 
                s.discount_reason as reason,
                COUNT(*) as quantity,
                COALESCE(SUM(s.total_discount), 0) as total_discount
            FROM sales s
        """
        
        query, params = filters.apply_to_query(base_query)
        query += """
            AND s.discount_reason IS NOT NULL 
            AND s.discount_reason != ''
            GROUP BY s.discount_reason 
            ORDER BY quantity DESC 
            LIMIT :limit
        """
        params["limit"] = limit
        
        result = fetch_all(query, params, timeout_ms=5000)
        
        return [
            DiscountReasonMetrics(
                reason=row["reason"],
                quantity=row["quantity"],
                total_discount=Decimal(str(row["total_discount"])),
            )
            for row in result
        ]
