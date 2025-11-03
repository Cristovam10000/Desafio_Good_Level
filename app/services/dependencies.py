"""FastAPI dependency providers for service layer."""

from app.repositories.sales_repository import SalesRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.delivery_repository import DeliveryRepository
from app.repositories.store_repository import StoreRepository
from app.repositories.channel_repository import ChannelRepository
from app.services.sales_service import SalesService
from app.services.product_service import ProductService
from app.services.delivery_service import DeliveryService
from app.services.store_service import StoreService
from app.services.channel_service import ChannelService


def get_sales_service() -> SalesService:
    return SalesService(SalesRepository())


def get_product_service() -> ProductService:
    return ProductService(ProductRepository())


def get_delivery_service() -> DeliveryService:
    return DeliveryService(DeliveryRepository())


def get_store_service() -> StoreService:
    return StoreService(StoreRepository())


def get_channel_service() -> ChannelService:
    return ChannelService(ChannelRepository())
