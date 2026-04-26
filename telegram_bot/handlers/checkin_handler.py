"""
Monthly Check-in Handler

/checkin  — Immediate: show passport status + prompt for new skills to add
Scheduled  — Monthly nudge sent to all users who have completed a passport

Uses python-telegram-bot's built-in JobQueue (APScheduler under the hood).
Register the monthly job via: schedule_monthly_checkins(app)
"""

import logging
from datetime import datetime

import httpx
from telegram import Update
from telegram.ext import Application, ContextTypes

logger = logging.getLogger(__name__)

import os
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _api_get(path: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{API_BASE}{path}")
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.warning("check-in API GET %s failed: %s", path, exc)
    return None


def _evidence_tier_label(evidence_type: str) -> str:
    return {
        "employer_verified": "Employer-verified",
        "assessed": "Assessed",
        "peer_vouched": "Peer-vouched",
        "self_report": "Self-reported",
    }.get(evidence_type, evidence_type)


def _passport_summary_text(passport: dict, cal: dict | None) -> str:
    """Build a concise passport status card for the check-in message."""
    skills = passport.get("skills", [])
    total  = len(skills)
    heritage = sum(1 for s in skills if s.get("is_heritage_skill"))
    peer_plus = sum(1 for s in skills if s.get("evidence_type") in ("peer_vouched", "employer_verified", "assessed"))

    country = passport.get("country_iso", "")
    issued  = (passport.get("issued_at") or "")[:10]

    lines = [
        "YOUR SKILLS PASSPORT CHECK-IN",
        "",
        f"Skills on record:   {total}",
        f"Heritage Skills:    {heritage}",
        f"Peer-verified+:     {peer_plus} of {total}",
        f"Country:            {country}",
        f"Last updated:       {issued}",
    ]

    if cal:
        lines += [
            "",
            f"Automation risk:  {cal.get('calibrated_pct', '–')}% (calibrated for {country})",
            f"Risk tier:        {cal.get('risk_tier', '–').upper()}",
        ]

    lines += [
        "",
        "Anything new to add? A job you did, a skill you used, a certificate you earned?",
        "Type it below, or send a voice message — I'll add it to your passport.",
        "",
        "/interview  to start a full update session",
        "/passport   to view your full passport",
        "/readiness  to review your automation risk",
    ]

    return "\n".join(lines)


# ── /checkin command ──────────────────────────────────────────────────────────

async def checkin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /checkin — Show passport status and invite the user to add new skills.
    Works as a standalone command; does not start a ConversationHandler.
    """
    telegram_id = str(update.effective_user.id)
    name = update.effective_user.first_name or "there"

    await update.message.reply_text(f"Checking in, {name}…")

    # 1. Fetch user passport
    passport = await _api_get(f"/skills/passport/by_user/{telegram_id}")
    if not passport:
        await update.message.reply_text(
            "No Skills Passport found yet.\n\n"
            "Use /interview to start your skills interview — it takes about 5 minutes."
        )
        return

    # 2. Fetch calibration headline (dominant ISCO from passport)
    passport_uuid = passport.get("passport_id") or passport.get("passport_uuid")
    cal = None
    if passport_uuid:
        cal = await _api_get(f"/readiness/profile/{passport_uuid}")
        if cal:
            cal = cal.get("headline_calibration")

    # 3. Send status card
    summary = _passport_summary_text(passport, cal)
    await update.message.reply_text(summary)


# ── Scheduled monthly nudge ───────────────────────────────────────────────────

async def _monthly_checkin_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    APScheduler job: fires monthly.
    Queries all users with passports and sends a nudge.
    """
    logger.info("Monthly check-in job firing at %s", datetime.utcnow().isoformat())

    users = await _api_get("/skills/users_with_passports")
    if not users:
        logger.info("No passport holders found — skipping monthly check-in")
        return

    sent = 0
    for user in users:
        telegram_id = user.get("telegram_id")
        if not telegram_id:
            continue
        passport_uuid = user.get("passport_uuid")
        skill_count   = user.get("skill_count", 0)
        name          = user.get("display_name") or "there"

        try:
            await context.bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"Hi {name} — monthly skills check-in!\n\n"
                    f"Your passport has {skill_count} skill{'' if skill_count == 1 else 's'} on record.\n\n"
                    "Did anything change in the last month? A new job, a course completed, "
                    "a skill you used for the first time?\n\n"
                    "Use /checkin to update your passport, or /interview for a full session.\n\n"
                    "_Your living skills record stays accurate only if you update it._"
                ),
                parse_mode="Markdown",
            )
            sent += 1
        except Exception as exc:
            logger.warning("Failed to send check-in to telegram_id=%s: %s", telegram_id, exc)

    logger.info("Monthly check-in: sent %d / %d messages", sent, len(users))


def schedule_monthly_checkins(app: Application) -> None:
    """
    Register the monthly check-in job with the bot's JobQueue.
    Called once during bot startup.

    Fires at 09:00 UTC on the 1st of each month.
    """
    if app.job_queue is None:
        logger.warning(
            "JobQueue not available — install python-telegram-bot[job-queue]. "
            "Monthly check-ins disabled."
        )
        return

    app.job_queue.run_monthly(
        _monthly_checkin_job,
        when=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
        day=1,
        name="monthly_checkin",
    )
    logger.info("Monthly check-in job scheduled: 1st of each month at 09:00 UTC")
