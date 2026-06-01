"""
Scraper plugin registry — discovers and manages all scraper adapters.

To add a new scraper:
  1. Create a new file in app/scrapers/ that subclasses BaseScraper.
  2. Decorate the class with @ScraperRegistry.register  OR
     call ScraperRegistry.register_scraper(MyScraperClass) at module level.
  3. Import the module in this file's _autodiscover() call.

That's it — no other changes needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import get_settings
from app.logging_config import get_logger

if TYPE_CHECKING:
    from app.scrapers.base import BaseScraper

log = get_logger(__name__)
settings = get_settings()

_registry: dict[str, type["BaseScraper"]] = {}


class ScraperRegistry:
    """Central registry of all available scraper adapters."""

    @classmethod
    def register(cls, scraper_class: type["BaseScraper"]) -> type["BaseScraper"]:
        """Class decorator — register a scraper by its `name` property."""
        # Instantiate temporarily to get the name
        instance_name = scraper_class.name.fget(None)  # type: ignore[attr-defined]
        _registry[instance_name] = scraper_class
        log.debug("scraper_registered", name=instance_name)
        return scraper_class

    @classmethod
    def register_scraper(cls, scraper_class: type["BaseScraper"]) -> None:
        """Programmatic registration (alternative to decorator)."""
        # Create a temporary instance to read the name property
        try:
            tmp = object.__new__(scraper_class)
            name = scraper_class.name.fget(tmp)  # type: ignore[attr-defined]
            _registry[name] = scraper_class
            log.debug("scraper_registered", name=name)
        except Exception as exc:
            log.error("scraper_registration_failed", scraper=str(scraper_class), error=str(exc))

    @classmethod
    def get_all_scrapers(cls) -> list["BaseScraper"]:
        """Return instantiated scrapers, excluding any that are disabled."""
        disabled = set(settings.disabled_scrapers)
        scrapers = []
        for name, klass in _registry.items():
            if name in disabled:
                log.info("scraper_disabled", name=name)
                continue
            scrapers.append(klass())
        return scrapers

    @classmethod
    def get_scraper(cls, name: str) -> "BaseScraper | None":
        """Get a single scraper instance by name."""
        klass = _registry.get(name)
        return klass() if klass else None

    @classmethod
    def list_names(cls) -> list[str]:
        return list(_registry.keys())


def _autodiscover() -> None:
    """Import all scraper modules so they self-register."""
    import app.scrapers.nigeriapropertycentre  # noqa: F401
    import app.scrapers.privateproperty  # noqa: F401
    import app.scrapers.property24  # noqa: F401
    import app.scrapers.propertypro  # noqa: F401


_autodiscover()
