"""Celery scraping tasks."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.killswitch import SYSTEM_PAUSED
from app.logging_config import get_logger
from app.tasks.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(
    name="app.tasks.scrape.scrape_all_sources",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def scrape_all_sources(self: object) -> dict[str, object]:
    """
    Main scraping task — runs all registered scraper adapters and stores new listings.
    Triggered by Celery Beat every 15 minutes.
    """
    if SYSTEM_PAUSED:
        log.info("scrape_all_sources skipped — system is paused.")
        return {"paused": True, "total_found": 0, "total_new": 0}
    return asyncio.run(_async_scrape_all())


async def _async_scrape_all() -> dict[str, object]:
    from app.database import get_db_context
    from app.scrapers.registry import ScraperRegistry
    from app.services.listing_service import ListingService

    started_at = datetime.now(tz=timezone.utc)
    scrapers = ScraperRegistry.get_all_scrapers()
    log.info("scrape_cycle_started", scraper_count=len(scrapers))

    total_found = 0
    total_new = 0
    results: dict[str, dict[str, int]] = {}

    for scraper in scrapers:
        try:
            listings = await scraper.scrape()
            found = len(listings)
            new_count = 0

            if listings:
                async with get_db_context() as db:
                    service = ListingService(db)
                    for listing_data in listings:
                        try:
                            _, is_new = await service.upsert_listing(listing_data)
                            if is_new:
                                new_count += 1
                        except Exception as exc:
                            log.error(
                                "listing_upsert_failed",
                                scraper=scraper.name,
                                error=str(exc),
                            )

            results[scraper.name] = {"found": found, "new": new_count}
            total_found += found
            total_new += new_count

            log.info(
                "scraper_complete",
                scraper=scraper.name,
                found=found,
                new=new_count,
            )

        except Exception as exc:
            log.error("scraper_task_error", scraper=scraper.name, error=str(exc))
            results[scraper.name] = {"found": 0, "new": 0, "error": str(exc)}

    # Trigger alert processing for newly added listings
    if total_new > 0:
        from app.tasks.alerts import process_new_listings
        process_new_listings.apply_async(
            kwargs={"since_iso": started_at.isoformat()},
            queue="alerts",
        )

    duration = (datetime.now(tz=timezone.utc) - started_at).total_seconds()
    log.info(
        "scrape_cycle_finished",
        total_found=total_found,
        total_new=total_new,
        duration_seconds=duration,
    )

    return {
        "started_at": started_at.isoformat(),
        "duration_seconds": duration,
        "total_found": total_found,
        "total_new": total_new,
        "per_scraper": results,
    }
