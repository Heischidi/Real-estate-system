"""Scraper admin routes — manually trigger scraping."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin
from app.scrapers.registry import ScraperRegistry

router = APIRouter(prefix="/scrape", tags=["Scraper (Admin)"])


@router.post("")
async def trigger_scrape(
    _: dict[str, object] = Depends(get_current_admin),
) -> dict[str, object]:
    """Manually trigger a full scrape cycle. Admin only."""
    from app.tasks.scrape import scrape_all_sources

    task = scrape_all_sources.apply_async(queue="scraping")
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Scrape task has been queued. Check task status for results.",
    }


@router.get("/status")
async def scraper_status(
    _: dict[str, object] = Depends(get_current_admin),
) -> dict[str, object]:
    """List all registered scrapers and their enabled/disabled status."""
    from app.config import get_settings

    settings = get_settings()
    all_names = ScraperRegistry.list_names()
    return {
        "registered_scrapers": all_names,
        "disabled_scrapers": settings.disabled_scrapers,
        "active_scrapers": [
            n for n in all_names if n not in settings.disabled_scrapers
        ],
    }
