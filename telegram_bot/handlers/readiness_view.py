"""
Readiness Lens — Telegram handlers

Sends a formatted Readiness summary in-chat (no web app required)
and offers a button to open the full Readiness Lens web app.
"""

import logging
import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

API_BASE    = "http://localhost:8000"
WEBAPP_BASE = "http://localhost:8000/webapp"


async def show_readiness(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /readiness command — fetch the user's readiness profile and summarise it in-chat.
    """
    tg_id = str(update.effective_user.id)

    await update.message.reply_text("Calculating your Readiness Lens...")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            # Get passport UUID for this user
            resp = await client.get(f"{API_BASE}/skills/passport/by_user/{tg_id}")
            if resp.status_code == 404:
                await update.message.reply_text(
                    "You don't have a Skills Passport yet.\n\n"
                    "Use /interview first — the Readiness Lens works from your passport."
                )
                return
            if resp.status_code != 200:
                raise Exception(f"Passport API error {resp.status_code}")

            passport = resp.json()
            passport_uuid = passport["passport_id"]

            # Get full readiness profile
            r2 = await client.get(f"{API_BASE}/readiness/profile/{passport_uuid}")
            if r2.status_code != 200:
                raise Exception(f"Readiness API error {r2.status_code}")
            profile = r2.json()

    except Exception as exc:
        logger.error("Readiness error for user %s: %s", tg_id, exc)
        await update.message.reply_text(
            "Readiness service unavailable. Make sure the backend is running."
        )
        return

    cal   = profile.get("headline_calibration", {})
    risk  = profile.get("risk_profile", {})
    wthr  = profile.get("weather", {})
    stars = profile.get("constellation", {}).get("summary", {})

    tier_emoji = {
        "low":      "☀️",
        "medium":   "⛅",
        "high":     "🌦️",
        "critical": "⛈️",
    }.get(cal.get("risk_tier", "medium"), "⛅")

    lines = [
        f"READINESS LENS — {profile.get('country', '')}",
        "",
        f"{tier_emoji} {cal.get('risk_tier_label', 'Watchful')}",
        f"Dominant occupation: {cal.get('occupation_label', 'Unknown')}",
        "",
        "CALIBRATION",
        f"  US baseline:  {cal.get('baseline_pct', '?')}%",
        f"  After infra:  {cal.get('infrastructure_adjusted_pct', '?')}%",
        f"  Local reality:{cal.get('calibrated_pct', '?')}%",
        "",
        "YOUR PASSPORT",
        f"  Total skills: {risk.get('total_skills', 0)}",
        f"  Heritage:     {risk.get('heritage_count', 0)}",
        f"  Durable (<30% risk): {risk.get('durable_skills', 0)}",
        f"  Overall risk: {risk.get('overall_risk_pct', '?')}%",
        "",
    ]

    protective = cal.get("protective_skills", [])[:3]
    if protective:
        lines.append("PROTECTS YOU")
        for p in protective:
            lines.append(f"  + {p}")
        lines.append("")

    lines.append("Source: Frey & Osborne (2013) + local calibration.")
    lines.append("Uncertainty ±15%.")

    webapp_url = f"{WEBAPP_BASE}/readiness.html?id={passport_uuid}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "Open Readiness Lens",
            web_app=WebAppInfo(url=webapp_url),
        )],
        [InlineKeyboardButton(
            "View Time Machine 2035",
            web_app=WebAppInfo(url=webapp_url + "#timemachine"),
        )],
    ])

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=keyboard,
    )
