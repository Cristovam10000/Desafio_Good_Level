from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Optional

import pandas as pd

from app.infra.db import fetch_all
from app.core.ai import generate_insights_text
from sqlalchemy.exc import ProgrammingError


def _parse_date(value: str) -> date:
    try:
        normalized = value.strip()
        normalized = normalized.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
    except Exception as exc:
        raise ValueError(f"Data inválida: {value}") from exc
    return dt.date()


def _start_end(start: str, end: str) -> tuple[datetime, datetime]:
    start_date = _parse_date(start)
    end_date = _parse_date(end)
    if start_date >= end_date:
        raise ValueError("'start' deve ser anterior a 'end'.")

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    return start_dt, end_dt


def _fetch_sales_daily(
    start_dt: datetime,
    end_dt: datetime,
    store_ids: Optional[list[int]],
    channel_id: Optional[int],
) -> pd.DataFrame:
    where_mv = ["bucket_hour >= :start_dt", "bucket_hour < :end_dt"]
    params: Dict[str, object] = {
        "start_dt": start_dt.isoformat(),
        "end_dt": end_dt.isoformat(),
    }

    if store_ids:
        where_mv.append("store_id = ANY(:store_ids)")
        params["store_ids"] = store_ids
    if channel_id is not None:
        where_mv.append("channel_id = :channel_id")
        params["channel_id"] = channel_id

    sql_mv = f"""
    SELECT
      DATE(bucket_hour) AS bucket_day,
      SUM(orders)::int                     AS orders,
      SUM(revenue)::float                  AS revenue,
      SUM(amount_items)::float             AS items_value,
      SUM(discounts)::float                AS discounts,
      CASE
        WHEN SUM(orders) > 0 THEN (SUM(revenue) / NULLIF(SUM(orders), 0))::float
        ELSE NULL
      END                                  AS avg_ticket
    FROM mv_sales_hour
    WHERE {" AND ".join(where_mv)}
    GROUP BY DATE(bucket_hour)
    ORDER BY bucket_day ASC
    """
    try:
        rows = fetch_all(sql_mv, params, timeout_ms=1500)
    except ProgrammingError as exc:
        if "UndefinedTable" not in str(exc):
            raise
        where_raw = [
            "s.sale_status_desc = 'COMPLETED'",
            "s.created_at >= :start_dt",
            "s.created_at < :end_dt",
        ]
        if store_ids:
            where_raw.append("s.store_id = ANY(:store_ids)")
        if channel_id is not None:
            where_raw.append("s.channel_id = :channel_id")

        sql_raw = f"""
        SELECT
          DATE(s.created_at) AS bucket_day,
          COUNT(*)::int AS orders,
          COALESCE(SUM(s.total_amount), 0)::float AS revenue,
          COALESCE(SUM(s.total_amount_items), 0)::float AS items_value,
          COALESCE(SUM(s.total_discount), 0)::float AS discounts,
          CASE WHEN COUNT(*) > 0 THEN (SUM(s.total_amount) / COUNT(*))::float ELSE NULL END AS avg_ticket
        FROM sales s
        WHERE {" AND ".join(where_raw)}
        GROUP BY DATE(s.created_at)
        ORDER BY bucket_day ASC
        """
        rows = fetch_all(sql_raw, params, timeout_ms=3000)
    return pd.DataFrame(rows)


def _fetch_top_products(
    start_dt: datetime,
    end_dt: datetime,
    limit: int,
    store_ids: Optional[list[int]],
) -> pd.DataFrame:
    if store_ids:
        sql = """
        SELECT
          p.name                               AS product_name,
          SUM(ps.total_price)::float           AS revenue,
          SUM(ps.quantity)::float              AS qty,
          COUNT(DISTINCT ps.sale_id)::int      AS orders
        FROM product_sales ps
        JOIN sales s      ON s.id = ps.sale_id
        JOIN products p   ON p.id = ps.product_id
        WHERE s.sale_status_desc = 'COMPLETED'
          AND s.created_at >= :start_dt
          AND s.created_at < :end_dt
          AND s.store_id = ANY(:store_ids)
        GROUP BY p.name
        ORDER BY revenue DESC
        LIMIT :limit
        """
        params = {
            "start_dt": start_dt.isoformat(),
            "end_dt": end_dt.isoformat(),
            "store_ids": store_ids,
            "limit": limit,
        }
        rows = fetch_all(sql, params, timeout_ms=1500)
        return pd.DataFrame(rows)

    sql_mv = """
    SELECT
      MAX(product_name) AS product_name,
      SUM(revenue)::float AS revenue,
      SUM(qty)::float     AS qty,
      SUM(orders)::int    AS orders
    FROM mv_product_day
    WHERE bucket_day >= :start_date
      AND bucket_day < :end_date
    GROUP BY product_id
    ORDER BY revenue DESC
    LIMIT :limit
    """
    params_mv = {
        "start_date": start_dt.date().isoformat(),
        "end_date": (end_dt.date()).isoformat(),
        "limit": limit,
    }
    try:
        rows = fetch_all(sql_mv, params_mv, timeout_ms=1500)
    except ProgrammingError as exc:
        if "UndefinedTable" not in str(exc):
            raise
        sql_raw = """
        SELECT
          p.name                               AS product_name,
          SUM(ps.total_price)::float           AS revenue,
          SUM(ps.quantity)::float              AS qty,
          COUNT(DISTINCT ps.sale_id)::int      AS orders
        FROM product_sales ps
        JOIN sales s      ON s.id = ps.sale_id
        JOIN products p   ON p.id = ps.product_id
        WHERE s.sale_status_desc = 'COMPLETED'
          AND s.created_at >= :start_dt
          AND s.created_at < :end_dt
        GROUP BY p.name
        ORDER BY revenue DESC
        LIMIT :limit
        """
        params_raw = {
            "start_dt": start_dt.isoformat(),
            "end_dt": end_dt.isoformat(),
            "limit": limit,
        }
        rows = fetch_all(sql_raw, params_raw, timeout_ms=3000)
    return pd.DataFrame(rows)


def _fetch_delivery_stats(
    start_dt: datetime,
    end_dt: datetime,
    limit: int,
    city: Optional[str],
    store_ids: Optional[list[int]],
) -> pd.DataFrame:
    if store_ids:
        where = [
            "s.sale_status_desc = 'COMPLETED'",
            "s.delivery_seconds IS NOT NULL",
            "s.created_at >= :start_dt",
            "s.created_at < :end_dt",
            "s.store_id = ANY(:store_ids)",
        ]
        if city:
            where.append("da.city = :city")
        sql = f"""
        SELECT
          DATE(s.created_at)                                            AS bucket_day,
          da.city,
          da.neighborhood,
          COUNT(*)                                                      AS deliveries,
          AVG(s.delivery_seconds)::float / 60.0                         AS avg_delivery_minutes,
          PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds)::float / 60.0 AS p90_delivery_minutes
        FROM sales s
        JOIN delivery_addresses da ON da.sale_id = s.id
        WHERE {" AND ".join(where)}
        GROUP BY DATE(s.created_at), da.city, da.neighborhood
        ORDER BY p90_delivery_minutes DESC, deliveries DESC
        LIMIT :limit
        """
        params: Dict[str, object] = {
            "start_dt": start_dt.isoformat(),
            "end_dt": end_dt.isoformat(),
            "store_ids": store_ids,
            "limit": limit,
        }
        if city:
            params["city"] = city
    else:
        where = ["bucket_day >= :start_date", "bucket_day < :end_date"]
        params = {
            "start_date": start_dt.date().isoformat(),
            "end_date": (end_dt.date()).isoformat(),
            "limit": limit,
        }
        if city:
            where.append("city = :city")
            params["city"] = city

        sql = f"""
        SELECT
          bucket_day,
          city,
          neighborhood,
          deliveries,
          avg_delivery_minutes,
          p90_delivery_minutes
        FROM mv_delivery_p90
        WHERE {" AND ".join(where)}
        ORDER BY p90_delivery_minutes DESC, deliveries DESC
        LIMIT :limit
        """
        try:
            rows = fetch_all(sql, params, timeout_ms=1500)
        except ProgrammingError as exc:
            if "UndefinedTable" not in str(exc):
                raise
            where_raw = [
                "s.sale_status_desc = 'COMPLETED'",
                "s.delivery_seconds IS NOT NULL",
                "s.created_at >= :start_dt",
                "s.created_at < :end_dt",
            ]
            if city:
                where_raw.append("da.city = :city")
            sql_raw = f"""
            SELECT
              DATE(s.created_at)                                            AS bucket_day,
              da.city,
              da.neighborhood,
              COUNT(*)                                                      AS deliveries,
              AVG(s.delivery_seconds)::float / 60.0                         AS avg_delivery_minutes,
              PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.delivery_seconds)::float / 60.0 AS p90_delivery_minutes
            FROM sales s
            JOIN delivery_addresses da ON da.sale_id = s.id
            WHERE {" AND ".join(where_raw)}
            GROUP BY DATE(s.created_at), da.city, da.neighborhood
            ORDER BY p90_delivery_minutes DESC, deliveries DESC
            LIMIT :limit
            """
            params_raw = {
                "start_dt": start_dt.isoformat(),
                "end_dt": end_dt.isoformat(),
                "limit": limit,
            }
            if city:
                params_raw["city"] = city
            rows = fetch_all(sql_raw, params_raw, timeout_ms=3000)
        return pd.DataFrame(rows)

    rows = fetch_all(sql, params, timeout_ms=1500)
    return pd.DataFrame(rows)


@dataclass
class InsightsDataset:
    sales_daily: pd.DataFrame
    top_products: pd.DataFrame
    delivery_stats: pd.DataFrame

    def is_empty(self) -> bool:
        return all(df.empty for df in (self.sales_daily, self.top_products, self.delivery_stats))

    def to_prompt_payload(self) -> str:
        def _fmt(title: str, df: pd.DataFrame, limit: int = 10) -> str:
            if df.empty:
                return f"## {title}\nSem dados disponíveis no período."
            view = df.head(limit)
            csv_text = view.to_csv(index=False)
            return f"## {title}\n{csv_text.strip()}"

        sections = [
            _fmt("Vendas agregadas por dia", self.sales_daily, limit=14),
            _fmt("Top produtos por receita", self.top_products, limit=10),
            _fmt("Performance de entrega (p90 minutos)", self.delivery_stats, limit=10),
        ]
        return "\n\n".join(sections)

    def preview(self, limit: int = 10) -> Dict[str, list]:
        def _preview(df: pd.DataFrame) -> list:
            if df.empty:
                return []
            return df.head(limit).to_dict(orient="records")

        return {
            "sales_daily": _preview(self.sales_daily),
            "top_products": _preview(self.top_products),
            "delivery_stats": _preview(self.delivery_stats),
        }


def build_dataset(
    start: str,
    end: str,
    *,
    store_ids: Optional[list[int]],
    channel_id: Optional[int],
    city: Optional[str],
    top_products: int,
    top_locations: int,
) -> InsightsDataset:
    start_dt, end_dt = _start_end(start, end)

    sales_daily = _fetch_sales_daily(start_dt, end_dt, store_ids, channel_id)
    top_products_df = _fetch_top_products(start_dt, end_dt, top_products, store_ids)
    delivery_df = _fetch_delivery_stats(start_dt, end_dt, top_locations, city, store_ids)

    return InsightsDataset(
        sales_daily=sales_daily,
        top_products=top_products_df,
        delivery_stats=delivery_df,
    )


def _extract_bullets(text: str) -> list[str]:
    items: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = line.lstrip("-•0123456789. ").strip()
        if line:
            items.append(line)
    return items


async def generate_dataset_insights(dataset: InsightsDataset) -> Dict[str, object]:
    prompt_payload = dataset.to_prompt_payload()
    raw_text = await generate_insights_text(prompt_payload)
    bullets = _extract_bullets(raw_text)
    if not bullets:
        bullets = [raw_text]
    return {
        "insights": bullets,
        "raw_text": raw_text,
    }
