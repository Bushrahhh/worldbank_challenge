"""
Readiness Lens — Time Machine 2035

Four-panel view using Wittgenstein Centre projections.

  Panel 1 — TODAY:       Where the country's workforce is now
  Panel 2 — DO NOTHING:  SSP3 (slow progress) trajectory to 2035
  Panel 3 — PATH A:      SSP2 (medium) — targeted skilling investment
  Panel 4 — PATH B:      SSP1 (fast) — full education + digital integration

The regret note: what 2035 would look like if this infrastructure existed in 2020.
That gap is the cost of the missing years — made visceral, not abstract.
"""

from backend.adapters.wittgenstein import WittgensteinAdapter, SCENARIO_LABELS
from backend.adapters.onet import OnetAdapter
from backend.config_loader import get_config, calibrate_automation_score
from backend.models.sourced_data import DataUnavailable

_wic = WittgensteinAdapter()
_onet = OnetAdapter()

# Education levels → automation vulnerability proxy
# Higher education = lower average automation risk
_EDUC_RISK_PROXY = {
    "e1": 0.75,  # No education
    "e2": 0.68,  # Incomplete primary
    "e3": 0.62,  # Primary
    "e4": 0.55,  # Lower secondary (JHS/JSC)
    "e5": 0.45,  # Upper secondary (SHS/SSC)
    "e6": 0.35,  # Post-secondary non-tertiary (TVET)
    "e7": 0.22,  # Bachelor's or equivalent
    "e8": 0.12,  # Master's / PhD
}

# Narrative templates per panel
_PANEL_NARRATIVE = {
    "today": (
        "This is where {country}'s working-age population is today. "
        "{low_educ_pct}% have primary education or less — the group most exposed "
        "to automation displacement. {high_educ_pct}% have post-secondary credentials."
    ),
    "do_nothing": (
        "If current skilling investment continues at the same rate, by 2035 the "
        "displacement-exposed group shrinks only slightly to {low_educ_pct}%. "
        "Automation deployment will likely outrun this pace. "
        "The gap between risk and readiness widens."
    ),
    "path_a": (
        "With targeted vocational and digital skilling investment (Path A), "
        "by 2035 the post-secondary share reaches {high_educ_pct}%. "
        "This requires sustained policy commitment — not a one-time program."
    ),
    "path_b": (
        "Full integration of digital economy pathways alongside formal credentials "
        "(Path B) achieves {high_educ_pct}% post-secondary by 2035. "
        "This is the SSP1 scenario — fast progress with consistent investment."
    ),
}


def build_time_machine(country_iso3: str = None) -> dict:
    """
    Build the full Time Machine 2035 four-panel dataset.
    Uses the active country config if country_iso3 not specified.
    """
    cfg = get_config()
    if not country_iso3:
        country_iso3 = cfg.country.iso_code

    raw = _wic.get_time_machine_data(country_iso3)

    panels = {
        "today": _build_panel(raw["today"], "today", cfg.country.name, raw["base_year"]),
        "do_nothing": _build_panel(raw["do_nothing"], "do_nothing", cfg.country.name, raw["target_year"]),
        "path_a": _build_panel(raw["path_a"]["data"], "path_a", cfg.country.name, raw["target_year"]),
        "path_b": _build_panel(raw["path_b"]["data"], "path_b", cfg.country.name, raw["target_year"]),
    }

    # Regret gap: difference between do_nothing and path_b at 2035
    gap_pct = panels["path_b"]["high_educ_pct"] - panels["do_nothing"]["high_educ_pct"]

    regret_note = (
        f"If UNMAPPED-style infrastructure had existed since 2020, "
        f"{country_iso3} would be tracking toward the Path B scenario today. "
        f"The gap between Do-Nothing and Path B in 2035 is {gap_pct:.0f} percentage points "
        f"of the working-age population — that is the cost of the missing five years. "
        f"The window is still open."
    )

    # Automation pressure overlay: how does workforce education shift compare to automation risk?
    automation_pressure = _compute_automation_pressure(panels)

    return {
        "country_iso3": country_iso3,
        "country_name": cfg.country.name,
        "base_year": raw["base_year"],
        "target_year": raw["target_year"],
        "panels": panels,
        "regret_note": regret_note,
        "automation_pressure": automation_pressure,
        "source": raw["source"],
        "data_gap_disclosure": raw["data_gap_disclosure"],
        "scenario_labels": SCENARIO_LABELS,
    }


def _build_panel(data: dict, panel_key: str, country_name: str, year: int) -> dict:
    """Build a single panel from Wittgenstein education distribution data."""
    if not data or data.get("unavailable"):
        return {
            "year": year,
            "panel": panel_key,
            "unavailable": True,
            "reason": data.get("reason", "Data not available") if data else "No data",
            "education_bars": [],
            "low_educ_pct": 0,
            "high_educ_pct": 0,
            "avg_automation_risk": 0.55,
            "narrative": "Data not available for this country/scenario.",
        }

    bars = []
    low_educ_total = 0.0
    high_educ_total = 0.0
    weighted_risk = 0.0

    for level_id in ["e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8"]:
        entry = data.get(level_id)
        if not entry:
            continue
        share = entry["share"]
        risk = _EDUC_RISK_PROXY.get(level_id, 0.55)
        calibrated = calibrate_automation_score(risk)["calibrated"]
        weighted_risk += calibrated * share

        bars.append({
            "level_id": level_id,
            "label": entry["label"],
            "share_pct": round(share * 100, 1),
            "automation_risk": round(calibrated, 2),
        })

        if level_id in ("e1", "e2", "e3"):
            low_educ_total += share
        if level_id in ("e6", "e7", "e8"):
            high_educ_total += share

    low_pct = round(low_educ_total * 100, 1)
    high_pct = round(high_educ_total * 100, 1)
    avg_risk = round(weighted_risk, 3)

    narrative_tpl = _PANEL_NARRATIVE.get(panel_key, "{country} — {year}")
    narrative = narrative_tpl.format(
        country=country_name,
        year=year,
        low_educ_pct=low_pct,
        high_educ_pct=high_pct,
    )

    return {
        "year": year,
        "panel": panel_key,
        "education_bars": bars,
        "low_educ_pct": low_pct,
        "high_educ_pct": high_pct,
        "avg_automation_risk": avg_risk,
        "avg_automation_risk_pct": round(avg_risk * 100, 1),
        "narrative": narrative,
    }


def _compute_automation_pressure(panels: dict) -> dict:
    """
    Compare workforce automation risk under each scenario.
    Returns the delta (how much better Path B is vs Do-Nothing).
    """
    dn_risk = panels["do_nothing"].get("avg_automation_risk", 0.55)
    pb_risk = panels["path_b"].get("avg_automation_risk", 0.40)
    pa_risk = panels["path_a"].get("avg_automation_risk", 0.47)
    today_risk = panels["today"].get("avg_automation_risk", 0.58)

    return {
        "today_pct": round(today_risk * 100, 1),
        "do_nothing_pct": round(dn_risk * 100, 1),
        "path_a_pct": round(pa_risk * 100, 1),
        "path_b_pct": round(pb_risk * 100, 1),
        "intervention_gain_pct": round((dn_risk - pb_risk) * 100, 1),
        "note": (
            "Average automation risk across the working-age population, "
            "weighted by education attainment share. "
            "Calibrated for local infrastructure and informal economy factors."
        ),
    }
