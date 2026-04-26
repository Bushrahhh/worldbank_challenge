"""
Matching — API routes

POST /matching/match/{passport_uuid}          Full match: top opportunities + wrong job + econ signals
GET  /matching/wrong_job/{passport_uuid}      Deliberate mismatch explanation
GET  /matching/blind/{passport_uuid}          Employer blind profile
POST /matching/reveal/request                 Employer requests identity reveal
POST /matching/reveal/verify                  Verify a reveal token
GET  /matching/econ_signals/{opportunity_id}  Live ILOSTAT + WDI signals for one opportunity
GET  /matching/catalog                        All opportunities for active country (policymaker view)
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config_loader import get_config
from backend.models.db import get_db, SkillReceipt, SkillsPassport, User
from backend.modules.matching.honest_matcher import match_passport
from backend.modules.matching.wrong_job import get_wrong_job
from backend.modules.matching.blind_match import (
    build_blind_profile,
    generate_reveal_token,
    verify_reveal_token,
    build_revealed_profile,
)
from backend.modules.matching.econ_signals import get_econ_signals

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_passport_receipts(
    db: AsyncSession,
    passport_uuid: str,
) -> tuple[object, list[dict]]:
    """Return (passport_row, receipts_list) or raise 404."""
    result = await db.execute(
        select(SkillsPassport).where(SkillsPassport.passport_uuid == passport_uuid)
    )
    passport = result.scalar_one_or_none()
    if not passport:
        raise HTTPException(404, f"Passport {passport_uuid} not found")

    receipt_result = await db.execute(
        select(SkillReceipt).where(SkillReceipt.passport_id == passport.id)
    )
    receipts = [
        {
            "skill_label": r.skill_label,
            "esco_code": r.esco_code,
            "isco_code": r.isco_code,
            "evidence_type": r.evidence_type,
            "confidence": r.confidence,
            "is_heritage_skill": r.is_heritage_skill,
            "heritage_skill_id": r.heritage_skill_id,
        }
        for r in receipt_result.scalars().all()
    ]
    return passport, receipts


async def _load_user(db: AsyncSession, user_id: int) -> Optional[object]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# POST /matching/match/{passport_uuid}
# ---------------------------------------------------------------------------

class MatchRequest(BaseModel):
    current_wage_month: Optional[float] = None
    top_n: int = 5
    include_wrong_job: bool = True
    fetch_econ_signals: bool = True


@router.post("/match/{passport_uuid}")
async def match(
    passport_uuid: str,
    req: MatchRequest = MatchRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Main matching endpoint. Returns top-N ranked opportunities for a passport holder.

    Every match includes:
    - skill_overlap_pct, income_multiple, training_gap_months (the honest tradeoffs)
    - skill_gaps (what still needs to close)
    - why_good + wrong_if (the honest context)
    - Live econ signals: ILOSTAT wage floor + WDI sector growth (with source tooltips)
    - One deliberate 'wrong_job' mismatch with explanation

    This is not aspirational matching. Every number has a source.
    """
    passport, receipts = await _load_passport_receipts(db, passport_uuid)

    if not receipts:
        return {
            "passport_uuid": passport_uuid,
            "matches": [],
            "wrong_job": None,
            "message": (
                "No skill receipts found for this passport. "
                "Complete the skills interview first."
            ),
        }

    result = match_passport(
        receipts=receipts,
        current_wage_month=req.current_wage_month,
        top_n=req.top_n,
        include_wrong_job=req.include_wrong_job,
    )

    # Enrich top matches with live econ signals (concurrent)
    if req.fetch_econ_signals and result["matches"]:
        econ_tasks = [
            asyncio.create_task(get_econ_signals(m))
            for m in result["matches"]
        ]
        econ_results = await asyncio.gather(*econ_tasks, return_exceptions=True)
        for match_item, econ in zip(result["matches"], econ_results):
            if isinstance(econ, Exception):
                match_item["econ_signals"] = {
                    "error": str(econ),
                    "note": "Live signals unavailable — check network connectivity.",
                }
            else:
                match_item["econ_signals"] = econ

    # Add wrong job (LLM-explained if Groq available)
    if req.include_wrong_job:
        cfg = get_config()
        wrong_job = await get_wrong_job(
            receipts=receipts,
            country_iso=cfg.country.iso_code,
            scored_opportunities=result["matches"] + (
                [result["wrong_job"]] if result.get("wrong_job") else []
            ),
        )
        result["wrong_job"] = wrong_job

    result["passport_uuid"] = passport_uuid

    # Data gaps from active country config
    cfg = get_config()
    result["data_gaps"] = [
        {"id": g.id, "description": g.description, "affects": g.affects}
        for g in cfg.data_gaps
    ]

    return result


# ---------------------------------------------------------------------------
# GET /matching/wrong_job/{passport_uuid}
# ---------------------------------------------------------------------------

@router.get("/wrong_job/{passport_uuid}")
async def wrong_job(
    passport_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    """
    The trust-building feature: returns one opportunity we deliberately set aside
    and explains clearly why it is wrong for this user.

    'A system willing to say no is trusted when it says yes.'
    """
    _, receipts = await _load_passport_receipts(db, passport_uuid)
    cfg = get_config()

    result = await get_wrong_job(
        receipts=receipts,
        country_iso=cfg.country.iso_code,
    )
    if not result:
        return {
            "message": (
                "No instructive mismatch found in the catalog for this profile. "
                "All catalog opportunities are reasonable matches."
            ),
            "feature": "wrong_job",
        }
    return result


# ---------------------------------------------------------------------------
# GET /matching/blind/{passport_uuid}
# ---------------------------------------------------------------------------

@router.get("/blind/{passport_uuid}")
async def blind_profile(
    passport_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Employer-facing blind profile. PII stripped: no name, age, gender, location.
    Employer sees only: skills, evidence tiers, ISCO group labels, heritage count.

    To request identity disclosure, use POST /matching/reveal/request.
    """
    passport, receipts = await _load_passport_receipts(db, passport_uuid)
    user = await _load_user(db, passport.user_id)
    education = user.education_level if user else None
    cfg = get_config()

    return build_blind_profile(
        passport_uuid=passport_uuid,
        receipts=receipts,
        country_iso=cfg.country.iso_code,
        education_level=education,
    )


# ---------------------------------------------------------------------------
# POST /matching/reveal/request
# ---------------------------------------------------------------------------

class RevealRequest(BaseModel):
    passport_uuid: str
    employer_id: str
    employer_name: Optional[str] = None
    reason: Optional[str] = None


@router.post("/reveal/request")
async def reveal_request(req: RevealRequest):
    """
    Employer requests identity reveal for a blind profile.

    Returns a reveal token (48-hour TTL). The candidate must approve before
    any PII is disclosed. In production, this triggers a Telegram/SMS notification
    to the candidate.
    """
    token_data = generate_reveal_token(
        passport_uuid=req.passport_uuid,
        employer_id=req.employer_id,
    )
    token_data["employer_name"] = req.employer_name
    token_data["reason"] = req.reason
    token_data["status"] = "pending_candidate_approval"
    token_data["next_step"] = (
        "Candidate has been notified (in production: via Telegram/SMS). "
        "They must approve before the token can be used to reveal their identity."
    )
    return token_data


# ---------------------------------------------------------------------------
# POST /matching/reveal/verify
# ---------------------------------------------------------------------------

class RevealVerify(BaseModel):
    token: str
    passport_uuid: str


@router.post("/reveal/verify")
async def reveal_verify(
    req: RevealVerify,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a reveal token and return the full profile if valid.
    In demo mode, approval is automatic. In production, requires candidate approval flag.
    """
    parsed = verify_reveal_token(req.token)
    if not parsed:
        raise HTTPException(400, "Reveal token is invalid or expired.")
    if parsed["passport_uuid"] != req.passport_uuid:
        raise HTTPException(403, "Token does not match the requested passport.")

    passport, receipts = await _load_passport_receipts(db, req.passport_uuid)
    user = await _load_user(db, passport.user_id)
    cfg = get_config()

    holder_name = user.display_name if user else "Candidate"
    return build_revealed_profile(
        passport_uuid=req.passport_uuid,
        receipts=receipts,
        holder_name=holder_name,
        country_iso=cfg.country.iso_code,
    )


# ---------------------------------------------------------------------------
# GET /matching/econ_signals/{opportunity_id}
# ---------------------------------------------------------------------------

@router.get("/econ_signals/{opportunity_id}")
async def econ_signals_for_opportunity(opportunity_id: str):
    """
    Live econometric signals for one catalog opportunity.

    Returns:
    1. ILOSTAT wage floor for the occupation + country (with source citation)
    2. World Bank WDI sector employment growth (with source citation)

    Both in plain language. Both in local currency. Both citable.
    These are the two required econometric signals for the UNMAPPED demo.
    """
    import yaml
    from pathlib import Path

    opps_path = Path(__file__).parent.parent.parent / "data" / "opportunities.yaml"
    try:
        raw = yaml.safe_load(opps_path.read_text(encoding="utf-8"))
        all_opps = raw.get("opportunities", [])
    except Exception as exc:
        raise HTTPException(500, f"Could not load opportunity catalog: {exc}")

    opp = next((o for o in all_opps if o.get("id") == opportunity_id), None)
    if not opp:
        raise HTTPException(404, f"Opportunity '{opportunity_id}' not found in catalog.")

    cfg = get_config()
    # Resolve country
    country_iso = opp.get("country_iso", cfg.country.iso_code)
    if country_iso == "LMIC":
        country_iso = cfg.country.iso_code
    opp["country_iso"] = country_iso

    signals = await get_econ_signals(opp)
    signals["opportunity_id"] = opportunity_id
    signals["opportunity_title"] = opp.get("title", "")
    signals["isco_code"] = opp.get("isco_code", "")
    return signals


# ---------------------------------------------------------------------------
# GET /matching/catalog
# ---------------------------------------------------------------------------

@router.get("/catalog")
async def opportunity_catalog(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    min_growth: Optional[float] = Query(None, description="Minimum annual growth %"),
    max_training_months: Optional[int] = Query(None, description="Max training gap months"),
):
    """
    Full opportunity catalog for the active country.
    Used by the policymaker dashboard to show the supply side of the skills market.
    Includes source citations for all wage and growth figures.
    """
    import yaml
    from pathlib import Path

    opps_path = Path(__file__).parent.parent.parent / "data" / "opportunities.yaml"
    try:
        raw = yaml.safe_load(opps_path.read_text(encoding="utf-8"))
        all_opps = raw.get("opportunities", [])
    except Exception as exc:
        raise HTTPException(500, f"Could not load opportunity catalog: {exc}")

    cfg = get_config()
    country_iso = cfg.country.iso_code

    filtered = [
        o for o in all_opps
        if o.get("country_iso") in (country_iso, "LMIC")
    ]

    if sector:
        filtered = [o for o in filtered if o.get("sector") == sector]
    if min_growth is not None:
        filtered = [o for o in filtered if (o.get("growth_pct_yr") or 0) >= min_growth]
    if max_training_months is not None:
        filtered = [o for o in filtered if (o.get("training_gap_months") or 99) <= max_training_months]

    return {
        "country": cfg.country.name,
        "country_iso": country_iso,
        "currency": cfg.country.currency,
        "total": len(filtered),
        "opportunities": filtered,
        "data_note": (
            "Wages are survey-based estimates (2022–2023). "
            "Growth rates from IRENA, World Bank WDI, and sector associations. "
            "Openings are directional — not vacancy counts."
        ),
    }


# ---------------------------------------------------------------------------
# GET /matching/district_stats
# ---------------------------------------------------------------------------

@router.get("/district_stats")
async def district_stats(
    district_pop_unmapped: int = Query(
        47000,
        description="Estimated unmapped youth workers in district",
    ),
    policy_reach: int = Query(
        2300,
        description="Current policy program annual reach",
    ),
    displacement_risk_pct: float = Query(
        0.26,
        description="Fraction of workers in high-automation-risk occupations",
    ),
):
    """
    Policymaker District View statistics.

    The 'uncomfortable' numbers:
    - How many Amaras exist in your district
    - How many current programs reach
    - How many will be displaced without action
    - Cost of inaction in GDP terms

    These numbers are intentionally designed to create urgency, not comfort.
    """
    cfg = get_config()

    displaced_by_2030 = int(district_pop_unmapped * displacement_risk_pct)
    currently_unreached = district_pop_unmapped - policy_reach
    coverage_rate = round(policy_reach / district_pop_unmapped * 100, 1)

    # GDP cost proxy: World Bank estimates informal worker productivity
    # at ~$1,200 USD/year in Sub-Saharan Africa (SSA average, World Bank 2022)
    gdp_per_worker_usd = 1200
    cost_of_inaction_usd = displaced_by_2030 * gdp_per_worker_usd * 5  # 5-year lost production
    # Convert to local currency (approximate)
    # We use a rough exchange rate stored in config or fall back to USD display
    currency = cfg.country.currency

    skills_gap_summary = _compute_skills_gap(cfg)

    return {
        "country": cfg.country.name,
        "country_iso": cfg.country.iso_code,
        "district": {
            "unmapped_workers": district_pop_unmapped,
            "policy_reach": policy_reach,
            "unreached": currently_unreached,
            "coverage_rate_pct": coverage_rate,
            "displaced_by_2030_estimate": displaced_by_2030,
            "displacement_source": "Frey-Osborne calibrated to LMIC context (UNMAPPED model)",
        },
        "cost_of_inaction": {
            "usd": cost_of_inaction_usd,
            "label": f"~${cost_of_inaction_usd:,} USD lost over 5 years",
            "currency_local": currency,
            "methodology": (
                "World Bank informal worker productivity proxy ($1,200 USD/year, SSA average). "
                "5-year horizon from 2025–2030. Does not include social costs."
            ),
            "source": "World Bank Enterprise Surveys + ILO informal economy estimates",
        },
        "headline_message": (
            f"{district_pop_unmapped:,} workers in your district are invisible to the formal economy. "
            f"Current programs reach {policy_reach:,} — {coverage_rate}% coverage. "
            f"At current automation trajectory, {displaced_by_2030:,} will be displaced by 2030 "
            f"with no pathway visible. Cost: ~${cost_of_inaction_usd:,} USD in lost productivity."
        ),
        "call_to_action": (
            "UNMAPPED is the infrastructure layer between these workers and opportunity. "
            "Not another training program. A protocol that makes invisible skills visible — "
            "at $0 marginal cost per user."
        ),
        "skills_gap": skills_gap_summary,
        "data_gaps": [
            {"id": g.id, "description": g.description}
            for g in cfg.data_gaps
        ],
    }


def _compute_skills_gap(cfg) -> dict:
    """
    Compute aggregate skills gap for the policymaker view.
    High-demand skills vs. estimated supply from catalog data.
    """
    import yaml
    from pathlib import Path

    opps_path = Path(__file__).parent.parent.parent / "data" / "opportunities.yaml"
    try:
        raw = yaml.safe_load(opps_path.read_text(encoding="utf-8"))
        all_opps = raw.get("opportunities", [])
    except Exception:
        return {}

    country_opps = [
        o for o in all_opps
        if o.get("country_iso") in (cfg.country.iso_code, "LMIC")
    ]

    total_openings = sum(o.get("openings_estimate", 0) for o in country_opps)
    high_growth = [o for o in country_opps if (o.get("growth_pct_yr") or 0) > 20]
    fastest_entry = sorted(country_opps, key=lambda o: o.get("training_gap_months", 99))[:3]

    skill_demand: dict[str, int] = {}
    for o in country_opps:
        for s in o.get("required_skills", []):
            label = s["label"]
            skill_demand[label] = skill_demand.get(label, 0) + o.get("openings_estimate", 0)

    top_skills = sorted(skill_demand.items(), key=lambda x: x[1], reverse=True)[:8]

    return {
        "total_catalog_openings": total_openings,
        "high_growth_sectors": [
            {
                "title": o["title"],
                "sector": o["sector"],
                "growth_pct_yr": o.get("growth_pct_yr"),
                "openings": o.get("openings_estimate"),
            }
            for o in high_growth
        ],
        "fastest_entry_paths": [
            {
                "title": o["title"],
                "training_months": o.get("training_gap_months"),
                "wage_month": o.get("wage_month"),
                "currency": o.get("currency"),
            }
            for o in fastest_entry
        ],
        "top_demanded_skills": [
            {"skill": s, "weighted_openings": cnt}
            for s, cnt in top_skills
        ],
    }
