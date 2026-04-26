"""
Telegram interview flow handler.
Manages the ConversationHandler states for the AI skills interview.
"""

import logging
from typing import Optional

import httpx
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000"

# Conversation states
SETUP, INTERVIEW = range(2)


async def start_interview_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Entry point: /interview command."""
    cfg_resp = await _api_get("/config")
    country_name = cfg_resp.get("country", {}).get("name", "your country") if cfg_resp else "your country"

    context.user_data.clear()

    # Start interview immediately with the current country config
    session = await _api_post("/skills/interview/start", {
        "telegram_id": str(update.effective_user.id),
        "display_name": update.effective_user.first_name,
        "country_iso": None,  # uses active config
    })

    if not session:
        await update.message.reply_text(
            "Couldn't start the interview right now. Make sure the backend is running.\n"
            "Run: ACTIVE_COUNTRY=ghana uvicorn backend.main:app --reload"
        )
        return ConversationHandler.END

    context.user_data["session_id"] = session["session_id"]
    context.user_data["stage"] = session.get("stage", "greeting")
    context.user_data["skill_count"] = 0

    await update.message.reply_text(
        session["message"] + "\n\n"
        "_You can type your answer or send a voice note._",
        parse_mode="Markdown",
    )
    return INTERVIEW


async def setup_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle country selection (not currently used — auto-uses active config)."""
    return await start_interview_command(update, context)


async def handle_interview_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Process a text message during the interview."""
    session_id = context.user_data.get("session_id")
    if not session_id:
        await update.message.reply_text("No active interview. Use /interview to start.")
        return ConversationHandler.END

    user_text = update.message.text
    stage = context.user_data.get("stage", "greeting")

    # Show typing indicator
    await update.message.chat.send_action("typing")

    resp = await _api_post("/skills/interview/message", {
        "session_id": session_id,
        "message": user_text,
        "stage": stage,
    })

    if not resp:
        await update.message.reply_text(
            "Interview service unavailable. Your progress is saved — type anything to continue."
        )
        return INTERVIEW

    context.user_data["stage"] = resp.get("stage", stage)
    skills_found = resp.get("extracted_skills_count", 0)
    if skills_found:
        context.user_data["skill_count"] = context.user_data.get("skill_count", 0) + skills_found

    message = resp.get("message", "")
    skill_count = context.user_data.get("skill_count", 0)

    # Add subtle skill counter as context
    footer = ""
    if skill_count > 0 and not resp.get("complete"):
        footer = f"\n\n_{skill_count} skill{'s' if skill_count != 1 else ''} captured so far_"

    await update.message.reply_text(message + footer, parse_mode="Markdown")

    if resp.get("complete"):
        await _send_passport_preview(update, context)
        return ConversationHandler.END

    return INTERVIEW


async def _send_passport_preview(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a passport preview with action buttons after interview completes."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    telegram_id = str(update.effective_user.id)

    # Fetch the user's passport
    passport_resp = await _api_get(f"/skills/passport/by_user/{telegram_id}")

    if not passport_resp:
        await update.message.reply_text(
            "Your Skills Passport has been created!\n"
            "Use /passport to view it and /qr for your shareable QR code."
        )
        return

    passport_uuid = passport_resp.get("passport_id", "")
    skills = passport_resp.get("skills", [])
    heritage = [s for s in skills if s.get("is_heritage_skill")]

    lines = [
        "YOUR SKILLS PASSPORT IS READY",
        "",
        f"{len(skills)} competencies captured",
    ]
    if heritage:
        lines.append(f"{len(heritage)} Heritage Skills recognized")
    lines.append("")
    for s in skills[:4]:
        ev = s.get("evidence_type", "self_report").replace("_", " ")
        lines.append(f"✓ {s['skill_label']} ({ev})")
    if len(skills) > 4:
        lines.append(f"...and {len(skills) - 4} more")

    keyboard = [
        [InlineKeyboardButton("View Full Passport", callback_data=f"passport_qr:{passport_uuid}")],
    ]

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    context.user_data["passport_uuid"] = passport_uuid


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Interview paused. Your progress is saved.\n"
        "Use /interview to continue or /passport to see what's been captured so far."
    )
    return ConversationHandler.END


# ── API helpers ───────────────────────────────────────────────────────────────

async def _api_post(path: str, data: dict) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{API_BASE}{path}", json=data)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("API POST %s returned %s: %s", path, resp.status_code, resp.text[:100])
    except Exception as exc:
        logger.error("API POST %s failed: %s", path, exc)
    return None


async def _api_get(path: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{API_BASE}{path}")
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.error("API GET %s failed: %s", path, exc)
    return None
