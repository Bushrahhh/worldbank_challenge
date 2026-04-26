"""
Module 3 — Matching: Honest Matcher

Distance-aware matching that shows every opportunity with full tradeoffs.
"Solar technician — 6 months training, 2.3× your current income, 47 openings within 30km."

Design rules:
- Every match shows the real gap (training months, income delta, skill gaps).
- Never aspirational. No "you could be a software engineer."
- Score = skill_overlap × 0.5 + income_potential × 0.3 + entry_speed × 0.2
- Heritage skill bonus applied when opportunity tags include heritage_fit.
- Results carry source citations for every wage and growth number.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

from backend.config_loader import get_config

logger = logging.getLogger(__name__)

_OPPORTUNITIES_PATH = Path(__file__).parent.parent.parent.parent / "data" / "opportunities.yaml"

# ---------------------------------------------------------------------------
# Opportunity loader (cached at module level, reloaded on country swap)
# ---------------------------------------------------------------------------

_cached_country: Optional[str] = None
_cached_opportunities: list[dict] = []


def _load_opportunities(country_iso: str) -> list[dict]:
    global _cached_country, _cached_opportunities
    if _cached_country == country_iso:
        return _cached_opportunities

    try:
        raw = yaml.safe_load(_OPPORTUNITIES_PATH.read_text(encoding="utf-8"))
        all_opps = raw.get("opportunities", [])
    except Exception as exc:
        logger.warning("Failed to load opportunities.yaml: %s", exc)
        return []

    filtered = [
        o for o in all_opps
        if o.get("country_iso") in (country_iso, "LMIC")
    ]
    _cached_country = country_iso
    _cached_opportunities = filtered
    logger.info(
        "Loaded %d opportunities for %s (+ %d LMIC)",
        sum(1 for o in filtered if o.get("country_iso") == country_iso),
        country_iso,
        sum(1 for o in filtered if o.get("country_iso") == "LMIC"),
    )
    return filtered


# ---------------------------------------------------------------------------
# Skill matching helpers
# ---------------------------------------------------------------------------

def _isco_overlap_score(user_isco_codes: list[str], required_isco: list[str]) -> float:
    """
    Fraction of required ISCO codes that match user's known codes.
    Uses major-group fallback: "7422" matches "74xx" logic.
    """
    if not required_isco:
        return 0.5  # no requirements = accessible to all
    if not user_isco_codes:
        return 0.0

    exact_hits = sum(1 for r in required_isco if r in user_isco_codes)
    # Major-group (first digit) fuzzy match
    user_majors = {c[0] for c in user_isco_codes if c}
    fuzzy_hits = sum(
        1 for r in required_isco
        if r not in user_isco_codes and r[0] in user_majors
    )
    # Exact = 1 point, major-group = 0.4 points
    score = (exact_hits + fuzzy_hits * 0.4) / len(required_isco)
    return min(score, 1.0)


def _skill_label_overlap(user_skill_labels: list[str], required_skills: list[dict]) -> float:
    """
    Soft label match: check if any user skill keywords appear in required skill labels.
    Returns weighted fraction of required skills matched.
    """
    if not required_skills:
        return 0.5
    if not user_skill_labels:
        return 0.0

    user_tokens = set()
    for label in user_skill_labels:
        user_tokens.update(label.lower().split())

    total_weight = sum(s.get("weight", 1.0) for s in required_skills)
    matched_weight = 0.0

    for req in required_skills:
        req_tokens = set(req["label"].lower().split())
        # Intersection of meaningful tokens (len > 3)
        shared = {t for t in req_tokens & user_tokens if len(t) > 3}
        if shared:
            matched_weight += req.get("weight", 1.0)
        elif any(t in req["label"].lower() for t in user_tokens if len(t) > 4):
            matched_weight += req.get("weight", 1.0) * 0.5

    return matched_weight / total_weight if total_weight else 0.0


def _heritage_bonus(receipts: list[dict], opportunity: dict) -> float:
    """Return 0.15 bonus if user has heritage skills and opportunity is heritage-adjacent."""
    tags = opportunity.get("tags", [])
    if not any(t in tags for t in ("heritage_fit", "heritage_adjacent", "community")):
        return 0.0
    has_heritage = any(r.get("is_heritage_skill") for r in receipts)
    return 0.15 if has_heritage else 0.0


def _income_score(current_wage: float, opportunity_wage: float) -> float:
    """
    Normalised income uplift score (0–1).
    2× wage → 1.0; same wage → 0.3; lower → 0.0.
    """
    if not current_wage or not opportunity_wage:
        return 0.3  # unknown — neutral
    ratio = opportunity_wage / current_wage
    if ratio >= 2.0:
        return 1.0
    if ratio >= 1.5:
        return 0.8
    if ratio >= 1.0:
        return 0.5
    if ratio >= 0.8:
        return 0.2
    return 0.0


def _entry_speed_score(training_months: int) -> float:
    """
    Normalised entry speed (0–1). Faster = higher score.
    0 months → 1.0, 12+ months → 0.1.
    """
    if training_months <= 0:
        return 1.0
    if training_months <= 1:
        return 0.9
    if training_months <= 3:
        return 0.7
    if training_months <= 6:
        return 0.5
    if training_months <= 9:
        return 0.3
    return 0.1


# ---------------------------------------------------------------------------
# Gap disclosure builder
# ---------------------------------------------------------------------------

def _build_skill_gaps(receipts: list[dict], opportunity: dict) -> list[dict]:
    """List the required skills that the user doesn't clearly cover."""
    user_labels = [r["skill_label"].lower() for r in receipts]
    user_tokens = set()
    for label in user_labels:
        user_tokens.update(label.split())

    gaps = []
    for req in opportunity.get("required_skills", []):
        req_tokens = set(req["label"].lower().split())
        shared = {t for t in req_tokens & user_tokens if len(t) > 3}
        if not shared:
            gaps.append({
                "skill": req["label"],
                "importance": req.get("weight", 0.5),
            })
    return gaps


# ---------------------------------------------------------------------------
# Core match function
# ---------------------------------------------------------------------------

def match_passport(
    receipts: list[dict],
    current_wage_month: Optional[float] = None,
    top_n: int = 5,
    include_wrong_job: bool = True,
) -> dict:
    """
    Match a skills passport (list of SkillReceipts) against the opportunity catalog.

    Returns:
        {
          "matches": [ ... top_n ranked matches ... ],
          "wrong_job": { ... one deliberate mismatch ... },
          "data_note": "...",
          "country": "...",
          "total_scored": N,
        }

    Each match includes:
        id, title, score, skill_overlap, income_multiple, training_gap_months,
        openings_estimate, why_good, skill_gaps, econ_signals_stub,
        tags, automation_risk_calibrated, sources.
    """
    cfg = get_config()
    country_iso = cfg.country.iso_code
    currency = cfg.country.currency

    opportunities = _load_opportunities(country_iso)
    if not opportunities:
        return {
            "matches": [],
            "wrong_job": None,
            "data_note": "No opportunities loaded for this country.",
            "country": cfg.country.name,
            "total_scored": 0,
        }

    user_isco = [r.get("isco_code", "") for r in receipts if r.get("isco_code")]
    user_labels = [r.get("skill_label", "") for r in receipts if r.get("skill_label")]

    # Estimate current wage from receipts if not provided
    if not current_wage_month:
        # Rough proxy: median wage of matched ISCOs in catalog
        known_wages = [
            o["wage_month"]
            for o in opportunities
            if o.get("isco_code") in user_isco and o.get("wage_month")
        ]
        current_wage_month = (sum(known_wages) / len(known_wages)) if known_wages else 0.0

    scored = []
    for opp in opportunities:
        isco_score = _isco_overlap_score(user_isco, opp.get("required_isco", []))
        label_score = _skill_label_overlap(user_labels, opp.get("required_skills", []))
        skill_overlap = isco_score * 0.6 + label_score * 0.4

        opp_wage = opp.get("wage_month", 0)
        income_s = _income_score(current_wage_month, opp_wage)
        entry_s = _entry_speed_score(opp.get("training_gap_months", 6))
        heritage_b = _heritage_bonus(receipts, opp)

        total = (
            skill_overlap * 0.50
            + income_s    * 0.30
            + entry_s     * 0.20
            + heritage_b
        )

        income_multiple = round(opp_wage / current_wage_month, 1) if current_wage_month else None

        scored.append({
            "id": opp["id"],
            "title": opp["title"],
            "sector": opp.get("sector", ""),
            "employer_type": opp.get("employer_type", ""),
            "isco_code": opp.get("isco_code", ""),
            "country_iso": opp.get("country_iso", country_iso),
            # Honest distance metrics — always shown
            "score": round(total, 3),
            "skill_overlap_pct": round(skill_overlap * 100),
            "income_multiple": income_multiple,
            "income_month": opp_wage,
            "income_currency": opp.get("currency", currency),
            "training_gap_months": opp.get("training_gap_months", 0),
            "training_source": opp.get("training_source", ""),
            "openings_estimate": opp.get("openings_estimate", 0),
            "openings_source": opp.get("openings_source", ""),
            "growth_pct_yr": opp.get("growth_pct_yr"),
            "growth_source": opp.get("growth_source", ""),
            "automation_risk_calibrated": opp.get("automation_risk_calibrated"),
            # Tradeoff narrative — honest
            "why_good": opp.get("why_good", ""),
            "wrong_if": opp.get("wrong_if", ""),
            # Gaps the user still needs to close
            "skill_gaps": _build_skill_gaps(receipts, opp),
            # Sources for UI tooltips
            "sources": {
                "wage": opp.get("wage_source", ""),
                "openings": opp.get("openings_source", ""),
                "growth": opp.get("growth_source", ""),
                "training": opp.get("training_source", ""),
            },
            "tags": opp.get("tags", []),
            # Econ signals will be populated live by the API layer
            "econ_signals": None,
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Separate the top matches from the deliberate wrong-job pick
    top_matches = scored[:top_n]

    wrong_job = None
    if include_wrong_job and len(scored) > top_n:
        # Pick the highest-scoring opportunity that has a real barrier (wrong_if non-empty)
        # and is NOT already in top matches — so the user sees we turned something down.
        candidates = [
            s for s in scored[top_n:]
            if s.get("wrong_if") and s["skill_overlap_pct"] < 40
        ]
        if candidates:
            wrong_job = candidates[0]
            wrong_job["_wrong_job_explanation"] = (
                f"We chose NOT to show this as a match. "
                f"Skill overlap is only {wrong_job['skill_overlap_pct']}%, "
                f"and there's a real barrier: {wrong_job['wrong_if']}"
            )

    data_notes = [
        "Skill overlap is estimated from ISCO code and keyword matching — not a formal assessment.",
        "Income multiples use catalog wage estimates. Actual pay varies by employer.",
        "Openings estimates are from 2022–2023 surveys. Treat as directional, not exact.",
    ]

    return {
        "matches": top_matches,
        "wrong_job": wrong_job,
        "data_note": " ".join(data_notes),
        "country": cfg.country.name,
        "country_iso": country_iso,
        "currency": currency,
        "current_wage_estimate": current_wage_month,
        "total_scored": len(scored),
    }
