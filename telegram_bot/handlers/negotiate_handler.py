"""
Wage Negotiation Coach — /negotiate

Gives the user data-backed talking points for negotiating wages or service prices.
Calibrated to their skills, evidence tier, and country wage floors.
No external API — uses embedded, cited data.
"""

import logging
import httpx
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)
import os
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

# ILOSTAT + GLSS wage floor data baked in
_WAGE_FLOORS = {
    "GHA": {
        "7422": {"floor": 1800, "currency": "GHS", "period": "month",
                 "source": "ILOSTAT 2023 + Ghana National Daily Minimum Wage"},
        "4211": {"floor": 1600, "currency": "GHS", "period": "month",
                 "source": "Bank of Ghana MNO agent remuneration data 2023"},
        "3253": {"floor": 1400, "currency": "GHS", "period": "month",
                 "source": "Ghana Health Service CHW pay scale 2023"},
        "7411": {"floor": 2100, "currency": "GHS", "period": "month",
                 "source": "GOGLA technician pay survey 2023"},
        "2320": {"floor": 2400, "currency": "GHS", "period": "month",
                 "source": "GES TVET instructor pay scale 2023"},
        "DEFAULT": {"floor": 1400, "currency": "GHS", "period": "month",
                    "source": "Ghana National Daily Minimum Wage × 26 days"},
    },
    "BGD": {
        "7422": {"floor": 12000, "currency": "BDT", "period": "month",
                 "source": "ILOSTAT 2023 + Bangladesh minimum wage order"},
        "4211": {"floor": 10000, "currency": "BDT", "period": "month",
                 "source": "bKash/Nagad agent remuneration data 2023"},
        "3253": {"floor": 9500,  "currency": "BDT", "period": "month",
                 "source": "DGDA community health worker pay schedule 2023"},
        "7411": {"floor": 13000, "currency": "BDT", "period": "month",
                 "source": "IDCOL solar technician pay survey 2023"},
        "DEFAULT": {"floor": 8000, "currency": "BDT", "period": "month",
                    "source": "Bangladesh National Minimum Wage Board 2023"},
    },
}

_EVIDENCE_MULTIPLIERS = {
    "employer_verified": 1.35,
    "assessed":          1.20,
    "peer_vouched":      1.15,
    "self_report":       1.00,
}

_NEGOTIATION_TIPS = {
    "7422": [
        "Show your diagnostic track record: average repair time, return rate, satisfied customers.",
        "Mention your NVTI or any formal certification — even in progress.",
        "Quote the ILOSTAT floor: 'Certified electronics technicians in Ghana average GHS 1,800/mo.'",
        "Offer a trial period: 'Let me solve one problem. Then we discuss rate.'",
    ],
    "4211": [
        "Reference your transaction volume and zero-loss record.",
        "Supervisor roles pay 30–50% more — ask about the path to supervisor.",
        "Quote Bank of Ghana data: mobile money volume grew 31% in 2023 — your role is in demand.",
        "Float management skills are rare — emphasise if you have them.",
    ],
    "3253": [
        "Lead with community trust: 'I have X families who rely on me by name.'",
        "NGO rates are higher than government — research both before negotiating.",
        "A CHW Certificate doubles your negotiating floor with NGOs.",
        "WHO and UNICEF programs pay certified CHWs 1.8× informal rates.",
    ],
    "7411": [
        "Off-grid solar grew 41% in Ghana 2023 — your skills are scarce.",
        "Quote GOGLA: certified technicians earn GHS 2,100+/month.",
        "Government contracts require registered technicians — your cert is the entry ticket.",
        "Offer maintenance contracts, not just installation — recurring income.",
    ],
    "DEFAULT": [
        "Know your floor: the national minimum wage is your baseline, not your target.",
        "Peer vouches from satisfied customers are worth quoting: 'I have verified references.'",
        "Your Skills Passport is a credential — show it. It has cited evidence.",
        "Every skill you've documented has a market rate. Ask for the rate, not a favour.",
    ],
}


async def negotiate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /negotiate — Data-backed wage negotiation talking points.
    """
    telegram_id = str(update.effective_user.id)

    await update.message.reply_text("Building your negotiation brief…")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(f"{API_BASE}/skills/passport/by_user/{telegram_id}")
            passport = r.json() if r.status_code == 200 else {}
        except Exception:
            passport = {}

    skills = passport.get("skills", [])
    country = passport.get("country_iso", "GHA")

    isco_counts: dict[str, int] = {}
    for s in skills:
        if s.get("isco_code"):
            isco_counts[s["isco_code"]] = isco_counts.get(s["isco_code"], 0) + 1
    dominant_isco = max(isco_counts, key=isco_counts.get) if isco_counts else "7422"

    # Best evidence tier across skills
    tier_rank = ["employer_verified", "assessed", "peer_vouched", "self_report"]
    best_tier = "self_report"
    for s in skills:
        et = s.get("evidence_type", "self_report")
        if tier_rank.index(et) < tier_rank.index(best_tier):
            best_tier = et

    country_wages = _WAGE_FLOORS.get(country, _WAGE_FLOORS["GHA"])
    wage_data = country_wages.get(dominant_isco, country_wages.get("DEFAULT", country_wages.get("7422", {})))

    floor   = wage_data.get("floor", 1400)
    currency = wage_data.get("currency", "GHS")
    source  = wage_data.get("source", "ILOSTAT")
    mult    = _EVIDENCE_MULTIPLIERS.get(best_tier, 1.0)
    target  = int(floor * mult)

    tips = _NEGOTIATION_TIPS.get(dominant_isco, _NEGOTIATION_TIPS["DEFAULT"])

    tier_label = {
        "employer_verified": "Employer-verified skills",
        "assessed":          "Assessed / certificate skills",
        "peer_vouched":      "Peer-vouched skills",
        "self_report":       "Self-reported skills",
    }.get(best_tier, "Self-reported skills")

    skill_count = len(skills)
    peer_count  = sum(1 for s in skills if s.get("evidence_type") in
                      ("peer_vouched", "employer_verified", "assessed"))

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "  WAGE NEGOTIATION BRIEF",
        f"  {country} | ISCO {dominant_isco}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "YOUR POSITION",
        f"  Skills documented:  {skill_count}",
        f"  Verified by others: {peer_count}",
        f"  Best evidence tier: {tier_label}",
        "",
        "WAGE DATA",
        f"  Market floor:  {floor:,} {currency}/{wage_data.get('period','month')}",
        f"  Your target:   {target:,} {currency}/{wage_data.get('period','month')}",
        f"  Uplift reason: {mult:.0%} for {tier_label.lower()}",
        f"  Source: {source}",
        "",
        "TALKING POINTS",
    ]

    for i, tip in enumerate(tips, 1):
        lines.append(f"  {i}. {tip}")

    lines += [
        "",
        "YOUR ANCHOR PHRASE",
        f"  'Workers with my verified skills in {country}",
        f"   earn {floor:,}–{target:,} {currency}/month.",
        f"   Source: {source}.'",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "  Add peer vouches to strengthen",
        "  your position → /passport",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    await update.message.reply_text(
        "```\n" + "\n".join(lines) + "\n```",
        parse_mode="Markdown",
    )
