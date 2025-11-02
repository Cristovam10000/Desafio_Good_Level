"""
Repositórios para acesso a dados.
Implementam a camada de persistência seguindo Clean Architecture.
"""

from .sales_repository import SalesRepository
from .delivery_repository import DeliveryRepository
from .product_repository import ProductRepository
from .store_repository import StoreRepository
from .channel_repository import ChannelRepository

__all__ = [
    "SalesRepository",
    "DeliveryRepository",
    "ProductRepository",
    "StoreRepository",
    "ChannelRepository",
]
