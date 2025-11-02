"""Sales business logic service."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.domain.filters import DataFilters
from app.domain.models import (
    SalesSummary,
    ChannelMetrics,
    DailySalesMetrics,
    HourlySalesMetrics,
    DiscountReasonMetrics,
)
from app.repositories.sales_repository import SalesRepository


class SalesService:
    """Service for sales-related business logic."""

    def __init__(self, repository: SalesRepository | None = None):
        """Initialize the service with a repository instance."""
        self.repository = repository or SalesRepository()

    def get_summary(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
    ) -> SalesSummary | None:
        """Get sales summary for the given period and filters."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
            channel_ids=channel_ids,
        )
        return self.repository.get_summary(filters)

    def get_by_day(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
    ) -> list[DailySalesMetrics]:
        """Get daily sales data for the given period and filters."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
            channel_ids=channel_ids,
        )
        return self.repository.get_by_day(filters)

    def get_by_channel(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
    ) -> list[ChannelMetrics]:
        """Get sales data grouped by channel for the given period and filters."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
            channel_ids=channel_ids,
        )
        return self.repository.get_by_channel(filters)

    def get_by_hour(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
    ) -> list[HourlySalesMetrics]:
        """Get hourly sales data for the given period and filters."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
            channel_ids=channel_ids,
        )
        return self.repository.get_by_hour(filters)

    def get_discount_reasons(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
        limit: int = 10,
    ) -> list[DiscountReasonMetrics]:
        """Get top discount reasons for the given period and filters."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
            channel_ids=channel_ids,
        )
        return self.repository.get_discount_reasons(filters, limit)

    def get_by_weekday(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
    ) -> list[dict]:
        """Get sales data grouped by weekday."""
        from app.infra.db import fetch_all
        
        where = [
            "s.sale_status_desc = 'COMPLETED'",
            "s.created_at >= :start",
            "s.created_at < :end",
        ]
        params: dict = {"start": start, "end": end}
        
        if store_ids:
            where.append("s.store_id = ANY(:store_ids)")
            params["store_ids"] = store_ids
        
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
