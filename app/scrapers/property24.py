"""
Property24 Nigeria scraper.

Target: https://www.property24.com.ng
Terms: Please review their ToS before production use.
"""

from __future__ import annotations

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
    "kano": City.KANO,
}

PROPERTY_TYPE_MAP: dict[str, PropertyType] = {
    "apartment": PropertyType.APARTMENT,
    "flat": PropertyType.FLAT,
    "duplex": PropertyType.DUPLEX,
    "detached": PropertyType.DETACHED_HOUSE,
    "terrace": PropertyType.TERRACE,
    "land": PropertyType.LAND,
    "commercial": PropertyType.COMMERCIAL,
}


class Property24Scraper(BaseScraper):
    """Scraper for property24.com.ng."""

    @property
    def name(self) -> str:
        return "property24"

    @property
    def base_url(self) -> str:
        return "https://www.property24.com.ng"

    async def scrape(self) -> list[ListingData]:
        log.info("scraper_started", scraper=self.name)
        try:
            return await self.run_with_playwright(self._scrape_all)
        except Exception as exc:
            log.error("scraper_fatal_error", scraper=self.name, error=str(exc))
            return []

    async def _scrape_all(self, browser: Browser) -> list[ListingData]:
        all_listings: list[ListingData] = []
        for city_slug, city_enum in CITY_SLUGS.items():
            try:
                result = await self._scrape_city(browser, city_slug, city_enum)
                all_listings.extend(result)
                log.info("scraper_city_done", scraper=self.name, city=city_slug, count=len(result))
            except Exception as exc:
                log.error("scraper_city_error", scraper=self.name, city=city_slug, error=str(exc))
        log.info("scraper_finished", scraper=self.name, total=len(all_listings))
        return all_listings

    async def _scrape_city(self, browser: Browser, city_slug: str, city_enum: City) -> list[ListingData]:
        listings: list[ListingData] = []
        for page_num in range(1, 3):
            url = f"{self.base_url}/to-buy/{city_slug}?Page={page_num}"
            html = await self._get_page_content(url, browser, wait_for_selector=".p24_results")
            if not html:
                break
            parsed = self._parse_page(html, city_enum)
            listings.extend(parsed)
            if not parsed:
                break
        return listings

    def _parse_page(self, html: str, city: City) -> list[ListingData]:
        soup = BeautifulSoup(html, "lxml")
        cards = (
            soup.select("div.p24_regularTile")
            or soup.select("div.p24_content")
            or soup.select("div[class*='tile']")
        )
        listings = []
        for card in cards:
            try:
                listing = self._parse_card(card, city)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                log.warning("scraper_card_error", scraper=self.name, error=str(exc))
        return listings

    def _parse_card(self, card: BeautifulSoup, city: City) -> ListingData | None:  # type: ignore[name-defined]
        link_tag = card.select_one("a[href]")
        if not link_tag:
            return None
        href = str(link_tag.get("href", ""))
        listing_url = self.normalize_url(self.base_url, href)
        source_id = listing_url.rstrip("/").split("/")[-1]
        if not source_id:
            return None

        title_tag = card.select_one("span.p24_title, h2, [class*='title']")
        title = title_tag.get_text(strip=True) if title_tag else "Property Listing"

        price_tag = card.select_one("span.p24_price, [class*='price']")
        price = self.parse_price(price_tag.get_text(strip=True) if price_tag else None)

        loc_tag = card.select_one("span.p24_address, [class*='address']")
        location = loc_tag.get_text(strip=True) if loc_tag else None

        property_type = self._infer_type(title)

        bedrooms: int | None = None
        bathrooms: int | None = None
        for tag in card.select("span[title]"):
            title_attr = str(tag.get("title", "")).lower()
            val = self.parse_int(tag.get_text(strip=True))
            if "bed" in title_attr:
                bedrooms = val
            elif "bath" in title_attr:
                bathrooms = val

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
            state=city.value.replace("_", " ").title(),
            listing_url=listing_url,
            image_url=image_url,
        )

    def _infer_type(self, text: str) -> PropertyType | None:
        tl = text.lower()
        for kw, pt in PROPERTY_TYPE_MAP.items():
            if kw in tl:
                return pt
        return None


from app.scrapers.registry import _registry  # noqa: E402
_registry["property24"] = Property24Scraper
