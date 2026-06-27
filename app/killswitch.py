"""
Central kill-switch for RealtorPal.

Set SYSTEM_PAUSED = False to re-activate the entire system.
"""

# ── MASTER SWITCH ─────────────────────────────────────────────────────────────
# True  → every bot interaction, API call, and background task is blocked.
# False → system operates normally.
SYSTEM_PAUSED = True

LICENSE_EXPIRED_MSG = (
    "⛔ <b>Service Unavailable</b>\n\n"
    "Your license has expired. Please contact support to renew access.\n\n"
    "<i>RealtorPal — Nigerian Property Scout</i>"
)

LICENSE_EXPIRED_API = {
    "detail": "Service unavailable. License expired. Please contact support."
}
