"""
Application builder following Clean Code principles.
Separates concerns from the monolithic create_app function.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import app_logger, init_app_logging
from app.core.security import AccessClaims
from app.infra.db import health_check
from app.routers import (
    analytics,
    auth,
    channels,
    delivery,
    finance,
    health,
    operations,
    products,
    sales,
    share,
    specials,
    stores,
    utils,
)


class ApplicationBuilder:
    """Builder for FastAPI application with separated concerns."""

    def __init__(self):
        self.app = FastAPI(
            title=settings.APP_NAME,
            version="1.0.0",
            description="Analytics API following Clean Code principles",
            openapi_url="/api/v1/openapi.json",
            docs_url="/docs",
            redoc_url="/redoc",
        )
        self._middlewares_added = False
        self._routes_added = False
        self._startup_handlers_added = False

    def add_cors_middleware(self) -> ApplicationBuilder:
        """Add CORS middleware configuration."""
        if self._middlewares_added:
            raise RuntimeError("Middlewares already added")

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS_LIST or ["http://localhost:3000", "http://localhost:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app_logger.info("CORS middleware added")
        return self

    def add_security_middleware(self) -> ApplicationBuilder:
        """Add security-related middlewares."""
        if self._middlewares_added:
            raise RuntimeError("Middlewares already added")

        # Add trusted host middleware if configured
        # Note: ALLOWED_HOSTS not in current settings, using default
        pass

        # Add custom security headers middleware
        @self.app.middleware("http")
        async def add_security_headers(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            return response

        app_logger.info("Security middleware added")
        return self

    def add_request_logging_middleware(self) -> ApplicationBuilder:
        """Add request logging middleware."""
        if self._middlewares_added:
            raise RuntimeError("Middlewares already added")

        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            app_logger.info(f"Request: {request.method} {request.url}")
            response = await call_next(request)
            app_logger.info(f"Response: {response.status_code}")
            return response

        app_logger.info("Request logging middleware added")
        return self

    def finalize_middlewares(self) -> ApplicationBuilder:
        """Mark middlewares as finalized."""
        self._middlewares_added = True
        return self

    def add_routes(self) -> ApplicationBuilder:
        """Add all API routes."""
        if self._routes_added:
            raise RuntimeError("Routes already added")

        # Include all routers directly
        self.app.include_router(auth.router)
        self.app.include_router(analytics.router)
        self.app.include_router(health.router)
        self.app.include_router(share.router)
        
        # Domain-specific routers (Clean Architecture)
        self.app.include_router(sales.router)
        self.app.include_router(products.router)
        self.app.include_router(delivery.router)
        self.app.include_router(stores.router)
        self.app.include_router(channels.router)
        self.app.include_router(operations.router)
        self.app.include_router(finance.router)
        self.app.include_router(utils.router)
        
        # Legacy specials router (to be gradually deprecated)
        self.app.include_router(specials.router)

        # Root routes
        @self.app.get("/healthz")
        def healthz():
            """Basic health check."""
            return {"status": "ok"}

        @self.app.get("/readyz")
        def readyz():
            """Readiness check with database connectivity."""
            try:
                db_status = health_check()
                return {
                    "status": "ready",
                    "database": db_status,
                }
            except Exception as exc:
                app_logger.error(f"Readiness check failed: {exc}")
                return JSONResponse(
                    status_code=503,
                    content={"status": "not ready", "error": str(exc)},
                )

        app_logger.info("All routes added")
        self._routes_added = True
        return self

    def add_startup_handlers(self) -> ApplicationBuilder:
        """Add startup and shutdown event handlers."""
        if self._startup_handlers_added:
            raise RuntimeError("Startup handlers already added")

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            app_logger.info("Starting application...")
            try:
                # Validate database connection
                health_check()
                app_logger.info("Database connection validated")
            except Exception as exc:
                app_logger.error(f"Database connection failed: {exc}")
                raise

            app_logger.info("Application started successfully")
            yield

            # Shutdown
            app_logger.info("Shutting down application...")

        self.app.router.lifespan_context = lifespan
        self._startup_handlers_added = True
        app_logger.info("Startup handlers added")
        return self

    def add_exception_handlers(self) -> ApplicationBuilder:
        """Add global exception handlers."""

        @self.app.exception_handler(500)
        async def internal_error_handler(request: Request, exc: Exception):
            app_logger.error(f"Internal error: {exc}", exc=exc)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )

        @self.app.exception_handler(404)
        async def not_found_handler(request: Request, exc: Exception):
            return JSONResponse(
                status_code=404,
                content={"detail": "Not found"},
            )

        app_logger.info("Exception handlers added")
        return self

    def build(self) -> FastAPI:
        """Build and return the configured FastAPI application."""
        if not self._middlewares_added:
            raise RuntimeError("Middlewares not finalized")
        if not self._routes_added:
            raise RuntimeError("Routes not added")
        if not self._startup_handlers_added:
            raise RuntimeError("Startup handlers not added")

        app_logger.info("FastAPI application built successfully")
        return self.app


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application using the builder pattern.
    Follows Single Responsibility Principle by separating concerns.
    """
    # Initialize structured logging
    init_app_logging()

    builder = (
        ApplicationBuilder()
        .add_cors_middleware()
        .add_security_middleware()
        .add_request_logging_middleware()
        .finalize_middlewares()
        .add_routes()
        .add_startup_handlers()
        .add_exception_handlers()
    )

    return builder.build()