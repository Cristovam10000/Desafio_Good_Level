"""Product business logic service."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.domain.filters import DataFilters
from app.domain.models import ProductMetrics
from app.repositories.product_repository import ProductRepository


class ProductService:
    """Service for product-related business logic."""

    def __init__(self, repository: ProductRepository | None = None):
        """Initialize the service with a repository instance."""
        self.repository = repository or ProductRepository()

    def get_top_sellers(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
        limit: int = 10,
    ) -> list[ProductMetrics]:
        """Get top selling products for the given period and filters."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
            channel_ids=channel_ids,
        )
        return self.repository.get_top_sellers(filters, limit)

    def get_low_sellers(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
        limit: int = 10,
    ) -> list[ProductMetrics]:
        """Get low selling products for the given period and filters."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
            channel_ids=channel_ids,
        )
        return self.repository.get_low_sellers(filters, limit)

    def get_most_customized(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get products with most customizations for the given period and filters."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
            channel_ids=channel_ids,
        )
        return self.repository.get_most_customized(filters, limit)

    def get_top_addons(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get top add-on items (modifiers)."""
        from app.infra.db import fetch_all
        
        where = [
            "s.created_at >= :start",
            "s.created_at < :end",
        ]
        params: dict = {"start": start, "end": end, "limit": limit}
        
        if store_ids:
            where.append("s.store_id = ANY(:store_ids)")
            params["store_ids"] = store_ids
        
        if channel_ids:
            where.append("s.channel_id = ANY(:channel_ids)")
            params["channel_ids"] = channel_ids
        
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

    def get_combinations(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Get products frequently bought together."""
        from app.infra.db import fetch_all
        
        where = [
            "s.created_at >= :start",
            "s.created_at < :end",
        ]
        params: dict = {"start": start, "end": end, "limit": limit}
        
        if store_ids:
            where.append("s.store_id = ANY(:store_ids)")
            params["store_ids"] = store_ids
        
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
        
        return fetch_all(sql, params, timeout_ms=3000)
