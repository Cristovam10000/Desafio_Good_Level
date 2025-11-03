"""Repository protocol definitions used by domain services."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol, Sequence

from app.domain.filters import DataFilters
from app.domain.models import (
    ChannelMetrics,
    DailySalesMetrics,
    DeliveryMetrics,
    HourlySalesMetrics,
    SalesSummary,
    DiscountReasonMetrics,
    CityDeliveryMetrics,
    ProductMetrics,
    StoreMetrics,
)


class SalesRepositoryProtocol(Protocol):
    """Contract for sales data access."""

    def get_summary(self, filters: DataFilters) -> Optional[SalesSummary]: ...

    def get_by_day(self, filters: DataFilters) -> list[DailySalesMetrics]: ...

    def get_by_channel(self, filters: DataFilters) -> list[ChannelMetrics]: ...

    def get_by_hour(self, filters: DataFilters) -> list[HourlySalesMetrics]: ...

    def get_discount_reasons(
        self, filters: DataFilters, limit: int = 10
    ) -> list[DiscountReasonMetrics]: ...


class ProductRepositoryProtocol(Protocol):
    """Contract for product data access."""

    def get_top_sellers(self, filters: DataFilters, limit: int = 20) -> list[ProductMetrics]: ...

    def get_low_sellers(self, filters: DataFilters, limit: int = 20) -> list[ProductMetrics]: ...

    def get_most_customized(self, filters: DataFilters, limit: int = 20) -> list[dict]: ...

    def get_top_addons(self, filters: DataFilters, limit: int = 10) -> list[dict]: ...

    def get_combinations(self, filters: DataFilters, limit: int = 20) -> list[dict]: ...


class DeliveryRepositoryProtocol(Protocol):
    """Contract for delivery-related queries."""

    def get_metrics(
        self, filters: DataFilters, sla_threshold_minutes: int = 60
    ) -> Optional[DeliveryMetrics]: ...

    def get_by_city(self, filters: DataFilters, limit: int = 20) -> list[CityDeliveryMetrics]: ...

    def get_by_neighborhood(
        self, filters: DataFilters, city: Optional[str] = None, limit: int = 20
    ) -> list[CityDeliveryMetrics]: ...

    def get_regions(
        self, filters: DataFilters, city: Optional[str] = None, limit: int = 50
    ) -> list[dict]: ...

    def get_percentiles(self, filters: DataFilters, sla_minutes: int = 45) -> dict: ...

    def get_stats(self, filters: DataFilters) -> dict: ...

    def get_stores_rank(self, filters: DataFilters, limit: int = 10) -> list[dict]: ...


class StoreRepositoryProtocol(Protocol):
    """Contract for store data access."""

    def get_all(self, store_ids: Optional[Sequence[int]] = None) -> list[dict]: ...

    def get_metrics(
        self, filters: DataFilters, include_prep_time: bool = False
    ) -> list[StoreMetrics]: ...


class ChannelRepositoryProtocol(Protocol):
    """Contract for channel data access."""

    def get_all(self, store_ids: Optional[Sequence[int]] = None) -> list[dict]: ...

    def get_by_name(self, name: str) -> Optional[dict]: ...
