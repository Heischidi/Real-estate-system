"""Telegram inline keyboard builders."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CITIES = [
    ("🏛️ Abuja", "city:abuja"),
    ("🌊 Lagos", "city:lagos"),
    ("⚓ Port Harcourt", "city:port_harcourt"),
    ("🌾 Kano", "city:kano"),
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
