"""
UNMAPPED Telegram Bot

Primary user channel. Works on any phone, low bandwidth.
Handles: interview flow, voice input, passport display, peer vouching.

Run: python telegram_bot/bot.py
Requires: TELEGRAM_BOT_TOKEN in .env
"""

import asyncio
import logging
import os
import sys
from pathlib import Path


# Ensure project root is on path when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import certifi
from telegram.request import HTTPXRequest
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from backend.config_loader import get_config
from backend.models.db import init_db
from telegram_bot.handlers.interview_flow import (
    INTERVIEW,
    SETUP,
    cancel,
    handle_interview_message,
    setup_country,
    start_interview_command,
)
from telegram_bot.handlers.passport_view import show_passport, show_qr
from telegram_bot.handlers.readiness_view import show_readiness
from telegram_bot.handlers.voice_input import handle_voice
from telegram_bot.handlers.photo_handler import handle_photo, handle_document
from telegram_bot.handlers.checkin_handler import checkin_command, schedule_monthly_checkins
from telegram_bot.handlers.cv_handler import cv_command
from telegram_bot.handlers.skill_lookup import skill_lookup_command
from telegram_bot.handlers.peer_compare import compare_command
from telegram_bot.handlers.daily_pulse import (
    tip_command, subscribe_command, unsubscribe_command, schedule_daily_pulse
)
from telegram_bot.handlers.progress_handler import progress_command
from telegram_bot.handlers.negotiate_handler import negotiate_command
from telegram_bot.handlers.impact_handler import impact_command

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8000")
WEBAPP_URL = os.environ.get("WEBAPP_URL", f"{APP_BASE_URL}/webapp/passport.html")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = get_config()
    name = update.effective_user.first_name or "there"
    await update.message.reply_text(
        f"Hi {name}! I'm UNMAPPED.\n\n"
        f"I help you map the skills you already have — the ones that "
        f"the formal economy hasn't seen yet.\n\n"
        f"This is not a form. It's a conversation.\n\n"
        f"Commands:\n"
        f"/interview — start your skills interview\n"
        f"/passport — view your Skills Passport\n"
        f"/cv — generate your employer-ready CV\n"
        f"/readiness — automation risk calibrated for {cfg.country.name}\n"
        f"/skill <name> — look up any skill instantly\n"
        f"/compare — see how you rank vs similar workers\n"
        f"/tip — today's market insight for your sector\n"
        f"/subscribe — daily market pulse at 09:00 UTC\n"
        f"/negotiate — wage negotiation talking points\n"
        f"/progress — your passport journey + achievements\n"
        f"/impact — UNMAPPED's live impact numbers\n"
        f"/checkin — monthly passport check-in\n"
        f"/heritage — Heritage Skills\n"
        f"/qr — your QR code\n"
        f"/help — how this works\n\n"
        f"Country: {cfg.country.name} | Currency: {cfg.country.currency}"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "HOW UNMAPPED WORKS\n\n"
        "1. /interview — I ask you about your work. You answer naturally.\n"
        "   You can type or send a voice message.\n\n"
        "2. I extract your competencies and map them to a global skills taxonomy.\n"
        "   I also look for Heritage Skills — things like mobile money fluency,\n"
        "   repair-not-replace problem solving, and community trust networks.\n\n"
        "3. Your Skills Passport is generated — a portable, verifiable record\n"
        "   you own and can share with anyone.\n\n"
        "4. You can ask customers to verify your skills via SMS.\n"
        "   Each verification upgrades your receipt from 'self-reported' to 'peer-verified'.\n\n"
        "PRIVACY: Your Skills Passport belongs to you. UNMAPPED never shares it without permission.\n\n"
        "HONESTY: Every number we show you cites its source. Where data is uncertain, we say so."
    )


async def heritage_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from backend.modules.skills_signal.heritage_skills import HERITAGE_SKILLS
    lines = ["HERITAGE SKILLS\n", "Skills your community values that formal taxonomies miss:\n"]
    for hs in HERITAGE_SKILLS[:10]:
        emoji = {"critical": "★", "high": "◆", "medium": "●", "low": "○"}.get(hs.employer_value, "•")
        lines.append(f"{emoji} {hs.label}")
    lines.append(f"\n...and {len(HERITAGE_SKILLS) - 10} more.")
    lines.append("\nThese are recognized in your Skills Passport.")
    await update.message.reply_text("\n".join(lines))


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks (vouch confirmation, passport actions)."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""

    if data.startswith("vouch_confirm:"):
        token = data.split(":")[1]
        await _handle_vouch_confirm(query, token)
    elif data.startswith("passport_qr:"):
        passport_uuid = data.split(":")[1]
        context.user_data["passport_uuid"] = passport_uuid
        await show_qr(update, context)


async def _handle_vouch_confirm(query, token: str) -> None:
    """Demo vouch confirmation via button press."""
    import httpx
    api_base = os.environ.get("API_BASE_URL", "http://localhost:8000")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{api_base}/skills/vouch/{token}",
                json={"reply": "YES"},
            )
        if resp.status_code == 200:
            data = resp.json()
            await query.edit_message_text(
                f"Skill verified!\n\n"
                f"'{data.get('skill_label', 'Your skill')}' is now peer-verified.\n"
                f"This has been updated in your Skills Passport."
            )
        else:
            await query.edit_message_text("Verification failed. The token may have expired.")
    except Exception as exc:
        logger.error("Vouch confirm error: %s", exc)
        await query.edit_message_text("Verification service unavailable. Please try again.")



async def _post_init(application: Application) -> None:
    """Runs inside PTB's event loop after the bot is initialized."""
    await init_db()
    schedule_monthly_checkins(application)
    schedule_daily_pulse(application)
    cfg = get_config()
    logger.info(
        "UNMAPPED Telegram Bot ready | country=%s | token=%s...",
        cfg.country.name,
        TELEGRAM_BOT_TOKEN[:8] if TELEGRAM_BOT_TOKEN else "NOT SET",
    )


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN not set. Add it to .env."
        )

    request = HTTPXRequest(
        connect_timeout=60.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=60.0,
    )
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(request)
        .get_updates_request(request)
        .post_init(_post_init)
        .build()
    )

    # Interview conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("interview", start_interview_command)],
        states={
            SETUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_country)],
            INTERVIEW: [
                CommandHandler("interview", start_interview_command),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_interview_message),
                MessageHandler(filters.VOICE, handle_voice),
                MessageHandler(filters.PHOTO, handle_photo),
                MessageHandler(filters.Document.IMAGE, handle_document),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        persistent=False,
        allow_reentry=True,
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("heritage", heritage_command))
    application.add_handler(CommandHandler("passport", show_passport))
    application.add_handler(CommandHandler("qr", show_qr))
    application.add_handler(CommandHandler("readiness", show_readiness))
    application.add_handler(CommandHandler("checkin", checkin_command))
    application.add_handler(CommandHandler("cv", cv_command))
    application.add_handler(CommandHandler("skill", skill_lookup_command))
    application.add_handler(CommandHandler("compare", compare_command))
    application.add_handler(CommandHandler("tip", tip_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    application.add_handler(CommandHandler("progress", progress_command))
    application.add_handler(CommandHandler("negotiate", negotiate_command))
    application.add_handler(CommandHandler("impact", impact_command))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))

    cfg = get_config()
    logger.info(
        "UNMAPPED Telegram Bot starting | country=%s | token=%s...",
        cfg.country.name,
        TELEGRAM_BOT_TOKEN[:8],
    )

    # run_polling() manages its own event loop — do NOT wrap in asyncio.run()
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
