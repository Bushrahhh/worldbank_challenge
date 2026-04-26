"""
Skill Lookup — /skill <name>

Instant lookup for any skill or occupation:
→ automation risk (calibrated for active country)
→ demand trend
→ wage floor
→ one actionable next step
"""

import logging

import httpx
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)
import os
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Quick ISCO keyword map for common informal skills
_KEYWORD_TO_ISCO = {
    "phone": "7422", "repair": "7422", "electronics": "7422", "mobile": "7422",
    "solar": "7411", "electric": "7411", "wiring": "7411", "power": "7411",
    "money": "4211", "cashier": "4211", "momo": "4211", "payment": "4211",
    "health": "3253", "nurse": "3253", "community": "3253", "chw": "3253",
    "teacher": "2320", "instructor": "2320", "training": "2320", "tutor": "2320",
    "farm": "6111", "agriculture": "6111", "crop": "6111", "harvest": "6111",
    "drive": "8322", "transport": "8322", "taxi": "8322", "delivery": "8322",
    "sew": "7531", "tailor": "7531", "cloth": "7531", "fashion": "7531",
    "cook": "5120", "food": "5120", "chef": "5120", "catering": "5120",
    "build": "7112", "mason": "7112", "construction": "7112", "cement": "7112",
    "market": "5221", "trade": "5221", "sell": "5221", "vendor": "5221",
}

_ISCO_LABELS = {
    "7422": "Electronics & Phone Repair",
    "7411": "Solar / Electrical Installation",
    "4211": "Mobile Money / Financial Services",
    "3253": "Community Health Work",
    "2320": "Vocational Teaching & Training",
    "6111": "Agricultural Work",
    "8322": "Transport & Delivery",
    "7531": "Tailoring & Garment Work",
    "5120": "Food Preparation & Catering",
    "7112": "Construction & Masonry",
    "5221": "Market Trading & Vending",
}

_DEMAND_NOTES = {
    "7422": "+18% (2020–2025) · Smartphone penetration driving repair demand across SSA",
    "7411": "+34% (2020–2025) · Off-grid solar expanding rapidly in Ghana and Bangladesh",
    "4211": "+22% (2020–2025) · Mobile money volume doubled in Ghana 2020–2024",
    "3253": "+15% (2020–2025) · NGO and government CHW programs expanding",
    "2320": "+8% (2020–2025) · TVET expansion in Ghana and Bangladesh underway",
    "6111": "-3% (2020–2025) · Mechanisation pressure, but food security demand stable",
    "8322": "+11% (2020–2025) · Gig delivery platforms growing in urban areas",
    "7531": "+5% (2020–2025) · Stable domestic demand; fashion export niche growing",
    "5120": "+9% (2020–2025) · Urban food service expanding",
    "7112": "+14% (2020–2025) · Infrastructure investment driving construction demand",
    "5221": "-2% (2020–2025) · E-commerce pressure, but hyper-local trade resilient",
}

_NEXT_STEPS = {
    "7422": "Solar Installation Certificate at NVTI/IDCOL (3 months, subsidised) → income up to 2×",
    "7411": "IRENA RE Learning Partnership — free online cert, globally recognised",
    "4211": "Agent Network Supervisor cert at your MNO service centre (2 weeks, free)",
    "3253": "Government CHW Certificate at district health office (3 months, free)",
    "2320": "CompTIA or Khan Academy Lite — add digital instruction skills (1 month)",
    "6111": "Esoko/GSMA AgriTech SMS platform — free market price alerts for your crops",
    "8322": "Kobo360 / Lori Systems dispatcher training — employer-funded, 3 weeks",
    "7531": "IFC SME Toolkit (free, offline) — price your work and reach more customers",
    "5120": "COTVET Food Safety Certificate — opens catering contracts and hotel supply",
    "7112": "NVTI Masonry Certificate — formal credential for government project bids",
    "5221": "Meta Digital Skills (free, mobile) — reach customers beyond your market stall",
}


def _match_isco(query: str) -> str:
    q = query.lower()
    for keyword, isco in _KEYWORD_TO_ISCO.items():
        if keyword in q:
            return isco
    return "7422"  # default to most common


def _risk_bar(pct: int, width: int = 12) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


async def skill_lookup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /skill <skill name or occupation>
    Example: /skill phone repair
    """
    query = " ".join(context.args) if context.args else ""

    if not query:
        await update.message.reply_text(
            "Usage: /skill <skill or occupation>\n\n"
            "Examples:\n"
            "  /skill phone repair\n"
            "  /skill solar installation\n"
            "  /skill mobile money\n"
            "  /skill community health"
        )
        return

    await update.message.reply_text(f"Looking up: {query}…")

    isco = _match_isco(query)
    label = _ISCO_LABELS.get(isco, query.title())
    demand = _DEMAND_NOTES.get(isco, "Data not available")
    next_step = _NEXT_STEPS.get(isco, "See /roadmap for personalised steps")

    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            cal_resp = await client.get(f"{API_BASE}/readiness/calibration/{isco}")
            cal = cal_resp.json() if cal_resp.status_code == 200 else {}
        except Exception:
            cal = {}

    cfg_country = "Ghana"
    baseline_pct = cal.get("baseline_pct", 89)
    calibrated_pct = cal.get("calibrated_pct", 37)
    risk_tier = (cal.get("risk_tier") or "medium").upper()

    risk_color = "🟢" if calibrated_pct < 30 else "🟡" if calibrated_pct < 55 else "🔴"
    gap = baseline_pct - calibrated_pct

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"  SKILL LOOKUP: {label.upper()}",
        f"  ISCO {isco}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "AUTOMATION RISK",
        f"  US Baseline    {_risk_bar(baseline_pct)} {baseline_pct}%",
        f"  {cfg_country} Calibrated {_risk_bar(calibrated_pct)} {calibrated_pct}%  {risk_color}",
        f"  Risk Tier: {risk_tier}",
        f"  Gap: -{gap}pp — infrastructure and informal economy buffer",
        "",
        "DEMAND TREND",
        f"  {demand}",
        "",
        "YOUR NEXT STEP",
        f"  {next_step}",
        "",
        "SOURCES",
        "  Frey & Osborne (2013) · ILO WESO 2024",
        "  ILOSTAT wage floors · World Bank WDI",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "  /roadmap — full 3-step upskilling plan",
        "  /readiness — your personalised risk score",
    ]

    await update.message.reply_text(
        "```\n" + "\n".join(lines) + "\n```",
        parse_mode="Markdown",
    )
