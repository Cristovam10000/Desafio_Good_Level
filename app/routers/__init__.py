"""API routers module."""

# Legacy routers
from . import analytics, auth, health, share, specials

# Domain-specific routers (Clean Architecture)
from . import channels, delivery, finance, operations, products, sales, stores, utils

__all__ = [
    "analytics",
    "auth",
    "channels",
    "delivery",
    "finance",
    "health",
    "operations",
    "products",
    "sales",
    "share",
    "specials",
    "stores",
    "utils",
]
