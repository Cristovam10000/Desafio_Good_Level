"""Finance business logic service."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.infra.db import fetch_all


class FinanceService:
    """Service for finance-related business logic (payments, revenue)."""

    @staticmethod
    def get_payments_mix(
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
    ) -> list[dict]:
        """Get payment types mix by channel."""
        where = [
            "s.sale_status_desc = 'COMPLETED'",
            "s.created_at >= :start",
            "s.created_at < :end",
        ]
        params: dict = {"start": start, "end": end}
        
        if store_ids:
            where.append("s.store_id = ANY(:store_ids)")
            params["store_ids"] = store_ids
        
        if channel_ids:
            where.append("s.channel_id = ANY(:channel_ids)")
            params["channel_ids"] = channel_ids
        
        sql = f"""
            WITH totals AS (
                SELECT SUM(p.value) AS grand_total
                FROM payments p
                JOIN sales s ON s.id = p.sale_id
                WHERE {" AND ".join(where)}
            )
            SELECT
                pt.description AS payment_type,
                c.name AS channel_name,
                SUM(p.value)::float AS revenue,
                COUNT(*)::int AS transactions,
                (SUM(p.value) / NULLIF(t.grand_total, 0) * 100)::float AS pct
            FROM payments p
            JOIN payment_types pt ON p.payment_type_id = pt.id
            JOIN sales s ON s.id = p.sale_id
            JOIN channels c ON s.channel_id = c.id
            CROSS JOIN totals t
            WHERE {" AND ".join(where)}
            GROUP BY pt.description, c.name, t.grand_total
            ORDER BY revenue DESC
        """
        
        return fetch_all(sql, params, timeout_ms=2000)

    @staticmethod
    def get_net_vs_gross(
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
    ) -> dict:
        """Get net vs gross revenue breakdown."""
        where = [
            "sale_status_desc = 'COMPLETED'",
            "created_at >= :start",
            "created_at < :end",
        ]
        params: dict = {"start": start, "end": end}
        
        if store_ids:
            where.append("store_id = ANY(:store_ids)")
            params["store_ids"] = store_ids
        
        if channel_ids:
            where.append("channel_id = ANY(:channel_ids)")
            params["channel_ids"] = channel_ids
        
        sql = f"""
            SELECT
                SUM(total_amount)::float AS gross_revenue,
                SUM(total_discount)::float AS total_discounts,
                SUM(service_tax_fee)::float AS service_fees,
                SUM(delivery_fee)::float AS delivery_fees,
                (SUM(total_amount) - SUM(total_discount))::float AS net_revenue,
                (SUM(total_discount) / NULLIF(SUM(total_amount), 0) * 100)::float AS discount_pct
            FROM sales
            WHERE {" AND ".join(where)}
        """
        
        result = fetch_all(sql, params, timeout_ms=2000)
        return result[0] if result else {
            "gross_revenue": 0.0,
            "total_discounts": 0.0,
            "service_fees": 0.0,
            "delivery_fees": 0.0,
            "net_revenue": 0.0,
            "discount_pct": 0.0,
        }

