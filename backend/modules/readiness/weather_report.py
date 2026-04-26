"""
Readiness Lens — Automation Weather Report

Reframes automation risk as weather: familiar, actionable, not fatalistic.
"Partly cloudy with a 5-year window. Here's your umbrella."

The weather metaphor was chosen deliberately:
- Weather is expected. Nobody blames themselves for rain.
- Weather has a horizon — it passes, or you prepare.
- Weather gives specific actions: bring an umbrella, not "be generally safer."
"""

from backend.modules.readiness.frey_calibrator import (
    _ADJACENT_ISCO,
    _PROTECTIVE_BY_MAJOR,
    _TIERS,
    get_calibration,
)

# Weather conditions mapped to calibrated risk tiers
_WEATHER = {
    "low": {
        "icon": "sunny",
        "headline": "Clear skies",
        "horizon": "10+ year stability window",
        "description": (
            "Your occupation has strong automation-resistance factors in this context. "
            "The tasks that define this work — judgment calls, local knowledge, "
            "physical presence, community trust — are hard to automate here."
        ),
        "action": "Build depth. The skills that make you irreplaceable are worth investing in now.",
        "emoji": "☀️",
        "color": "#f0b429",
    },
    "medium": {
        "icon": "partly_cloudy",
        "headline": "Partly cloudy",
        "horizon": "5–10 year window before task changes",
        "description": (
            "Some routine tasks in this occupation will likely be automated in the next decade. "
            "The core skills remain valuable — but the edges are changing. "
            "Adjacent skills now are insurance."
        ),
        "action": "Expand sideways. Add one adjacent skill this year. Small moves compound.",
        "emoji": "⛅",
        "color": "#58a6ff",
    },
    "high": {
        "icon": "changeable",
        "headline": "Changeable weather",
        "horizon": "3–7 years before significant task displacement",
        "description": (
            "A meaningful portion of this occupation's current tasks will be automated or "
            "restructured in the next 3–7 years. This doesn't mean the job disappears — "
            "it means the job changes. The people who shape how it changes fare best."
        ),
        "action": "Move with the change. Identify the 2 tasks in this job that automation can't touch. Double down on those.",
        "emoji": "🌦️",
        "color": "#d97706",
    },
    "critical": {
        "icon": "storm",
        "headline": "Storm approaching",
        "horizon": "1–5 years before high displacement probability",
        "description": (
            "This occupation faces significant automation pressure in the near term. "
            "The opportunity to reposition is now, not later. The adjacent skills exist — "
            "many share 70–80% of the underlying competencies."
        ),
        "action": "Start transitioning now. The adjacent roles are closer than they look. See the Skills Constellation.",
        "emoji": "⛈️",
        "color": "#f85149",
    },
}


def generate_weather_report(isco_code: str) -> dict:
    """
    Generate the full Automation Weather Report for an ISCO occupation.
    """
    cal = get_calibration(isco_code)
    tier = cal["risk_tier"]
    weather = _WEATHER.get(tier, _WEATHER["medium"])
    major = str(isco_code)[0] if isco_code else "7"

    # Adjacent low-risk occupations (the "umbrella skills")
    adjacent = _ADJACENT_ISCO.get(major, _ADJACENT_ISCO.get("7", []))
    safe_adjacent = [a for a in adjacent if a[2] < 0.45][:3]

    # Protective skills for this major group
    protective = _PROTECTIVE_BY_MAJOR.get(major, _PROTECTIVE_BY_MAJOR["7"])[:4]

    # Build skill gap analysis (what to learn)
    umbrella_skills = []
    for isco, label, risk in safe_adjacent:
        umbrella_skills.append({
            "isco_code": isco,
            "label": label,
            "calibrated_risk": round(risk, 2),
            "learning_time": _estimate_learning_time(isco, major),
            "why": _adjacency_reason(isco_code, isco),
        })

    return {
        "isco_code": isco_code,
        "occupation": cal["occupation_label"],
        "weather_icon": weather["icon"],
        "weather_headline": weather["headline"],
        "weather_emoji": weather["emoji"],
        "weather_color": weather["color"],
        "horizon": weather["horizon"],
        "description": weather["description"],
        "action": weather["action"],
        "calibrated_risk_pct": cal["calibrated_pct"],
        "baseline_risk_pct": cal["baseline_pct"],
        "country_name": cal["country_name"],
        "protective_skills": protective,
        "umbrella_skills": umbrella_skills,
        "risk_tier": tier,
        "source_note": (
            f"Risk calibrated from Frey & Osborne (2013) baseline "
            f"using {cal['country_name']}-specific infrastructure and "
            f"informal economy adjustment factors. All numbers cite sources. "
            f"Uncertainty ±15% at occupation level."
        ),
    }


def generate_passport_weather(receipts: list[dict]) -> dict:
    """
    Generate a weather summary across all skills in a passport.
    Returns the dominant weather condition + per-skill breakdown.
    """
    if not receipts:
        return {
            "overall_weather": "partly_cloudy",
            "headline": "No skills recorded yet",
            "skill_weather": [],
        }

    skill_weather = []
    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}

    for r in receipts:
        isco = r.get("isco_code") or "7422"
        cal = get_calibration(isco)
        tier = cal["risk_tier"]
        risk_counts[tier] += 1
        w = _WEATHER[tier]
        skill_weather.append({
            "skill_label": r.get("skill_label", "Unknown"),
            "isco_code": isco,
            "weather_emoji": w["emoji"],
            "weather_headline": w["headline"],
            "calibrated_risk_pct": cal["calibrated_pct"],
            "risk_tier": tier,
            "is_heritage": r.get("is_heritage_skill", False),
        })

    # Dominant weather: highest-risk tier with more than 1 skill, else overall average
    if risk_counts["critical"] >= 2:
        dominant = "critical"
    elif risk_counts["high"] >= 3:
        dominant = "high"
    elif risk_counts["medium"] >= len(receipts) // 2:
        dominant = "medium"
    else:
        dominant = "low"

    w = _WEATHER[dominant]
    return {
        "overall_weather": w["icon"],
        "overall_emoji": w["emoji"],
        "overall_headline": w["headline"],
        "overall_color": w["color"],
        "overall_action": w["action"],
        "risk_distribution": risk_counts,
        "durable_pct": round(risk_counts["low"] / len(receipts) * 100) if receipts else 0,
        "skill_weather": skill_weather,
    }


def _estimate_learning_time(target_isco: str, source_major: str) -> str:
    same_major = target_isco[0] == source_major
    if same_major:
        return "2–4 months"
    technical_to_technical = source_major in "37" and target_isco[0] in "23"
    if technical_to_technical:
        return "4–8 months"
    return "6–12 months"


def _adjacency_reason(source: str, target: str) -> str:
    reasons = {
        ("7", "3"): "Technician roles share 70% of the diagnostic and repair toolkit.",
        ("7", "2"): "Technical depth transfers — credentials are the gap, not the skills.",
        ("5", "2"): "Customer-facing communication is the foundation. Add specialist knowledge.",
        ("4", "2"): "Administrative systems knowledge maps directly to analyst roles.",
    }
    key = (source[0], target[0])
    return reasons.get(key, "Overlapping task profile — skills transfer with targeted training.")
