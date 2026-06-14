"""
Nigeria Property Centre scraper.

Target: https://nigeriapropertycentre.com
Terms: Please review their ToS before production deployment.
       Consider API/data partnership for long-term sustainability.

This scraper uses async Playwright + BeautifulSoup with polite delays.
"""

from __future__ import annotations

from bs4 import BeautifulSoup
from playwright.async_api import Browser

from app.logging_config import get_logger
from app.models.listing import City, PropertyType
from app.scrapers.base import BaseScraper
from app.schemas.listing import ListingData

log = get_logger(__name__)

CITY_PATHS: dict[str, City] = {
    "abuja": City.ABUJA,
    "lagos": City.LAGOS,
    "portharcourt": City.PORT_HARCOURT,
}

# Keywords found in scraped location strings → City enum
LOCATION_CITY_KEYWORDS: list[tuple[str, City]] = [
    ("abuja", City.ABUJA),
    ("lagos", City.LAGOS),
    ("port harcourt", City.PORT_HARCOURT),
    ("portharcourt", City.PORT_HARCOURT),
]


def _infer_city_from_location(location: str | None, fallback: City) -> City:
    """Return the City enum that matches a keyword in the location string.
    
    Falls back to `fallback` if no known city keyword is found.
    This prevents cross-city contamination when a site returns out-of-city results.
    """
    if not location:
        return fallback
    loc_lower = location.lower()
    for keyword, city_enum in LOCATION_CITY_KEYWORDS:
        if keyword in loc_lower:
            return city_enum
    return fallback

PROPERTY_TYPE_MAP: dict[str, PropertyType] = {
    "apartment": PropertyType.APARTMENT,
    "flat": PropertyType.FLAT,
    "duplex": PropertyType.DUPLEX,
    "detached": PropertyType.DETACHED_HOUSE,
    "terrace": PropertyType.TERRACE,
    "land": PropertyType.LAND,
    "commercial": PropertyType.COMMERCIAL,
}


class NigeriaPropertyCentreScraper(BaseScraper):
    """Scraper for nigeriapropertycentre.com."""

    @property
    def name(self) -> str:
        return "nigeriapropertycentre"

    @property
    def base_url(self) -> str:
        return "https://nigeriapropertycentre.com"

    async def scrape(self) -> list[ListingData]:
        log.info("scraper_started", scraper=self.name)
        try:
            return await self.run_with_playwright(self._scrape_all)
        except Exception as exc:
            log.error("scraper_fatal_error", scraper=self.name, error=str(exc))
            return []

    async def _scrape_all(self, browser: Browser) -> list[ListingData]:
        all_listings: list[ListingData] = []
        for city_slug, city_enum in CITY_PATHS.items():
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
        for page_num in range(1, 3):
            url = (
                f"{self.base_url}/properties-for-sale/{city_slug}"
                f"?page={page_num}"
            )
            html = await self._get_page_content(
                url, browser, wait_for_selector=".property-list"
            )
            if not html:
                break
            parsed = self._parse_page(html, city_enum)
            listings.extend(parsed)
            if not parsed:
                break
        return listings

    def _parse_page(self, html: str, city: City) -> list[ListingData]:
        soup = BeautifulSoup(html, "lxml")
        listings: list[ListingData] = []

        # Try multiple selectors since layouts can differ or change
        cards = (
            soup.select("div.property-list div.wp-block.property")
            or soup.select("div.property-list article")
            or soup.select("div.col-sm-6.col-md-4")
        )

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
        source_id = listing_url.rstrip("/").split("/")[-1] or href.split("/")[-2]

        title_tag = card.select_one("h4.content-title, h4, h3, [class*='title']")
        title = title_tag.get_text(strip=True) if title_tag else "Property Listing"

        # Robust price parsing from span.price tags
        price = None
        price_tags = card.select("span.price")
        for p_tag in price_tags:
            content = p_tag.get("content")
            if content and content != "NGN":
                price = self.parse_price(content)
                break
            txt = p_tag.get_text(strip=True)
            if txt and txt != "₦" and any(c.isdigit() for c in txt):
                price = self.parse_price(txt)
                break

        loc_tag = card.select_one("[class*='location'], address, small")
        location = loc_tag.get_text(strip=True) if loc_tag else None

        property_type = self._infer_type(title)

        # Parse bedrooms and bathrooms from aux-info list
        bedrooms = None
        bathrooms = None
        for li in card.select("ul.aux-info li"):
            text = li.get_text(strip=True).lower()
            if "bedroom" in text:
                bedrooms = self.parse_int(text)
            elif "bathroom" in text:
                bathrooms = self.parse_int(text)

        img_tag = card.select_one("img[src]")
        image_url = str(img_tag.get("src", "")) if img_tag else None

        # Override city with whatever the scraped location text actually says.
        # The site can return Lagos properties when we request the Abuja page.
        true_city = _infer_city_from_location(location, fallback=city)

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
            city=true_city,
            state=true_city.value.replace("_", " ").title(),
            listing_url=listing_url,
            image_url=image_url,
        )

    def _infer_type(self, text: str) -> PropertyType | None:
        text_lower = text.lower()
        for kw, pt in PROPERTY_TYPE_MAP.items():
            if kw in text_lower:
                return pt
        return None


from app.scrapers.registry import _registry  # noqa: E402

_registry["nigeriapropertycentre"] = NigeriaPropertyCentreScraper
