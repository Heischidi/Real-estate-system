"""Payment conversation handler for the Telegram bot."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from app.database import AsyncSessionLocal
from app.schemas.payment import PaymentCreate
from app.services.payment_service import PaymentService

PAYMENT_PLAN, PAYMENT_CONFIRM = range(2)

async def start_payment_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("Monthly Plan - $2 (₦3,000)", callback_data="pay_monthly_2_3000")],
        [InlineKeyboardButton("Yearly Plan - $20 (₦30,000)", callback_data="pay_yearly_20_30000")],
        [InlineKeyboardButton("Lifetime Plan - $200 (₦300,000)", callback_data="pay_lifetime_200_300000")],
        [InlineKeyboardButton("❌ Cancel", callback_data="pay_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "💎 *Upgrade to Premium*\n\n"
        "Free users are limited to 10 properties per search.\n"
        "Upgrade now to unlock unlimited access!\n\n"
        "Please select a subscription plan:"
    )
    
    if update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        await update.callback_query.answer()
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    return PAYMENT_PLAN

async def handle_payment_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "pay_cancel":
        await query.message.edit_text("Payment cancelled. You remain on the Free tier.")
        return ConversationHandler.END

    parts = query.data.split('_')
    plan = parts[1] # monthly, yearly, lifetime
    amount_usd = int(parts[2])
    amount_ngn = int(parts[3])

    context.user_data["payment_plan"] = plan
    context.user_data["payment_amount"] = amount_usd

    keyboard = [
        [InlineKeyboardButton("✅ I have made payment", callback_data="pay_confirm")],
        [InlineKeyboardButton("❌ Cancel", callback_data="pay_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"💳 *Make Transfer for {plan.capitalize()} Plan*\n\n"
        f"Amount: *₦{amount_ngn:,}* (${amount_usd})\n\n"
        f"*Bank:* Opay\n"
        f"*Account Number:* `9055576563`\n"
        f"*Account Name:* Chidiebere Ejikonye\n\n"
        "After transferring the exact amount, click the *I have made payment* button below. "
        "Our admin will verify and activate your Premium subscription shortly."
    )
    await query.message.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    return PAYMENT_CONFIRM

async def handle_payment_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "pay_cancel":
        await query.message.edit_text("Payment cancelled. You remain on the Free tier.")
        return ConversationHandler.END

    if query.data == "pay_confirm":
        telegram_id = update.effective_user.id
        plan = context.user_data.get("payment_plan", "monthly")
        amount = context.user_data.get("payment_amount", 2)

        async with AsyncSessionLocal() as db:
            service = PaymentService(db)
            await service.create_payment(
                PaymentCreate(
                    telegram_id=telegram_id,
                    plan=plan,
                    amount=amount,
                )
            )

        await query.message.edit_text(
            "✅ *Payment Claim Submitted!*\n\n"
            "Your payment is now pending verification by our team. "
            "Once approved, you will have unlimited Premium access.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

payment_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("upgrade", start_payment_flow),
        CallbackQueryHandler(start_payment_flow, pattern="^trigger_payment$")
    ],
    states={
        PAYMENT_PLAN: [
            CallbackQueryHandler(handle_payment_plan, pattern="^pay_(monthly|yearly|lifetime|cancel)")
        ],
        PAYMENT_CONFIRM: [
            CallbackQueryHandler(handle_payment_confirm, pattern="^pay_(confirm|cancel)$")
        ]
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)
