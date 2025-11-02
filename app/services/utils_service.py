"""Utility endpoints service (data-range, refresh, legacy endpoints)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.infra.db import fetch_all, refresh_materialized_views


class UtilsService:
    """Service for utility endpoints (data range, MV refresh, legacy endpoints)."""

    @staticmethod
    def get_data_range() -> dict:
        """Get the date range of available data in the database."""
        sql = """
            SELECT
                MIN(created_at)::text AS min_date,
                MAX(created_at)::text AS max_date
            FROM sales
        """
        result = fetch_all(sql, timeout_ms=2000)
        if result:
            return {
                "min_date": result[0]["min_date"],
                "max_date": result[0]["max_date"],
            }
        return {"min_date": None, "max_date": None}

    @staticmethod
    def refresh_materialized_views() -> dict:
        """Refresh all materialized views."""
        try:
            refresh_materialized_views()
            return {"status": "success", "message": "Materialized views refreshed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_top_products(
        limit: int,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
        offset: int = 0,
    ) -> list[dict]:
        """
        Get top products (legacy endpoint - simple ranking).
        This is a lightweight fallback without depending on specific MVs.
        """
        where_clauses = []
        params: dict = {"limit": limit, "offset": offset, "start": start, "end": end}

        where_clauses.extend(["s.created_at >= :start", "s.created_at < :end"])

        if store_ids:
            where_clauses.append("s.store_id = ANY(:store_ids)")
            params["store_ids"] = store_ids

        if channel_ids:
            where_clauses.append("s.channel_id = ANY(:channel_ids)")
            params["channel_ids"] = channel_ids

        sql = f"""
            SELECT
                ps.product_id,
                p.name AS product_name,
                SUM(ps.quantity)::float AS qty
            FROM product_sales ps
            JOIN products p ON p.id = ps.product_id
            JOIN sales s ON s.id = ps.sale_id
            WHERE {" AND ".join(where_clauses)}
            GROUP BY ps.product_id, p.name
            ORDER BY qty DESC
            LIMIT :limit OFFSET :offset
        """

        return fetch_all(sql, params, timeout_ms=3000)

    @staticmethod
    def get_product_top(
        limit: int,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
    ) -> list[dict]:
        """
        Get top products with revenue (legacy endpoint - similar to top-products).
        """
        where_clauses = []
        params: dict = {"limit": limit, "start": start, "end": end}

        where_clauses.extend(["s.created_at >= :start", "s.created_at < :end"])

        if store_ids:
            where_clauses.append("s.store_id = ANY(:store_ids)")
            params["store_ids"] = store_ids

        if channel_ids:
            where_clauses.append("s.channel_id = ANY(:channel_ids)")
            params["channel_ids"] = channel_ids

        sql = f"""
            SELECT
                ps.product_id,
                p.name AS product_name,
                SUM(ps.quantity)::float AS qty,
                SUM(ps.subtotal)::float AS revenue
            FROM product_sales ps
            JOIN products p ON p.id = ps.product_id
            JOIN sales s ON s.id = ps.sale_id
            WHERE {" AND ".join(where_clauses)}
            GROUP BY ps.product_id, p.name
            ORDER BY revenue DESC
            LIMIT :limit
        """

        return fetch_all(sql, params, timeout_ms=3000)

    @staticmethod
    def get_sales_hour(
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
    ) -> list[dict]:
        """
        Get sales by hour with store and channel details (legacy endpoint).
        Returns detailed hourly data grouped by bucket_hour, store_id, and channel_id.
        """
        where_clauses = []
        params: dict = {"start": start, "end": end}

        where_clauses.extend(["s.created_at >= :start", "s.created_at < :end"])

        if store_ids:
            where_clauses.append("s.store_id = ANY(:store_ids)")
            params["store_ids"] = store_ids

        if channel_ids:
            where_clauses.append("s.channel_id = ANY(:channel_ids)")
            params["channel_ids"] = channel_ids

        sql = f"""
            SELECT
                TO_CHAR(date_trunc('hour', s.created_at), 'YYYY-MM-DD"T"HH24:MI:SS') AS bucket_hour,
                s.store_id,
                s.channel_id,
                COUNT(*)::int AS orders,
                COALESCE(SUM(s.total_amount), 0)::float AS revenue,
                COALESCE(SUM(s.total_amount_items), 0)::float AS amount_items,
                COALESCE(SUM(s.total_discount), 0)::float AS discounts,
                COALESCE(SUM(s.service_tax_fee), 0)::float AS service_tax_fee,
                CASE 
                    WHEN COUNT(*) > 0 
                    THEN (SUM(s.total_amount) / COUNT(*))::float 
                    ELSE NULL 
                END AS avg_ticket
            FROM sales s
            WHERE {" AND ".join(where_clauses)}
            GROUP BY date_trunc('hour', s.created_at), s.store_id, s.channel_id
            ORDER BY bucket_hour ASC
            LIMIT 10000
        """

        return fetch_all(sql, params, timeout_ms=5000)

    @staticmethod
    def get_delivery_p90(
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
    ) -> list[dict]:
        """Get P90 delivery time by store."""
        where_clauses = [
            "delivery_seconds IS NOT NULL",
        ]
        params: dict = {"start": start, "end": end}

        where_clauses.extend(["created_at >= :start", "created_at < :end"])

        if store_ids:
            where_clauses.append("store_id = ANY(:store_ids)")
            params["store_ids"] = store_ids

        sql = f"""
            SELECT
                store_id,
                COUNT(*)::int AS deliveries,
                PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY delivery_seconds / 60.0)::float AS p90_minutes
            FROM sales
            WHERE {" AND ".join(where_clauses)}
            GROUP BY store_id
            ORDER BY p90_minutes DESC
        """

        return fetch_all(sql, params, timeout_ms=2000)
