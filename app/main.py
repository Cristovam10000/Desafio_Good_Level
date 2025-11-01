from __future__ import annotations
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import analytics, auth, specials, health
from app.routers.share import router as share_router
from app.infra.db import health_check
from app.infra.cube_client import cube_meta, CubeError


def create_app() -> FastAPI:
    # Instância principal da aplicação
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url="/docs",           # Swagger
        redoc_url="/redoc",         # ReDoc
        openapi_url="/openapi.json" # Esquema OpenAPI
    )

    # -------------------------------------------------------------------------
    # CORS (origens permitidas vêm do .env -> settings.CORS_ORIGINS)
    # -------------------------------------------------------------------------
    allowed_origins = settings.CORS_ORIGINS_LIST or [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    logger = logging.getLogger("uvicorn.error")
    logger.info("CORS allow: %s", allowed_origins)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.cors_allowed_origins = allowed_origins

    @app.middleware("http")
    async def _log_auth_requests(request: Request, call_next):
        if request.url.path.startswith("/auth"):
            print(
                "AUTH inbound | method=%s path=%s origin=%s"
                % (request.method, request.url.path, request.headers.get("origin")),
            )
        response = await call_next(request)
        if request.url.path.startswith("/auth"):
            print(
                "AUTH outbound | method=%s path=%s status=%s acao=%s"
                % (
                    request.method,
                    request.url.path,
                    response.status_code,
                    response.headers.get("access-control-allow-origin"),
                ),
            )
        return response

    # -------------------------------------------------------------------------
    # Routers (ordem não importa; /healthz e /readyz primeiro por conveniência)
    # -------------------------------------------------------------------------
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(analytics.router)
    app.include_router(specials.router)
    app.include_router(share_router)

    # -------------------------------------------------------------------------
    # Rota raiz para conveniência (links rápidos)
    # -------------------------------------------------------------------------
    @app.get("/")
    def root():
        return {
            "name": settings.APP_NAME,
            "env": settings.ENV,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "healthz": "/healthz",
            "readyz": "/readyz",
        }

    @app.get("/__debug/cors")
    def debug_cors(request: Request):
        return {
            "allowed_origins": app.state.cors_allowed_origins,
            "request_origin": request.headers.get("origin"),
            "request_referer": request.headers.get("referer"),
        }

    # -------------------------------------------------------------------------
    # Startup hook: logs rápidos (não falham o boot se der erro)
    # -------------------------------------------------------------------------
    @app.on_event("startup")
    async def _startup_checks():
        # Logging básico (útil em dev; em prod prefira config via gunicorn/uvicorn)
        logging.basicConfig(level=logging.INFO if settings.DEBUG else logging.WARNING)

        # 1) DB health
        try:
            info = health_check()
            logging.info(
                "DB ok | db=%s user=%s",
                info.get("database"), info.get("user")
            )
        except Exception as e:
            logging.warning("DB ainda não respondeu no startup: %s", e)

        # 2) Cube meta
        try:
            meta = await cube_meta(timeout=5.0, retries=0)
            # meta costuma trazer 'cubes' com medidas/dimensões
            n_cubes = len(meta.get("cubes", [])) if isinstance(meta, dict) else "?"
            logging.info("Cube ok | cubes=%s", n_cubes)
        except CubeError as ce:
            logging.warning("Cube não respondeu /meta (%s): %s", ce.status_code, ce.message)
        except Exception as e:
            logging.warning("Cube ainda não respondeu no startup: %s", e)

    return app


# Instância global para uvicorn: `uvicorn app.main:app --reload`
app = create_app()
