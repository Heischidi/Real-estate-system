"""Celery application and Beat schedule configuration."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "nigeria_realestate",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.scrape",
        "app.tasks.alerts",
        "app.tasks.cleanup",
    ],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="Africa/Lagos",
    enable_utc=True,
    # Task behavior
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_soft_time_limit=600,   # 10 min soft limit
    task_time_limit=900,        # 15 min hard kill
    # Worker
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    # Results
    result_expires=3600,
    # Beat schedule
    beat_schedule={
        "scrape-all-sources": {
            "task": "app.tasks.scrape.scrape_all_sources",
            "schedule": crontab(minute=f"*/{settings.scrape_interval_minutes}"),
            "options": {"queue": "scraping"},
        },
        "cleanup-old-notifications": {
            "task": "app.tasks.cleanup.cleanup_old_notifications",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM Lagos time
            "options": {"queue": "default"},
        },
    },
    task_routes={
        "app.tasks.scrape.*": {"queue": "scraping"},
        "app.tasks.alerts.*": {"queue": "alerts"},
        "app.tasks.cleanup.*": {"queue": "default"},
    },
)
