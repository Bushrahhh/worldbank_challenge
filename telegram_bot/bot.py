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
        f"/readiness — Readiness Lens (automation risk calibrated for {cfg.country.name})\n"
        f"/qr — get your QR code\n"
        f"/heritage — see Heritage Skills\n"
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
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"http://localhost:8000/skills/vouch/{token}",
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


def build_application() -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN not set. "
            "Add it to .env: TELEGRAM_BOT_TOKEN=your_bot_token_here\n"
            "Get a token from @BotFather on Telegram."
        )

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Interview conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("interview", start_interview_command)],
        states={
            SETUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_country)],
            INTERVIEW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_interview_message),
                MessageHandler(filters.VOICE, handle_voice),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        persistent=False,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("heritage", heritage_command))
    app.add_handler(CommandHandler("passport", show_passport))
    app.add_handler(CommandHandler("qr", show_qr))
    app.add_handler(CommandHandler("readiness", show_readiness))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_callback))

    return app


async def main():
    await init_db()
    application = build_application()
    cfg = get_config()
    logger.info(
        "UNMAPPED Telegram Bot starting | country=%s | token=%s...",
        cfg.country.name,
        TELEGRAM_BOT_TOKEN[:8] if TELEGRAM_BOT_TOKEN else "NOT SET",
    )
    await application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
