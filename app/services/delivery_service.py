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
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
        )
        return self.repository.get_regions(filters, city, limit)

    def get_percentiles(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        sla_minutes: int = 45,
    ) -> dict:
        """Get delivery time percentiles."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
        )
        return self.repository.get_percentiles(filters, sla_minutes)

    def get_stats(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
    ) -> dict:
        """Get general delivery statistics."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
        )
        return self.repository.get_stats(filters)

    def get_stores_rank(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get delivery performance ranking by store."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
        )
        return self.repository.get_stores_rank(filters, limit)
