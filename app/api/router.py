"""Central API router — assembles all route modules."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import check_system_active
from app.api.routes import (
    admin_ui,
    auth,
    health,
    listings,
    payments,
    scraper,
    stats,
    subscribers,
)

api_router = APIRouter(dependencies=[Depends(check_system_active)])

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(listings.router)
api_router.include_router(subscribers.router)
api_router.include_router(payments.router)
api_router.include_router(scraper.router)
api_router.include_router(stats.router)
api_router.include_router(admin_ui.router)
