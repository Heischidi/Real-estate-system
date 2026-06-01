"""Scrapers package init."""

from app.scrapers.base import BaseScraper, ScraperStats
from app.scrapers.registry import ScraperRegistry

__all__ = ["BaseScraper", "ScraperRegistry", "ScraperStats"]
