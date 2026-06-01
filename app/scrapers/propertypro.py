"""
PropertyPro Nigeria scraper.

Target: https://www.propertypro.ng
Terms: Please review https://www.propertypro.ng/terms before production use.
       Consider contacting PropertyPro for API/data partnership for sustainability.

Rate limiting: Uses BaseScraper delays (default 5s between requests).
"""

from __future__ import annotations

import asyncio
import re

from bs4 import BeautifulSoup
from playwright.async_api import Browser

from app.logging_config import get_logger
from app.models.listing import City, PropertyType
from app.scrapers.base import BaseScraper
from app.schemas.listing import ListingData

log = get_logger(__name__)

CITY_SLUGS: dict[str, City] = {
    "abuja": City.ABUJA,
    "lagos": City.LAGOS,
    "port-harcourt": City.PORT_HARCOURT,
}

PROPERTY_TYPE_MAP: dict[str, PropertyType] = {
    "apartment": PropertyType.APARTMENT,
    "flat": PropertyType.FLAT,
    "duplex": PropertyType.DUPLEX,
    "detached": PropertyType.DETACHED_HOUSE,
    "terrace": PropertyType.TERRACE,
    "land": PropertyType.LAND,
    "commercial": PropertyType.COMMERCIAL,
    "office": PropertyType.COMMERCIAL,
    "shop": PropertyType.COMMERCIAL,
}


class PropertyProScraper(BaseScraper):
    """Scraper adapter for propertypro.ng."""

    @property
    def name(self) -> str:
        return "propertypro"

    @property
    def base_url(self) -> str:
        return "https://www.propertypro.ng"

    async def scrape(self) -> list[ListingData]:
        """Entry point — scrapes all configured cities."""
        log.info("scraper_started", scraper=self.name)
        try:
            return await self.run_with_playwright(self._scrape_all_cities)
        except Exception as exc:
            log.error("scraper_fatal_error", scraper=self.name, error=str(exc))
            return []

    async def _scrape_all_cities(self, browser: Browser) -> list[ListingData]:
        all_listings: list[ListingData] = []

        for city_slug, city_enum in CITY_SLUGS.items():
            try:
                listings = await self._scrape_city(browser, city_slug, city_enum)
                all_listings.extend(listings)
                log.info(
                    "scraper_city_done",
                    scraper=self.name,
                    city=city_slug,
                    count=len(listings),
                )
            except Exception as exc:
                log.error(
                    "scraper_city_error",
                    scraper=self.name,
                    city=city_slug,
                    error=str(exc),
                )

        log.info("scraper_finished", scraper=self.name, total=len(all_listings))
        return all_listings

    async def _scrape_city(
        self, browser: Browser, city_slug: str, city_enum: City
    ) -> list[ListingData]:
        listings: list[ListingData] = []

        # Scrape first 2 pages per city (conservative — adjust as needed)
        for page_num in range(1, 3):
            url = f"{self.base_url}/property-for-sale/{city_slug}?page={page_num}"
            html = await self._get_page_content(
                url, browser, wait_for_selector=".listings-property"
            )
            if not html:
                break

            page_listings = self._parse_listings_page(html, city_enum)
            listings.extend(page_listings)

            if not page_listings:
                break  # No more results

        return listings

    def _parse_listings_page(self, html: str, city: City) -> list[ListingData]:
        soup = BeautifulSoup(html, "lxml")
        listings: list[ListingData] = []

        cards = soup.select("div.listings-property-item")
        if not cards:
            # Try alternative selector structure
            cards = soup.select("div.single-room-sale")

        for card in cards:
            try:
                listing = self._parse_card(card, city)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                log.warning("scraper_card_parse_error", scraper=self.name, error=str(exc))

        return listings

    def _parse_card(self, card: BeautifulSoup, city: City) -> ListingData | None:  # type: ignore[name-defined]
        # Extract listing URL and ID
        link_tag = card.select_one("a[href]")
        if not link_tag:
            return None

        href = link_tag.get("href", "")
        listing_url = self.normalize_url(self.base_url, str(href))

        # Extract source ID from URL slug
        source_id = listing_url.rstrip("/").split("/")[-1]
        if not source_id:
            return None

        # Title
        title_tag = card.select_one("h3, .listings-property-title, [class*='title']")
        title = title_tag.get_text(strip=True) if title_tag else "Property Listing"

        # Price
        price_tag = card.select_one("[class*='price'], .listings-price")
        raw_price = price_tag.get_text(strip=True) if price_tag else None
        price = self.parse_price(raw_price)

        # Location
        location_tag = card.select_one("[class*='location'], .listings-property-location")
        location = location_tag.get_text(strip=True) if location_tag else None

        # Property type from title/tag
        property_type = self._infer_property_type(title)

        # Bedrooms / bathrooms
        bed_tag = card.select_one("[class*='bed'], [class*='bedroom']")
        bath_tag = card.select_one("[class*='bath'], [class*='bathroom']")
        bedrooms = self.parse_int(bed_tag.get_text(strip=True) if bed_tag else None)
        bathrooms = self.parse_int(bath_tag.get_text(strip=True) if bath_tag else None)

        # Image
        img_tag = card.select_one("img[src]")
        image_url = str(img_tag.get("src", "")) if img_tag else None

        return ListingData(
            source=self.name,
            source_listing_id=source_id,
            title=title,
            price=price,
            currency="NGN",
            property_type=property_type,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            location=location,
            city=city,
            state=city.value.replace("_", " ").title() if city else None,
            listing_url=listing_url,
            image_url=image_url,
        )

    def _infer_property_type(self, text: str) -> PropertyType | None:
        text_lower = text.lower()
        for keyword, prop_type in PROPERTY_TYPE_MAP.items():
            if keyword in text_lower:
                return prop_type
        return None


# Self-register in the registry
from app.scrapers.registry import _registry  # noqa: E402

_registry["propertypro"] = PropertyProScraper
