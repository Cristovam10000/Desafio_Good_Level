"""Store business logic service."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.domain.filters import DataFilters
from app.domain.models import StoreMetrics
from app.repositories.protocols import StoreRepositoryProtocol


class StoreService:
    """Service for store-related business logic."""

    def __init__(self, repository: StoreRepository | None = None):
        """Initialize the service with a repository instance."""
        self.repository = repository or StoreRepository()

    def get_all(self, user_store_ids: Optional[list[int]] = None) -> list[dict]:
        """Get all stores, optionally filtered by user's accessible stores."""
        return self.repository.get_all(user_store_ids)

    def get_metrics(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        channel_ids: Optional[list[int]] = None,
        include_prep_time: bool = False,
    ) -> list[StoreMetrics]:
        """Get store metrics for the given period and filters."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
            channel_ids=channel_ids,
        )
        return self.repository.get_metrics(filters, include_prep_time)

    def get_timeseries(
        self,
        store_id: int,
        start: datetime,
        end: datetime,
    ) -> list[dict]:
        """Get time series data for a specific store."""
        from app.infra.db import fetch_all
        
        params = {"start": start, "end": end, "store_id": store_id}
        
        sql = """
            SELECT
                DATE(created_at) AS bucket_day,
                SUM(total_amount)::float AS revenue,
                COUNT(*)::int AS orders
            FROM sales
            WHERE sale_status_desc = 'COMPLETED'
              AND created_at >= :start
              AND created_at < :end
              AND store_id = :store_id
            GROUP BY DATE(created_at)
            ORDER BY bucket_day ASC
        """
        
        return fetch_all(sql, params, timeout_ms=2000)
