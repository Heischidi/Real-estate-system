"""Telegram message formatters for property alert messages."""

from __future__ import annotations

from app.models.listing import Listing, PropertyType

PROPERTY_TYPE_EMOJI: dict[str, str] = {
    "apartment": "🏢",
    "flat": "🏠",
    "duplex": "🏘️",
    "detached_house": "🏡",
    "terrace": "🏘️",
    "land": "🌍",
    "commercial": "🏪",
}

CITY_DISPLAY: dict[str, str] = {
    "abuja": "Abuja",
    "lagos": "Lagos",
    "port_harcourt": "Port Harcourt",
}


def format_price(price: int | None, currency: str = "NGN") -> str:
    """Format a price integer into human-readable Naira notation."""
    if price is None:
        return "Price on request"
    symbol = "₦" if currency == "NGN" else currency
    if price >= 1_000_000_000:
        return f"{symbol}{price / 1_000_000_000:.1f}B"
    if price >= 1_000_000:
        return f"{symbol}{price / 1_000_000:.1f}M"
    if price >= 1_000:
        return f"{symbol}{price / 1_000:.0f}K"
    return f"{symbol}{price:,}"


def format_listing_alert(listing: Listing) -> str:
    """Format a Listing object into a Telegram HTML alert message."""
    prop_type = listing.property_type or "property"
    prop_type_str = (
        prop_type.value if hasattr(prop_type, "value") else str(prop_type)
    )
    emoji = PROPERTY_TYPE_EMOJI.get(prop_type_str, "🏠")

    bedrooms_str = ""
    if listing.bedrooms is not None:
        bedrooms_str = f"\n🛏 <b>Bedrooms:</b> {listing.bedrooms}"

    bathrooms_str = ""
    if listing.bathrooms is not None:
        bathrooms_str = f"\n🚿 <b>Bathrooms:</b> {listing.bathrooms}"

    toilets_str = ""
    if listing.toilets is not None:
        toilets_str = f"\n🚽 <b>Toilets:</b> {listing.toilets}"

    location_str = ""
    if listing.location:
        location_str = listing.location
    
    city_val = listing.city.value if hasattr(listing.city, "value") else str(listing.city or "")
    city_display = CITY_DISPLAY.get(city_val.lower() if city_val else "", "")
    # Only append city if it's not already present in the scraped location string
    city_already_in_location = (
        city_display and location_str and city_display.lower() in location_str.lower()
    )
    if city_display and location_str and not city_already_in_location:
        full_location = f"{location_str}, {city_display}"
    elif city_display and not location_str:
        full_location = city_display
    else:
        full_location = location_str or "Nigeria"

    agent_str = ""
    if listing.agent_name:
        agent_str = f"\n👤 <b>Agent:</b> {listing.agent_name}"
    if listing.agent_phone:
        agent_str += f"\n📞 <b>Phone:</b> {listing.agent_phone}"

    title_display = listing.title[:80] + ("..." if len(listing.title) > 80 else "")
    price_display = format_price(listing.price, listing.currency)
    type_display = prop_type_str.replace("_", " ").title()

    return (
        f"{emoji} <b>{title_display}</b>\n\n"
        f"📍 <b>Location:</b> {full_location}\n"
        f"🏷️ <b>Type:</b> {type_display}\n"
        f"💰 <b>Price:</b> {price_display}"
        f"{bedrooms_str}"
        f"{bathrooms_str}"
        f"{toilets_str}"
        f"{agent_str}\n\n"
        f"<i>📡 via {listing.source.replace('_', ' ').title()}</i>"
    )


def format_settings_summary(subscriber: object) -> str:
    """Format a subscriber's current settings for display."""
    from app.models.subscriber import Subscriber

    sub: Subscriber = subscriber  # type: ignore[assignment]

    city = CITY_DISPLAY.get(sub.city.value if sub.city else "", "Any")
    prop_type = (
        sub.property_type.value.replace("_", " ").title()
        if sub.property_type
        else "Any"
    )
    min_price = format_price(sub.min_price) if sub.min_price else "No minimum"
    max_price = format_price(sub.max_price) if sub.max_price else "No maximum"
    status = "✅ Active" if sub.active else "❌ Paused"

    return (
        f"⚙️ <b>Your Alert Settings</b>\n\n"
        f"🏙️ <b>City:</b> {city}\n"
        f"🏠 <b>Property Type:</b> {prop_type}\n"
        f"💵 <b>Min Budget:</b> {min_price}\n"
        f"💵 <b>Max Budget:</b> {max_price}\n"
        f"📡 <b>Status:</b> {status}"
    )
