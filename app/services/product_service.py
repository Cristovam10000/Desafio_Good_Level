"""Product business logic service."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.domain.filters import DataFilters
from app.domain.models import ProductMetrics
from app.repositories.protocols import ProductRepositoryProtocol


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
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
            channel_ids=channel_ids,
        )
        return self.repository.get_top_addons(filters, limit)

    def get_combinations(
        self,
        start: datetime,
        end: datetime,
        store_ids: Optional[list[int]] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Get products frequently bought together."""
        filters = DataFilters(
            start_date=start,
            end_date=end,
            store_ids=store_ids,
        )
        return self.repository.get_combinations(filters, limit)
