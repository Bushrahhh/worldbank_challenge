"""
Passport view handler — shows Skills Passport and QR code in Telegram.
"""

import logging
from typing import Optional

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

import os
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")


async def show_passport(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user's current Skills Passport."""
    telegram_id = str(update.effective_user.id)

    # Try to get passport for this user
    passport = await _get_user_passport(telegram_id)

    if not passport:
        await update.message.reply_text(
            "No Skills Passport yet.\n\n"
            "Use /interview to start your skills interview — "
            "it takes about 5 minutes."
        )
        return

    skills = passport.get("skills", [])
    passport_uuid = passport.get("passport_id", "")
    country = passport.get("country_iso", "")
    issued = passport.get("issued_at", "")[:10]

    if not skills:
        await update.message.reply_text(
            "Your interview isn't complete yet.\n"
            "Continue with /interview to finish capturing your skills."
        )
        return

    # Build the passport display
    heritage = [s for s in skills if s.get("is_heritage_skill")]
    peer_verified = [s for s in skills if s.get("evidence_type") == "peer_vouched"]
    lines = [
        "YOUR SKILLS PASSPORT",
        f"Issued: {issued} | Country: {country}",
        f"ID: {passport_uuid[:8]}...",
        "",
        f"{len(skills)} verified competencies:",
        "",
    ]

    for skill in skills:
        ev_type = skill.get("evidence_type", "self_report")
        ev_icon = {
            "self_report": "○",
            "peer_vouched": "●",
            "employer_verified": "★",
            "assessed": "◆",
        }.get(ev_type, "○")
        heritage_tag = " [Heritage]" if skill.get("is_heritage_skill") else ""
        lines.append(f"{ev_icon} {skill['skill_label']}{heritage_tag}")

    lines.append("")
    if heritage:
        lines.append(f"{len(heritage)} Heritage Skills — competencies the formal economy")
        lines.append("  often misses. Yours are now on record.")
    if peer_verified:
        lines.append(f"{len(peer_verified)} peer-verified skill(s)")
    lines.append("")
    lines.append("Legend: ○ self-reported  ● peer-verified  ★ employer-verified")

    keyboard = [
        [
            InlineKeyboardButton("Get QR Code", callback_data=f"passport_qr:{passport_uuid}"),
        ],
    ]

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_qr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the passport QR code as a PNG image."""
    # Get passport UUID from callback or user_data
    query = getattr(update, "callback_query", None)
    if query:
        passport_uuid = query.data.split(":")[1] if ":" in query.data else None
    else:
        passport_uuid = context.user_data.get("passport_uuid")

    if not passport_uuid:
        telegram_id = str(update.effective_user.id)
        passport = await _get_user_passport(telegram_id)
        if passport:
            passport_uuid = passport.get("passport_id")

    if not passport_uuid:
        msg = update.message or (query.message if query else None)
        if msg:
            await msg.reply_text(
                "No passport found. Complete your /interview first."
            )
        return

    # Fetch QR PNG from backend
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{API_BASE}/skills/passport/{passport_uuid}/qr")
            if resp.status_code == 200:
                png_bytes = resp.content
                msg = update.message or (query.message if query else None)
                if msg:
                    await msg.reply_photo(
                        photo=png_bytes,
                        caption=(
                            f"Your Skills Passport QR code\n"
                            f"ID: {passport_uuid[:12]}...\n\n"
                            f"Anyone can scan this to verify your skills.\n"
                            f"You own this — share it anywhere."
                        ),
                    )
                return
    except Exception as exc:
        logger.error("QR fetch failed: %s", exc)

    msg = update.message or (query.message if query else None)
    if msg:
        await msg.reply_text(
            f"QR generation failed. Your passport link:\n"
            f"{API_BASE}/passport/{passport_uuid}"
        )


async def _get_user_passport(telegram_id: str) -> Optional[dict]:
    """Fetch the most recent passport for a Telegram user."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # First get the user's passport UUID via a user lookup
            resp = await client.get(
                f"{API_BASE}/skills/passport/by_user/{telegram_id}"
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.error("Passport fetch for user %s failed: %s", telegram_id[:6], exc)
    return None
