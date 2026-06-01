"""Prometheus metrics setup for FastAPI."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

# Scraper metrics
scraper_runs_total = Counter(
    "scraper_runs_total",
    "Total number of scraper runs",
    ["scraper_name", "status"],
)
scraper_listings_found = Counter(
    "scraper_listings_found_total",
    "Total listings found by scraper",
    ["scraper_name"],
)
scraper_listings_new = Counter(
    "scraper_listings_new_total",
    "New listings saved to database",
    ["scraper_name"],
)
scraper_duration_seconds = Histogram(
    "scraper_duration_seconds",
    "Time taken per scraper run",
    ["scraper_name"],
)

# Alert metrics
alerts_sent_total = Counter(
    "alerts_sent_total",
    "Total Telegram alerts sent",
)
alerts_failed_total = Counter(
    "alerts_failed_total",
    "Total failed Telegram alert attempts",
)

# Subscriber metrics
subscribers_active = Gauge(
    "subscribers_active_total",
    "Number of active subscribers",
)

# Database metrics
db_errors_total = Counter(
    "db_errors_total",
    "Total database errors",
    ["operation"],
)


def setup_metrics(app: object) -> None:
    """Attach Prometheus instrumentation to the FastAPI app."""
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health"],
        env_var_name="METRICS_ENABLED",
    ).instrument(app).expose(app, endpoint="/metrics")  # type: ignore[arg-type]
