"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.logging_config import setup_logging
from app.metrics.prometheus import setup_metrics

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle."""
    setup_logging(
        log_level="DEBUG" if settings.debug else "INFO",
        json_logs=settings.is_production,
    )
    yield
    # Cleanup on shutdown (close DB engine, etc.)
    from app.database import engine
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description=(
        "Production-ready Nigerian Real Estate Alert Platform. "
        "Scrapes property listings from multiple sources and delivers "
        "instant Telegram alerts to subscribers."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
if settings.metrics_enabled:
    setup_metrics(app)

# All routes
app.include_router(api_router)
