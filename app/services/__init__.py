"""
Serviços de domínio separados das rotas.

Inclui serviços de negócio por domínio e utilidades para geração de insights (LangChain + Gemini).
"""

from .channel_service import ChannelService  # noqa: F401
from .delivery_service import DeliveryService  # noqa: F401
from .finance_service import FinanceService  # noqa: F401
from .insights import (  # noqa: F401
    build_dataset,
    generate_dataset_insights,
    InsightsDataset,
)
from .operations_service import OperationsService  # noqa: F401
from .product_service import ProductService  # noqa: F401
from .sales_service import SalesService  # noqa: F401
from .store_service import StoreService  # noqa: F401
from .utils_service import UtilsService  # noqa: F401

__all__ = [
    "build_dataset",
    "ChannelService",
    "DeliveryService",
    "FinanceService",
    "generate_dataset_insights",
    "InsightsDataset",
    "OperationsService",
    "ProductService",
    "SalesService",
    "StoreService",
    "UtilsService",
]
