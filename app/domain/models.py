"""
Modelos de domínio e DTOs.
Representam os conceitos de negócio independentes da infraestrutura.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class SalesSummary:
    """Resumo de vendas agregadas."""
    
    total_sales: int
    total_revenue: Decimal
    average_ticket: Decimal
    total_discount: Decimal
    
    @property
    def discount_rate(self) -> float:
        """Taxa de desconto sobre a receita total."""
        if self.total_revenue == 0:
            return 0.0
        return float((self.total_discount / self.total_revenue) * 100)


@dataclass
class DailySalesMetrics:
    """Métricas agregadas por dia."""
    
    day: date
    total_revenue: Decimal
    order_count: int
    avg_ticket: Decimal
    
    @property
    def day_iso(self) -> str:
        """Representação ISO da data."""
        return self.day.isoformat()


@dataclass
class HourlySalesMetrics:
    """Métricas agregadas por hora."""
    
    hour: int
    total_revenue: Decimal
    order_count: int


@dataclass
class DiscountReasonMetrics:
    """Métricas para motivos de desconto."""
    
    reason: str
    quantity: int
    total_discount: Decimal


@dataclass
class DeliveryMetrics:
    """Métricas de entrega."""
    
    total_deliveries: int
    avg_delivery_minutes: float
    p50_delivery_minutes: float
    p90_delivery_minutes: float
    p95_delivery_minutes: float
    within_sla_count: int
    sla_threshold_minutes: int = 60
    
    @property
    def within_sla_percentage(self) -> float:
        """Percentual de entregas dentro do SLA."""
        if self.total_deliveries == 0:
            return 0.0
        return (self.within_sla_count / self.total_deliveries) * 100


@dataclass
class ProductMetrics:
    """Métricas de produto."""
    
    product_id: int
    product_name: str
    total_quantity: float
    total_sales: int
    total_revenue: Decimal
    
    @property
    def avg_quantity_per_sale(self) -> float:
        """Quantidade média por venda."""
        if self.total_sales == 0:
            return 0.0
        return self.total_quantity / self.total_sales
    
    @property
    def avg_revenue_per_sale(self) -> Decimal:
        """Receita média por venda."""
        if self.total_sales == 0:
            return Decimal(0)
        return self.total_revenue / self.total_sales


@dataclass
class StoreMetrics:
    """Métricas de loja."""
    
    store_id: int
    store_name: str
    total_sales: int
    total_revenue: Decimal
    cancelled_sales: int
    avg_prep_minutes: Optional[float] = None
    p90_prep_minutes: Optional[float] = None
    
    @property
    def cancellation_rate(self) -> float:
        """Taxa de cancelamento."""
        total = self.total_sales + self.cancelled_sales
        if total == 0:
            return 0.0
        return (self.cancelled_sales / total) * 100


@dataclass
class TimeSeriesData:
    """Dados de série temporal."""
    
    bucket: datetime | date | str
    value: Decimal | int | float
    label: Optional[str] = None
    
    def __post_init__(self):
        """Gera label automaticamente se não fornecido."""
        if self.label is None:
            if isinstance(self.bucket, datetime):
                self.label = self.bucket.strftime("%Y-%m-%d %H:%M")
            elif isinstance(self.bucket, date):
                self.label = self.bucket.strftime("%Y-%m-%d")
            else:
                self.label = str(self.bucket)


@dataclass
class CityDeliveryMetrics:
    """Métricas de entrega por cidade."""
    
    city: str
    neighborhood: Optional[str] = None
    total_deliveries: int = 0
    avg_delivery_minutes: float = 0.0
    p90_delivery_minutes: float = 0.0


@dataclass
class ChannelMetrics:
    """Métricas por canal de vendas."""
    
    channel_id: int
    channel_name: str
    total_sales: int
    total_revenue: Decimal
    avg_ticket: Decimal


@dataclass
class DataRangeResult:
    """Intervalo de datas disponível nos dados."""
    
    min_date: datetime
    max_date: datetime


@dataclass
class TopProductsRow:
    """[LEGADO] Produto mais vendido por quantidade."""
    
    product_id: int
    product_name: str
    total_quantity: int


@dataclass
class ProductTopRow:
    """[LEGADO] Produto mais vendido com receita."""
    
    product_id: int
    product_name: str
    total_quantity: int
    total_revenue: Decimal


@dataclass
class SalesByHourRow:
    """[LEGADO] Vendas agregadas por hora com detalhes de loja e canal."""
    
    bucket_hour: str
    store_id: Optional[int]
    channel_id: Optional[int]
    orders: int
    revenue: float
    amount_items: float
    discounts: float
    service_tax_fee: float
    avg_ticket: Optional[float]


@dataclass
class DeliveryP90Row:
    """[LEGADO] P90 de entrega por loja."""
    
    store_id: int
    store_name: str
    p90_delivery_minutes: float
