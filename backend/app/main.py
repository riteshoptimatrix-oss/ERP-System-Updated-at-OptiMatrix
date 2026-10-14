import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import setup_exception_handlers
from app.core.logging import setup_logging
from app.database.mongodb import mongodb_manager
from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.logging import RequestLoggingMiddleware

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Initializes database pools, logging, and background resources on startup.
    Gracefully cleans up resources and closes connection pools on shutdown.
    """
    setup_logging()
    logger.info(
        f"Starting {settings.PROJECT_NAME} in [{settings.ENVIRONMENT}] environment..."
    )

    # Initialize MongoDB connection pool
    await mongodb_manager.connect()

    # Seed initial roles, unique indexes, and Super Admin root account
    from app.database.seeds import seed_initial_roles_and_admin
    await seed_initial_roles_and_admin()

    yield

    # Clean shutdown
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")
    await mongodb_manager.disconnect()
    logger.info("Shutdown complete.")


def create_application() -> FastAPI:
    """
    Factory function to configure and create the FastAPI application.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description="Production-grade Manufacturing ERP Backend for Opti Matrix (Unit 1: Heavy Machining & Unit 2: Precision Assembly & QC)",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    # Attach SlowAPI rate limiter state
    from app.core.rate_limit import limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi import _rate_limit_exceeded_handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Middleware Pipeline
    # 1. Correlation ID (outermost to wrap all operations)
    app.add_middleware(CorrelationIdMiddleware)

    # 2. Structured Request Logging
    app.add_middleware(RequestLoggingMiddleware)

    # 3. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    # Centralized Exception Handlers
    setup_exception_handlers(app)

    # Include API Routers
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_application()
