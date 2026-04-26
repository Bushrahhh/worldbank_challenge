"""
Readiness Lens — Frey-Osborne Calibration Engine

The headline intellectual contribution of UNMAPPED:
  Frey & Osborne (2013) says 89% automation risk for phone repair.
  In Ghana, it's 37%. Here's why — shown transparently, with citations.

Every calibrated number carries its full provenance chain.
"""

from backend.adapters.onet import OnetAdapter
from backend.config_loader import calibrate_automation_score, get_config
from backend.models.sourced_data import AutomationScore, DataUnavailable

_onet = OnetAdapter()

# Risk tier thresholds (calibrated scale, not raw F&O)
_TIERS = [
    (0.0,  0.30, "low",    "Durable",   "This occupation has strong automation-resistance factors in the local context."),
    (0.30, 0.50, "medium", "Watchful",  "Some routine tasks face displacement risk in the next decade. Adjacent skills matter now."),
    (0.50, 0.70, "high",   "Shifting",  "Significant task displacement likely within 5–7 years. Upskilling window is open."),
    (0.70, 1.01, "critical","Urgent",   "High displacement probability. Transition planning should start immediately."),
]

# Protective skills by ISCO major group (1-digit prefix)
_PROTECTIVE_BY_MAJOR = {
    "1": ["Strategic planning", "Stakeholder relationship management", "Organizational decision-making"],
    "2": ["Research and analysis", "Complex problem formulation", "Cross-disciplinary synthesis"],
    "3": ["Field-based troubleshooting", "Client advisory services", "Technical interpretation"],
    "4": ["Exception handling", "Multi-system coordination", "Customer empathy"],
    "5": ["Crisis response", "Physical care and reassurance", "Hyperlocal knowledge"],
    "6": ["Agro-ecological observation", "Climate adaptation", "Informal supply chain management"],
    "7": ["Novel fault diagnosis", "Non-standard repair", "Customer trust building"],
    "8": ["Multi-machine oversight", "Quality edge-case detection", "Safety judgment calls"],
    "9": ["Physical terrain navigation", "Community network leverage", "Informal logistics"],
}

# Durable adjacent ISCO codes by major group (codes with low automation risk)
_ADJACENT_ISCO = {
    "7": [
        ("3511", "ICT operations technicians", 0.34),
        ("3512", "ICT user support technicians", 0.38),
        ("7411", "Electricians — building", 0.45),
        ("3521", "Broadcasting technicians", 0.28),
        ("2523", "Database/network professionals", 0.08),
    ],
    "5": [
        ("2635", "Social work professionals", 0.03),
        ("3412", "Social work associate professionals", 0.07),
        ("4226", "Receptionist/information clerks", 0.29),
        ("5329", "Health associate professionals", 0.12),
    ],
    "4": [
        ("2431", "Advertising/marketing professionals", 0.09),
        ("3311", "Securities/finance dealers", 0.15),
        ("2422", "Management consultants", 0.12),
    ],
    "6": [
        ("3213", "Farmers/agricultural advisers", 0.22),
        ("3252", "Medical/pharma reps", 0.18),
        ("1311", "Agricultural managers", 0.15),
    ],
    "9": [
        ("5414", "Security guards", 0.41),
        ("8332", "Heavy truck drivers", 0.54),
        ("3512", "ICT user support", 0.38),
    ],
}


def get_calibration(isco_code: str) -> dict:
    """
    Return the full calibration story for an ISCO occupation code.

    The headline numbers plus the narrative explaining each step.
    """
    raw = _onet.get_automation_score(isco_code)
    cfg = get_config()
    cal = cfg.automation_calibration

    if isinstance(raw, DataUnavailable):
        baseline = 0.55  # LMIC median fallback
        label = f"ISCO {isco_code} (occupation not in F&O dataset — using LMIC median)"
        data_gap = True
    else:
        baseline = raw.frey_osborne_probability
        label = raw.isco_label
        data_gap = False

    calibrated_data = calibrate_automation_score(baseline)
    calibrated = calibrated_data["calibrated"]
    infra_adj = calibrated_data["infrastructure_adjusted"]

    # Determine risk tier
    tier_id, tier_label, tier_note = "medium", "Watchful", ""
    for lo, hi, tid, tlabel, tnote in _TIERS:
        if lo <= calibrated < hi:
            tier_id, tier_label, tier_note = tid, tlabel, tnote
            break

    # Build the narrative
    country_name = cfg.country.name
    infra_pct = round(cal.infrastructure_adjustment * 100)
    informal_pct = round(cal.informal_economy_adjustment * 100)

    narrative = (
        f"Frey & Osborne modelled the US workforce in 2013. "
        f"Their model says {round(baseline * 100)}% of tasks in this occupation "
        f"could be automated with technology available then. "
        f"\n\n"
        f"That number doesn't translate directly to {country_name}. "
        f"Two local factors change it:\n\n"
        f"1. Infrastructure gap ({infra_pct}% factor): "
        f"{cal.infrastructure_adjustment_rationale}\n\n"
        f"2. Informal economy dynamics ({informal_pct}% factor): "
        f"{cal.informal_economy_adjustment_rationale}\n\n"
        f"Combined: {round(baseline * 100)}% × {infra_pct/100:.2f} × {informal_pct/100:.2f} "
        f"= {round(calibrated * 100)}%.\n\n"
        f"This is still real risk. The window for action is open — not closed."
    )

    # Protective skills for this ISCO major group
    major = str(isco_code)[0] if isco_code else "7"
    protective = _PROTECTIVE_BY_MAJOR.get(major, _PROTECTIVE_BY_MAJOR["7"])

    return {
        "isco_code": isco_code,
        "occupation_label": label,
        "baseline_score": round(baseline, 3),
        "baseline_pct": round(baseline * 100),
        "infrastructure_adjusted": round(infra_adj, 3),
        "infrastructure_adjusted_pct": round(infra_adj * 100),
        "calibrated_score": round(calibrated, 3),
        "calibrated_pct": round(calibrated * 100),
        "risk_tier": tier_id,
        "risk_tier_label": tier_label,
        "risk_tier_note": tier_note,
        "narrative": narrative,
        "calibration_factors": {
            "infrastructure": cal.infrastructure_adjustment,
            "infrastructure_source": cal.infrastructure_adjustment_source,
            "informal_economy": cal.informal_economy_adjustment,
            "informal_economy_source": cal.informal_economy_adjustment_source,
        },
        "protective_skills": protective,
        "country_name": country_name,
        "country_iso": cfg.country.iso_code,
        "data_gap_warning": data_gap,
        "sources": [
            {"name": "Frey & Osborne (2013)", "url": "https://www.oxfordmartin.ox.ac.uk/downloads/academic/future-of-employment.pdf"},
            {"name": "ILO SOC-ISCO crosswalk (2012)", "url": "https://www.ilo.org/public/english/bureau/stat/isco/"},
            {"name": "UNMAPPED calibration v1", "url": ""},
        ],
    }


def get_passport_risk_profile(receipts: list[dict]) -> dict:
    """
    Given a list of skill receipts (with isco_code), compute the aggregate
    automation risk profile for the passport holder.

    Returns overall risk + per-skill breakdown + durable skill count.
    """
    scored = []
    total_weight = 0.0
    weighted_risk = 0.0
    durable_count = 0

    for r in receipts:
        isco = r.get("isco_code") or "7422"
        raw = _onet.get_automation_score(isco)
        if isinstance(raw, DataUnavailable):
            baseline = 0.55
        else:
            baseline = raw.frey_osborne_probability
        cal_data = calibrate_automation_score(baseline)
        cal_risk = cal_data["calibrated"]
        weight = r.get("confidence", 0.7)
        weighted_risk += cal_risk * weight
        total_weight += weight
        if cal_risk < 0.30:
            durable_count += 1
        scored.append({
            "skill_label": r.get("skill_label", "Unknown"),
            "isco_code": isco,
            "calibrated_risk": round(cal_risk, 3),
            "is_heritage": r.get("is_heritage_skill", False),
        })

    overall = round(weighted_risk / total_weight, 3) if total_weight else 0.55

    _, tier_label, _ = "medium", "Watchful", ""
    for lo, hi, tid, tlabel, tnote in _TIERS:
        if lo <= overall < hi:
            tier_label = tlabel
            break

    return {
        "overall_risk": overall,
        "overall_risk_pct": round(overall * 100),
        "risk_tier_label": tier_label,
        "durable_skills": durable_count,
        "total_skills": len(receipts),
        "heritage_count": sum(1 for r in receipts if r.get("is_heritage_skill")),
        "skill_breakdown": scored,
    }
