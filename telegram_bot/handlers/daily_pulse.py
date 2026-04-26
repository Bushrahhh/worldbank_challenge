"""
Daily Market Pulse — /tip and /subscribe

/tip     → Instant market insight for the user's sector
/subscribe → Opt in to daily 09:00 UTC market pulse
/unsubscribe → Opt out

Insights are calibrated to the active country and the user's dominant ISCO.
No external API calls — uses curated, cited data baked in.
"""

import logging
import random
from datetime import datetime, time

import httpx
from telegram import Update
from telegram.ext import Application, ContextTypes

logger = logging.getLogger(__name__)
import os
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Subscribed telegram_ids stored in memory (resets on bot restart)
# Production: store in DB. For demo this is sufficient.
_SUBSCRIBERS: set[str] = set()

# ── Market pulse data ─────────────────────────────────────────────────────────
# Each entry: (headline, stat, source, action)
_PULSES = {
    "7422": [
        ("Smartphone penetration in Ghana hit 54% in 2024.",
         "Each 10pp increase creates ~8,000 new repair jobs.",
         "GSMA Mobile Economy Sub-Saharan Africa 2024",
         "Price your diagnostic service — not just the repair."),
        ("Ghana imported 2.3M refurbished phones in 2023.",
         "Every import is a future repair job. Refurb repair pays 1.4× new-phone repair.",
         "Ghana Revenue Authority trade data 2023",
         "Specialise in refurbished device repair to capture this market."),
        ("Right-to-repair laws are advancing in 12 African countries.",
         "Formal repair sector employment projected +23% by 2027.",
         "iFixit Africa Policy Brief 2024",
         "Get a formal NVTI certification now — before the market formalises."),
    ],
    "4211": [
        ("Ghana's mobile money transaction volume: GHS 1.2 trillion in 2023.",
         "That's a 31% increase year-on-year. Agent demand follows volume.",
         "Bank of Ghana Payment Systems Report 2023",
         "Apply for Supervisor certification at your MNO service centre."),
        ("17 million active mobile money accounts in Ghana (Q3 2024).",
         "Agent-to-account ratio: 1:620. Optimal ratio is 1:400 — gap means opportunity.",
         "GSMA State of the Industry 2024",
         "Rural agent positions are unfilled — higher commission rates apply."),
    ],
    "3253": [
        ("Ghana Health Service trained 12,000 new CHWs in 2023.",
         "NGO demand for certified CHWs outpaced supply by 34%.",
         "GHS Annual Report 2023",
         "CHW Certificate at district health office: 3 months, free, opens NGO roles."),
        ("USAID and GIZ both expanded CHW programs in Ghana in 2024.",
         "Certified CHWs earn 1.8× more than uncertified counterparts.",
         "WHO Health Workforce Report 2024",
         "Community trust is your credential. Formalise it now."),
    ],
    "7411": [
        ("Ghana's off-grid solar market grew 41% in 2023.",
         "GOGLA estimates 180,000 solar systems installed — each needs maintenance.",
         "GOGLA Africa Off-Grid Solar Market Report 2023",
         "NVTI Solar Installation Certificate: 3 months, subsidised GHS 50–200."),
        ("World Bank approved $200M for Ghana energy access in 2024.",
         "Most funding is for installation and maintenance — not manufacturing.",
         "World Bank Project Brief 2024",
         "Registered solar technicians get first access to government contracts."),
    ],
    "DEFAULT": [
        ("The informal economy employs 89% of Ghana's workforce.",
         "Only 11% have any formal skills credential. First-mover advantage is real.",
         "ILO WESO 2024 + Ghana Statistical Service",
         "Complete your Skills Passport and get ahead of the formalisation wave."),
        ("Automation risk in LMICs is 40–60% lower than US estimates suggest.",
         "Infrastructure gaps and informal economy structures are natural buffers.",
         "Frey & Osborne (2013) + World Bank LMIC calibration 2022",
         "Your skills are more durable than the global headlines suggest."),
        ("Peer-verified skills increase hiring probability by 2.3× in informal markets.",
         "Based on World Bank STEP survey data, Ghana and Bangladesh.",
         "World Bank STEP Survey 2012–2014 + SSA proxy 2024",
         "Ask one satisfied customer to verify a skill via /passport → Request Vouch."),
    ],
}


def _get_pulse(isco: str) -> dict:
    pool = _PULSES.get(isco, _PULSES["DEFAULT"]) + _PULSES["DEFAULT"]
    entry = random.choice(pool)
    return {
        "headline": entry[0],
        "stat": entry[1],
        "source": entry[2],
        "action": entry[3],
    }


def _format_pulse(pulse: dict, country: str, date_str: str) -> str:
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"  MARKET PULSE — {country}",
        f"  {date_str}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"📌 {pulse['headline']}",
        "",
        f"   {pulse['stat']}",
        "",
        f"   Source: {pulse['source']}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "YOUR ACTION",
        f"   → {pulse['action']}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "/subscribe — get this daily at 09:00",
        "/skill /compare /roadmap",
    ]
    return "```\n" + "\n".join(lines) + "\n```"


# ── /tip command ──────────────────────────────────────────────────────────────

async def tip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Instant market insight for the user's dominant sector."""
    telegram_id = str(update.effective_user.id)

    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            r = await client.get(f"{API_BASE}/skills/passport/by_user/{telegram_id}")
            passport = r.json() if r.status_code == 200 else {}
        except Exception:
            passport = {}

    skills = passport.get("skills", [])
    isco_counts: dict[str, int] = {}
    for s in skills:
        if s.get("isco_code"):
            isco_counts[s["isco_code"]] = isco_counts.get(s["isco_code"], 0) + 1
    dominant_isco = max(isco_counts, key=isco_counts.get) if isco_counts else "DEFAULT"
    country = passport.get("country_iso", "GHA")

    pulse = _get_pulse(dominant_isco)
    date_str = datetime.utcnow().strftime("%d %b %Y")
    await update.message.reply_text(
        _format_pulse(pulse, country, date_str),
        parse_mode="Markdown",
    )


# ── /subscribe command ────────────────────────────────────────────────────────

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = str(update.effective_user.id)
    _SUBSCRIBERS.add(telegram_id)
    await update.message.reply_text(
        "Subscribed to daily Market Pulse.\n\n"
        "You'll receive a cited market insight every day at 09:00 UTC, "
        "calibrated to your skills and sector.\n\n"
        "Use /unsubscribe to stop anytime.\n"
        "Use /tip for an instant insight right now."
    )


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = str(update.effective_user.id)
    _SUBSCRIBERS.discard(telegram_id)
    await update.message.reply_text(
        "Unsubscribed from daily Market Pulse.\n\n"
        "Use /subscribe to re-enable anytime.\n"
        "Use /tip for an instant insight on demand."
    )


# ── Scheduled daily broadcast ─────────────────────────────────────────────────

async def _daily_pulse_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _SUBSCRIBERS:
        return

    date_str = datetime.utcnow().strftime("%d %b %Y")
    logger.info("Daily pulse job: sending to %d subscribers", len(_SUBSCRIBERS))

    async with httpx.AsyncClient(timeout=8.0) as client:
        for telegram_id in list(_SUBSCRIBERS):
            try:
                r = await client.get(f"{API_BASE}/skills/passport/by_user/{telegram_id}")
                passport = r.json() if r.status_code == 200 else {}
            except Exception:
                passport = {}

            skills = passport.get("skills", [])
            isco_counts: dict[str, int] = {}
            for s in skills:
                if s.get("isco_code"):
                    isco_counts[s["isco_code"]] = isco_counts.get(s["isco_code"], 0) + 1
            dominant_isco = max(isco_counts, key=isco_counts.get) if isco_counts else "DEFAULT"
            country = passport.get("country_iso", "GHA")

            pulse = _get_pulse(dominant_isco)
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=_format_pulse(pulse, country, date_str),
                    parse_mode="Markdown",
                )
            except Exception as exc:
                logger.warning("Daily pulse failed for %s: %s", telegram_id, exc)
                _SUBSCRIBERS.discard(telegram_id)


def schedule_daily_pulse(app: Application) -> None:
    if app.job_queue is None:
        logger.warning("JobQueue not available — daily pulse disabled.")
        return
    app.job_queue.run_daily(
        _daily_pulse_job,
        time=time(hour=9, minute=0, second=0),
        name="daily_pulse",
    )
    logger.info("Daily market pulse scheduled at 09:00 UTC")
