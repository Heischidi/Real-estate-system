"""Telegram inline keyboard builders."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CITIES = [
    ("🏛️ Abuja", "city:abuja"),
    ("🌊 Lagos", "city:lagos"),
    ("⚓ Port Harcourt", "city:port_harcourt"),
]

PROPERTY_TYPES = [
    ("🏢 Apartment", "type:apartment"),
    ("🏠 Flat", "type:flat"),
    ("🏘️ Duplex", "type:duplex"),
    ("🏡 Detached House", "type:detached_house"),
    ("🏘️ Terrace", "type:terrace"),
    ("🌍 Land", "type:land"),
    ("🏪 Commercial", "type:commercial"),
]


def city_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for city selection."""
    buttons = [
        [InlineKeyboardButton(label, callback_data=data)]
        for label, data in CITIES
    ]
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


def property_type_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for property type selection (2 per row)."""
    pairs = [
        PROPERTY_TYPES[i : i + 2] for i in range(0, len(PROPERTY_TYPES), 2)
    ]
    buttons = [
        [InlineKeyboardButton(label, callback_data=data) for label, data in pair]
        for pair in pairs
    ]
    buttons.append([InlineKeyboardButton("⏩ Any Type", callback_data="type:any")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


def confirm_keyboard() -> InlineKeyboardMarkup:
    """Yes/No confirmation keyboard."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Yes, Save", callback_data="confirm:yes"),
                InlineKeyboardButton("✏️ Edit Again", callback_data="confirm:no"),
            ]
        ]
    )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔔 Subscribe", callback_data="menu:subscribe")],
            [InlineKeyboardButton("⚙️ My Settings", callback_data="menu:settings")],
            [InlineKeyboardButton("🔕 Unsubscribe", callback_data="menu:unsubscribe")],
            [InlineKeyboardButton("🏙️ Available Cities", callback_data="menu:cities")],
        ]
    )


def start_city_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting a city upon /start."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🏛️ Abuja", callback_data="start_city:abuja")],
            [InlineKeyboardButton("🌊 Lagos", callback_data="start_city:lagos")],
            [InlineKeyboardButton("⚓ Port Harcourt", callback_data="start_city:port_harcourt")],
        ]
    )


def after_listings_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown after displaying the last page of listings."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔔 Subscribe for Alerts", callback_data="menu:subscribe")],
            [InlineKeyboardButton("🔙 Back to Cities", callback_data="back_to_cities")],
        ]
    )


def load_more_keyboard(city_code: str, next_page: int) -> InlineKeyboardMarkup:
    """Keyboard shown mid-listing to offer loading the next page."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(
                f"⬇️ Load More",
                callback_data=f"load_more:{city_code}:{next_page}",
            )],
            [InlineKeyboardButton("🔔 Subscribe for Alerts", callback_data="menu:subscribe")],
            [InlineKeyboardButton("🔙 Back to Cities", callback_data="back_to_cities")],
        ]
    )
