"""
Progress & Achievements — /progress

Shows passport growth journey with milestones and achievement badges.
Gamifies the skills-building process without being patronising.
"""

import logging
import httpx
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)
import os
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

_ACHIEVEMENTS = [
    (1,  "FIRST SKILL",        "You started. Most people never do."),
    (3,  "GROWING",            "3 skills documented. Your passport is real."),
    (5,  "SKILLED WORKER",     "5 skills. You're ahead of 70% of passport holders."),
    (8,  "SPECIALIST",         "8 skills. Employers can see real depth here."),
    (12, "EXPERT",             "12 skills. Top 10% of all UNMAPPED passports."),
    (20, "MASTER",             "20 skills. Rare. You're a walking knowledge base."),
]

_PEER_BADGES = [
    (1,  "TRUSTED",            "First peer verification — someone vouched for you."),
    (3,  "COMMUNITY VERIFIED", "3 peer vouches. Trust is your strongest credential."),
    (5,  "HIGHLY TRUSTED",     "5 verifications. You have real social capital."),
]

_HERITAGE_BADGES = [
    (1, "HERITAGE HOLDER",     "You carry skills the formal economy can't see yet."),
    (3, "CULTURAL CAPITAL",    "3 Heritage Skills. These are your competitive edge."),
]


def _get_achievement(count: int, table: list) -> tuple | None:
    earned = [a for a in table if count >= a[0]]
    return earned[-1] if earned else None


def _next_milestone(count: int, table: list) -> tuple | None:
    upcoming = [a for a in table if count < a[0]]
    return upcoming[0] if upcoming else None


def _progress_bar(current: int, target: int, width: int = 12) -> str:
    if target == 0:
        return "█" * width
    filled = min(width, round(current / target * width))
    return "█" * filled + "░" * (width - filled)


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = str(update.effective_user.id)

    await update.message.reply_text("Loading your passport journey…")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(f"{API_BASE}/skills/passport/by_user/{telegram_id}")
            passport = r.json() if r.status_code == 200 else None
        except Exception:
            passport = None

    if not passport:
        await update.message.reply_text(
            "No passport yet.\n\nUse /interview to start your journey."
        )
        return

    skills       = passport.get("skills", [])
    skill_count  = len(skills)
    peer_count   = sum(1 for s in skills if s.get("evidence_type") in
                       ("peer_vouched", "employer_verified", "assessed"))
    heritage_count = sum(1 for s in skills if s.get("is_heritage_skill"))
    strength     = min(100, skill_count * 10 + peer_count * 5 + heritage_count * 3)

    skill_badge   = _get_achievement(skill_count, _ACHIEVEMENTS)
    peer_badge    = _get_achievement(peer_count,  _PEER_BADGES)
    heritage_badge = _get_achievement(heritage_count, _HERITAGE_BADGES)

    next_skill    = _next_milestone(skill_count, _ACHIEVEMENTS)
    next_peer     = _next_milestone(peer_count,  _PEER_BADGES)

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "  YOUR PASSPORT JOURNEY",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "PASSPORT STRENGTH",
        f"  {_progress_bar(strength, 100)} {strength}/100",
        "",
        "SKILLS",
        f"  {skill_count} documented",
    ]

    if skill_badge:
        lines.append(f"  ✦ [{skill_badge[1]}]")
        lines.append(f"    {skill_badge[2]}")

    if next_skill:
        gap = next_skill[0] - skill_count
        lines.append(f"  → {gap} more skill{'s' if gap > 1 else ''} to unlock [{next_skill[1]}]")
        lines.append(f"    {_progress_bar(skill_count, next_skill[0])} {skill_count}/{next_skill[0]}")

    lines += ["", "PEER TRUST", f"  {peer_count} verification{'s' if peer_count != 1 else ''}"]

    if peer_badge:
        lines.append(f"  ✦ [{peer_badge[1]}]")
        lines.append(f"    {peer_badge[2]}")

    if next_peer:
        gap = next_peer[0] - peer_count
        lines.append(f"  → {gap} more vouch{'es' if gap > 1 else ''} to unlock [{next_peer[1]}]")

    lines += ["", "HERITAGE SKILLS", f"  {heritage_count} recognised"]

    if heritage_badge:
        lines.append(f"  ✦ [{heritage_badge[1]}]")
        lines.append(f"    {heritage_badge[2]}")
    elif heritage_count == 0:
        lines.append("  → Answer fully in /interview to unlock Heritage Skills")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "  /interview  /passport  /compare",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    await update.message.reply_text(
        "```\n" + "\n".join(lines) + "\n```",
        parse_mode="Markdown",
    )
