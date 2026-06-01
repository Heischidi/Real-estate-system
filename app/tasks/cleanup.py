"""Celery cleanup tasks."""

from __future__ import annotations

import asyncio

from app.logging_config import get_logger
from app.tasks.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(
    name="app.tasks.cleanup.cleanup_old_notifications",
    bind=True,
    max_retries=2,
)
def cleanup_old_notifications(self: object) -> dict[str, object]:
    """Remove notification records older than the configured retention period."""
    return asyncio.run(_async_cleanup())


async def _async_cleanup() -> dict[str, object]:
    from app.config import get_settings
    from app.database import get_db_context
    from app.services.alert_service import AlertService

    settings = get_settings()
    async with get_db_context() as db:
        alert_service = AlertService(db)
        deleted = await alert_service.delete_old_notifications(
            older_than_days=settings.notification_retention_days
        )
    return {"deleted_notifications": deleted}
