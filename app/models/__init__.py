"""Models package — import all models here so Alembic can discover them."""

from app.models.listing import City, Listing, PropertyType
from app.models.notification import Notification
from app.models.subscriber import Subscriber

__all__ = [
    "City",
    "Listing",
    "Notification",
    "PropertyType",
    "Subscriber",
]
