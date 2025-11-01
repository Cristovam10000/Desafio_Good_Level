"""
Refactored analytics services following Clean Code principles.
Eliminated massive duplication from the original 539-line analytics.py file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from fastapi import HTTPException, Query
from pydantic import BaseModel

from app.core.cache import etag_json
from app.core.security import AccessClaims
from app.infra.db import fetch_all


# ------------------------------------------------------------------------------
# Domain Models
# ------------------------------------------------------------------------------


class AnalyticsFilters(BaseModel):
    """Common filters for analytics endpoints."""
    store_ids: Optional[List[int]] = None
    channel_ids: Optional[Sequence[int]] = None
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_params(
        cls,
        start: str,
        end: str,
        store_ids: Optional[List[int]] = None,
        channel_ids: Optional[Sequence[int]] = None,
    ) -> AnalyticsFilters:
        """Create filters from endpoint parameters."""
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Datas inválidas: {exc}") from exc

        if start_dt >= end_dt:
            raise HTTPException(status_code=400, detail="'start' deve ser anterior a 'end'")

        return cls(
            store_ids=store_ids,
            channel_ids=channel_ids,
            start_date=start_dt,
            end_date=end_dt,
        )


class AnalyticsResponse(BaseModel):
    """Common response structure for analytics endpoints."""
    ok: bool = True
    data: List[Dict[str, Any]]
    period: Dict[str, str]
    filters: Dict[str, Any]
    metadata: Dict[str, Any]


# ------------------------------------------------------------------------------
# Base Analytics Service
# ------------------------------------------------------------------------------


class BaseAnalyticsService(ABC):
    """Base class for analytics services with common functionality."""

    def __init__(self, filters: AnalyticsFilters):
        self.filters = filters

    @abstractmethod
    def get_query(self) -> str:
        """Return the SQL query for this analytics service."""
        pass

    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """Return query parameters."""
        pass

    @abstractmethod
    def validate_response(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and transform response data."""
        pass

    def execute_query(self, timeout_ms: int = 3000) -> List[Dict[str, Any]]:
        """Execute the analytics query with common error handling."""
        try:
            return fetch_all(
                self.get_query(),
                self.get_params(),
                timeout_ms=timeout_ms
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Erro na consulta analítica: {exc}"
            ) from exc

    def build_response(self, data: List[Dict[str, Any]]) -> AnalyticsResponse:
        """Build standardized response."""
        validated_data = self.validate_response(data)

        return AnalyticsResponse(
            data=validated_data,
            period={
                "start": self.filters.start_date.isoformat(),
                "end": self.filters.end_date.isoformat(),
            },
            filters={
                "store_ids": self.filters.store_ids,
                "channel_ids": list(self.filters.channel_ids) if self.filters.channel_ids else None,
            },
            metadata={
                "query_type": self.__class__.__name__,
                "record_count": len(validated_data),
            },
        )

    def get_metadata(self) -> Dict[str, Any]:
        """Return metadata for the response."""
        return {
            "query_type": self.__class__.__name__,
            "record_count": 0,  # Will be set by build_response
        }


# ------------------------------------------------------------------------------
# Specific Analytics Services
# ------------------------------------------------------------------------------


class TopAdditionsService(BaseAnalyticsService):
    """Service for top product additions analytics."""

    def get_query(self) -> str:
        return """
        SELECT 
            i.name AS item_name,
            COUNT(*)::int AS quantidade_vendas,
            SUM(ips.price)::float AS receita_total,
            AVG(ips.price)::float AS preco_medio
        FROM item_product_sales ips
        JOIN items i ON i.id = ips.item_id
        JOIN product_sales ps ON ps.id = ips.product_sale_id
        JOIN sales s ON s.id = ps.sale_id
        WHERE s.sale_status_desc = 'COMPLETED'
            AND s.created_at >= :start_date
            AND s.created_at < :end_date
        GROUP BY i.name
        ORDER BY quantidade_vendas DESC
        LIMIT 5
        """

    def get_params(self) -> Dict[str, Any]:
        params = {
            "start_date": self.filters.start_date.isoformat(),
            "end_date": self.filters.end_date.isoformat(),
        }

        if self.filters.store_ids:
            # Add store filtering logic
            pass
        if self.filters.channel_ids:
            # Add channel filtering logic
            pass

        return params

    def validate_response(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate top additions data."""
        return data


class TopRemovalsService(BaseAnalyticsService):
    """Service for top product removals analytics."""

    def get_query(self) -> str:
        # Similar structure to TopAdditionsService but for removals
        return """
        SELECT 
            p.name AS product_name,
            COUNT(ps.id)::int AS quantidade_vendas,
            SUM(ps.quantity)::float AS quantidade_itens
        FROM products p
        LEFT JOIN product_sales ps ON ps.product_id = p.id
        LEFT JOIN sales s ON s.id = ps.sale_id AND s.sale_status_desc = 'COMPLETED'
            AND s.created_at >= :start_date
            AND s.created_at < :end_date
        GROUP BY p.id, p.name
        HAVING COUNT(ps.id) > 0
        ORDER BY quantidade_vendas ASC
        LIMIT 5
        """

    def get_params(self) -> Dict[str, Any]:
        return {
            "start_date": self.filters.start_date.isoformat(),
            "end_date": self.filters.end_date.isoformat(),
        }

    def validate_response(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate top removals data."""
        return data


class DeliveryTimeByRegionService(BaseAnalyticsService):
    """Service for delivery time analytics by region."""

    def get_query(self) -> str:
        return """
        SELECT 
            da.neighborhood AS regiao,
            AVG(s.delivery_seconds / 60.0)::float AS tempo_medio_minutos,
            COUNT(DISTINCT s.id)::int AS total_entregas,
            MIN(s.delivery_seconds / 60.0)::float AS tempo_minimo,
            MAX(s.delivery_seconds / 60.0)::float AS tempo_maximo
        FROM sales s
        JOIN delivery_addresses da ON da.sale_id = s.id
        WHERE s.sale_status_desc = 'COMPLETED'
            AND s.delivery_seconds IS NOT NULL
            AND s.delivery_seconds > 0
            AND da.neighborhood IS NOT NULL
            AND LENGTH(da.neighborhood) > 3
            AND s.created_at >= :start_date
            AND s.created_at < :end_date
        GROUP BY da.neighborhood
        HAVING COUNT(DISTINCT s.id) >= 5
        ORDER BY tempo_medio_minutos DESC
        LIMIT 10
        """

    def get_params(self) -> Dict[str, Any]:
        return {
            "start_date": self.filters.start_date.isoformat(),
            "end_date": self.filters.end_date.isoformat(),
        }

    def validate_response(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate delivery time data."""
        return data


class PaymentMixByChannelService(BaseAnalyticsService):
    """Service for payment method mix by channel analytics."""

    def get_query(self) -> str:
        return """
        SELECT 
            c.name AS canal,
            pt.description AS forma_pagamento,
            COUNT(*)::int AS quantidade_vendas,
            SUM(p.value)::float AS valor_total,
            ROUND((COUNT(*)::numeric / SUM(COUNT(*)) OVER (PARTITION BY c.name) * 100), 1)::float AS percentual
        FROM payments p
        JOIN sales s ON s.id = p.sale_id
        JOIN payment_types pt ON pt.id = p.payment_type_id
        JOIN channels c ON c.id = s.channel_id
        WHERE s.sale_status_desc = 'COMPLETED'
            AND s.created_at >= :start_date
            AND s.created_at < :end_date
        GROUP BY c.name, pt.description
        ORDER BY c.name, quantidade_vendas DESC
        """

    def get_params(self) -> Dict[str, Any]:
        return {
            "start_date": self.filters.start_date.isoformat(),
            "end_date": self.filters.end_date.isoformat(),
        }

    def validate_response(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate payment mix data."""
        return data  # Basic validation - could add more specific checks


# ------------------------------------------------------------------------------
# Service Factory
# ------------------------------------------------------------------------------


class AnalyticsServiceFactory:
    """Factory for creating analytics services."""

    @staticmethod
    def create_service(
        service_type: str,
        filters: AnalyticsFilters
    ) -> BaseAnalyticsService:
        """Create the appropriate analytics service."""
        services = {
            "top-additions": TopAdditionsService,
            "top-removals": TopRemovalsService,
            "delivery-time-by-region": DeliveryTimeByRegionService,
            "payment-mix-by-channel": PaymentMixByChannelService,
        }

        service_class = services.get(service_type)
        if not service_class:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de serviço inválido: {service_type}"
            )

        return service_class(filters)