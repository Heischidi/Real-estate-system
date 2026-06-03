"""Tests for BaseScraper utilities."""

from __future__ import annotations

import pytest

from app.scrapers.base import BaseScraper
from app.schemas.listing import ListingData


class DummyScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def base_url(self) -> str:
        return "https://example.com"

    async def scrape(self) -> list[ListingData]:
        return []


@pytest.mark.unit
class TestBaseScraper:
    def setup_method(self):
        self.scraper = DummyScraper()

    def test_parse_price_naira_symbol(self):
        assert self.scraper.parse_price("₦180,000,000") == 180_000_000

    def test_parse_price_plain_number(self):
        assert self.scraper.parse_price("5000000") == 5_000_000

    def test_parse_price_with_text(self):
        assert self.scraper.parse_price("N 25,000,000 / year") == 25_000_000

    def test_parse_price_none(self):
        assert self.scraper.parse_price(None) is None

    def test_parse_price_empty(self):
        assert self.scraper.parse_price("") is None

    def test_parse_price_no_digits(self):
        assert self.scraper.parse_price("Price on request") is None

    def test_parse_int_basic(self):
        assert self.scraper.parse_int("3 bedrooms") == 3

    def test_parse_int_none(self):
        assert self.scraper.parse_int(None) is None

    def test_parse_int_no_digits(self):
        assert self.scraper.parse_int("N/A") is None

    def test_normalize_url_absolute(self):
        url = "https://other.com/listing/123"
        assert self.scraper.normalize_url("https://example.com", url) == url

    def test_normalize_url_relative(self):
        result = self.scraper.normalize_url("https://example.com", "/listing/123")
        assert result == "https://example.com/listing/123"

    def test_scraper_name(self):
        assert self.scraper.name == "dummy"

    def test_cities_to_scrape_default(self):
        cities = self.scraper.cities_to_scrape
        assert "Abuja" in cities
        assert "Lagos" in cities
        assert len(cities) == 3

