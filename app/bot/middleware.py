"""Bot middleware and helper functions."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from app.config import get_settings
from app.logging_config import get_logger

log = get_logger(__name__)

async def enforce_community_membership(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Checks if the user is a member of the required community channel.
    If not, it sends a message prompting them to join and returns False.
    If they are a member, returns True.
    """
    settings = get_settings()
    channel_username = settings.community_channel_username

    if not channel_username:
        # If no community is configured, bypass the check
        return True

    user = update.effective_user
    if not user:
        return True

    try:
        member = await context.bot.get_chat_member(
            chat_id=channel_username, user_id=user.id
        )
        if member.status in ["left", "kicked"]:
            is_member = False
        else:
            is_member = True
    except TelegramError as e:
        log.warning(
            "Could not check membership for user %s in channel %s: %s",
            user.id,
            channel_username,
            e,
        )
        # If the bot is not an admin or the channel is invalid, we fail open
        # or fail closed. To avoid breaking the bot for everyone if the admin
        # makes a typo, we could bypass. But the client explicitly wants a forced join.
        # Let's fail closed if it's a known error, but let's assume False for now.
        is_member = False

    if not is_member:
        # Create a link without the '@' symbol
        clean_username = channel_username.lstrip("@")
        invite_link = f"https://t.me/{clean_username}"

        keyboard = [
            [InlineKeyboardButton("🔗 Join Community", url=invite_link)],
            [InlineKeyboardButton("✅ I Have Joined", callback_data="check_membership")],
        ]
        text = (
            "🔒 <b>Community Access Required</b>\n\n"
            "To use this bot, you must be a member of our official community channel!\n\n"
            "Please join using the button below, then click <b>I Have Joined</b> to unlock the bot."
        )

        if update.callback_query:
            await update.callback_query.message.reply_html(
                text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif update.message:
            await update.message.reply_html(
                text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        return False

    return True
