"""Tests for the scraper registry."""

from __future__ import annotations

import pytest

from app.scrapers.registry import ScraperRegistry, _registry


@pytest.mark.unit
class TestScraperRegistry:
    def test_all_scrapers_registered(self):
        names = ScraperRegistry.list_names()
        assert "propertypro" in names
        assert "nigeriapropertycentre" in names
        assert "privateproperty" in names
        assert "property24" in names

    def test_get_scraper_by_name(self):
        scraper = ScraperRegistry.get_scraper("propertypro")
        assert scraper is not None
        assert scraper.name == "propertypro"

    def test_get_nonexistent_scraper(self):
        scraper = ScraperRegistry.get_scraper("nonexistent")
        assert scraper is None

    def test_get_all_scrapers_returns_instances(self):
        scrapers = ScraperRegistry.get_all_scrapers()
        assert len(scrapers) >= 4
        for s in scrapers:
            assert hasattr(s, "name")
            assert hasattr(s, "scrape")

    def test_disabled_scraper_excluded(self, monkeypatch):
        from app.config import get_settings
        settings = get_settings()
        monkeypatch.setattr(settings, "disabled_scrapers", ["propertypro"])
        scrapers = ScraperRegistry.get_all_scrapers()
        names = [s.name for s in scrapers]
        assert "propertypro" not in names
