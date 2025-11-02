"""Delivery business logic service."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.domain.filters import DataFilters
from app.domain.models import DeliveryMetrics, CityDeliveryMetrics
from app.repositories.delivery_repository import DeliveryRepository


class DeliveryService:
    """Service for delivery-related business logic."""

    def __init__(self, repository: DeliveryRepository | None = None):
        """Initialize the service with a repository instance."""
        self.repository = repository or DeliveryRepository()

    def get_metrics(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
    ) -> DeliveryMetrics | None:
        """Get delivery metrics for the given period and filters."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
            channel_ids=channel_ids,
        )
        return self.repository.get_metrics(filters)

    def get_by_city(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
        limit: int = 10,
    ) -> list[CityDeliveryMetrics]:
        """Get delivery metrics grouped by city for the given period and filters."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
            channel_ids=channel_ids,
        )
        return self.repository.get_by_city(filters, limit)

    def get_by_neighborhood(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
        limit: int = 10,
    ) -> list[CityDeliveryMetrics]:
        """Get delivery metrics grouped by neighborhood for the given period and filters."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
            channel_ids=channel_ids,
        )
        return self.repository.get_by_neighborhood(filters, None, limit)

    def get_regions(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        city: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get delivery performance by region (city + neighborhood)."""
        from app.infra.db import fetch_all
        
        where = [
            "s.sale_status_desc = 'COMPLETED'",
            "s.delivery_seconds IS NOT NULL",
            "s.created_at >= :start",
            "s.created_at < :end",
        ]
        params: dict = {"start": start, "end": end, "limit": limit}
        
        if store_ids:
            where.append("s.store_id = ANY(:store_ids)")
            params["store_ids"] = store_ids
        
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
            ORDER BY deliveries DESC
            LIMIT :limit
        """
        
        return fetch_all(sql, params, timeout_ms=3000)

    def get_percentiles(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        sla_minutes: int = 45,
    ) -> dict:
        """Get delivery time percentiles."""
        from app.infra.db import fetch_all
        
        where = [
            "sale_status_desc = 'COMPLETED'",
            "delivery_seconds IS NOT NULL",
            "created_at >= :start",
            "created_at < :end",
        ]
        params: dict = {"start": start, "end": end, "sla_minutes": sla_minutes}
        
        if store_ids:
            where.append("store_id = ANY(:store_ids)")
            params["store_ids"] = store_ids
        
        sql = f"""
            SELECT
                AVG(delivery_seconds / 60.0)::float AS avg_minutes,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY delivery_seconds / 60.0)::float AS p50_minutes,
                PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY delivery_seconds / 60.0)::float AS p90_minutes,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY delivery_seconds / 60.0)::float AS p95_minutes,
                (SUM(CASE WHEN delivery_seconds / 60.0 <= :sla_minutes THEN 1 ELSE 0 END)::float / 
                    COUNT(*) * 100)::float AS within_sla_pct
            FROM sales
            WHERE {" AND ".join(where)}
        """
        
        result = fetch_all(sql, params, timeout_ms=2000)
        return result[0] if result else {
            "avg_minutes": 0,
            "p50_minutes": 0,
            "p90_minutes": 0,
            "p95_minutes": 0,
            "within_sla_pct": 0,
        }

    def get_stats(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
    ) -> dict:
        """Get general delivery statistics."""
        from app.infra.db import fetch_all
        
        where = [
            "sale_status_desc = 'COMPLETED'",
            "delivery_seconds IS NOT NULL",
            "created_at >= :start",
            "created_at < :end",
        ]
        params: dict = {"start": start, "end": end}
        
        if store_ids:
            where.append("store_id = ANY(:store_ids)")
            params["store_ids"] = store_ids
        
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
        return result[0] if result else {
            "total_deliveries": 0,
            "fastest_minutes": 0,
            "slowest_minutes": 0,
            "avg_minutes": 0,
        }

    def get_stores_rank(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get delivery performance ranking by store."""
        from app.infra.db import fetch_all
        
        where = [
            "s.sale_status_desc = 'COMPLETED'",
            "s.delivery_seconds IS NOT NULL",
            "s.created_at >= :start",
            "s.created_at < :end",
        ]
        params: dict = {"start": start, "end": end, "limit": limit}
        
        if store_ids:
            where.append("s.store_id = ANY(:store_ids)")
            params["store_ids"] = store_ids
        
        sql = f"""
            SELECT
                s.store_id,
                st.name AS store_name,
                COUNT(*)::int AS deliveries,
                AVG(s.delivery_seconds / 60.0)::float AS avg_minutes,
                PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds / 60.0)::float AS p90_minutes
            FROM sales s
            JOIN stores st ON s.store_id = st.id
            WHERE {" AND ".join(where)}
            GROUP BY s.store_id, st.name
            ORDER BY deliveries DESC
            LIMIT :limit
        """
        
        return fetch_all(sql, params, timeout_ms=3000)
