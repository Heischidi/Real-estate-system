"""
BaseScraper — abstract foundation for all Nigerian property scrapers.

Design principles:
- Respect rate limits (configurable delay between requests)
- Retry with exponential backoff on transient failures
- Rotate User-Agent headers to avoid trivial blocks
- Check robots.txt before scraping (best-effort)
- NEVER hammer a site — be a good citizen of the web
"""

from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from fake_useragent import UserAgent
from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.logging_config import get_logger
from app.schemas.listing import ListingData

log = get_logger(__name__)
settings = get_settings()

_ua = UserAgent()


@dataclass
class ScraperStats:
    """Runtime statistics collected during a scrape run."""

    scraper_name: str
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    finished_at: datetime | None = None
    listings_found: int = 0
    listings_new: int = 0
    pages_scraped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


class BaseScraper(ABC):
    """
    Abstract base class for all property scrapers.

    Subclasses must implement:
        - name: str property
        - base_url: str property
        - async scrape() -> list[ListingData]
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this scraper (snake_case)."""
        ...

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Root URL of the target website."""
        ...

    @property
    def cities_to_scrape(self) -> list[str]:
        """City search terms — subclasses may override."""
        return ["Abuja", "Lagos", "Port Harcourt", "Kano"]

    @abstractmethod
    async def scrape(self) -> list[ListingData]:
        """
        Main scrape entry point.
        Must return a list of ListingData (may be empty on failure).
        Must NOT raise — catch all errors internally and log them.
        """
        ...

    # -------------------------------------------------------------------------
    # Robots.txt helper
    # -------------------------------------------------------------------------

    async def is_allowed_by_robots(self, url: str) -> bool:
        """Check robots.txt — returns True if we're allowed to scrape."""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(robots_url)
            if resp.status_code != 200:
                return True  # No robots.txt — assume allowed
            rp = RobotFileParser()
            rp.parse(resp.text.splitlines())
            allowed: bool = rp.can_fetch("*", url)
            return allowed
        except Exception as exc:
            log.warning("robots_txt_check_failed", url=url, error=str(exc))
            return True  # Fail open — assume allowed

    # -------------------------------------------------------------------------
    # Playwright helpers
    # -------------------------------------------------------------------------

    async def _get_page_content(
        self,
        url: str,
        browser: Browser,
        wait_for_selector: str | None = None,
        extra_wait_ms: int = 1500,
    ) -> str | None:
        """
        Load a URL with Playwright and return the rendered HTML.
        Includes random delay, UA rotation, and retry logic.
        """
        context: BrowserContext | None = None
        page: Page | None = None
        try:
            ua = _ua.random
            context = await browser.new_context(
                user_agent=ua,
                viewport={"width": 1280, "height": 900},
                locale="en-GB",
                timezone_id="Africa/Lagos",
                java_script_enabled=True,
                ignore_https_errors=True,
            )
            page = await context.new_page()

            # Throttle requests — be polite
            delay = settings.scraper_request_delay_seconds + random.uniform(0.5, 2.5)
            await asyncio.sleep(delay)

            log.debug("scraper_fetching", scraper=self.name, url=url)
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

            if wait_for_selector:
                try:
                    await page.wait_for_selector(
                        wait_for_selector, timeout=10_000
                    )
                except Exception:
                    pass  # Selector didn't appear — proceed with what we have

            await page.wait_for_timeout(extra_wait_ms)
            return await page.content()

        except Exception as exc:
            log.error("scraper_page_load_failed", scraper=self.name, url=url, error=str(exc))
            return None
        finally:
            if page:
                await page.close()
            if context:
                await context.close()

    async def run_with_playwright(
        self, scrape_fn: Any, *args: Any, **kwargs: Any
    ) -> list[ListingData]:
        """Run `scrape_fn(browser, *args, **kwargs)` inside a Playwright context."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=settings.playwright_headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            try:
                return await scrape_fn(browser, *args, **kwargs)
            finally:
                await browser.close()

    # -------------------------------------------------------------------------
    # Parsing helpers (shared utilities for subclasses)
    # -------------------------------------------------------------------------

    @staticmethod
    def parse_price(raw: str | None) -> int | None:
        """Extract a numeric price from a string like '₦180,000,000'."""
        if not raw:
            return None
        digits = "".join(c for c in raw if c.isdigit())
        return int(digits) if digits else None

    @staticmethod
    def parse_int(raw: str | None) -> int | None:
        """Parse a small integer from a string."""
        if not raw:
            return None
        digits = "".join(c for c in raw if c.isdigit())
        return int(digits) if digits else None

    @staticmethod
    def normalize_url(base: str, href: str) -> str:
        """Join a relative href to a base URL."""
        if href.startswith("http"):
            return href
        return urljoin(base, href)
