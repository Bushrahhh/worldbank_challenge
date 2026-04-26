"""
Readiness Lens — API routes

GET /readiness/calibration/{isco_code}   Frey-Osborne calibration story
GET /readiness/weather/{isco_code}       Automation weather report
GET /readiness/weather/passport/{uuid}   Weather across full passport
GET /readiness/time_machine              Wittgenstein 4-panel 2035 view
GET /readiness/constellation/{uuid}     Skills constellation star map data
GET /readiness/profile/{uuid}            Full readiness profile for a passport
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config_loader import get_config
from backend.models.db import get_db, SkillReceipt, SkillsPassport
from backend.modules.readiness.frey_calibrator import get_calibration, get_passport_risk_profile
from backend.modules.readiness.weather_report import generate_weather_report, generate_passport_weather
from backend.modules.readiness.time_machine import build_time_machine
from backend.modules.readiness.constellation import build_constellation
from backend.modules.readiness.upskill_roadmap import build_roadmap

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_receipts(db: AsyncSession, passport_uuid: str) -> list[dict]:
    result = await db.execute(
        select(SkillsPassport).where(SkillsPassport.passport_uuid == passport_uuid)
    )
    passport_row = result.scalar_one_or_none()
    if not passport_row:
        raise HTTPException(404, f"Passport {passport_uuid} not found")

    receipt_result = await db.execute(
        select(SkillReceipt).where(SkillReceipt.passport_id == passport_row.id)
    )
    return [
        {
            "skill_label": r.skill_label,
            "isco_code": r.isco_code,
            "evidence_type": r.evidence_type,
            "confidence": r.confidence,
            "is_heritage_skill": r.is_heritage_skill,
        }
        for r in receipt_result.scalars().all()
    ]


@router.get("/calibration/{isco_code}")
async def calibration(isco_code: str):
    """
    The headline Readiness Lens moment:
    'Frey-Osborne says 89%. In Ghana, it's 37%. Here's why.'

    Returns the full calibration chain with narrative and citations.
    """
    return get_calibration(isco_code)


@router.get("/weather/{isco_code}")
async def weather(isco_code: str):
    """
    Automation Weather Report for a single occupation.
    ☀️ Clear / ⛅ Partly cloudy / 🌦️ Changeable / ⛈️ Storm
    """
    return generate_weather_report(isco_code)


@router.get("/weather/passport/{passport_uuid}")
async def weather_for_passport(
    passport_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    """Weather report across all skills in a passport."""
    receipts = await _get_receipts(db, passport_uuid)
    return generate_passport_weather(receipts)


@router.get("/time_machine")
async def time_machine(country_iso3: str = None):
    """
    Wittgenstein Centre 2035 four-panel Time Machine.

    Panels: today / do-nothing (SSP3) / path-A (SSP2) / path-B (SSP1)
    Includes regret note: cost of the missing years since 2020.
    """
    cfg = get_config()
    iso3 = (country_iso3 or cfg.country.iso_code).upper()
    return build_time_machine(iso3)


@router.get("/constellation/{passport_uuid}")
async def constellation(
    passport_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Skills Constellation star map data for a passport.
    Returns SVG-ready (x, y, r, color) node data + adjacency edges.
    """
    receipts = await _get_receipts(db, passport_uuid)
    return build_constellation(receipts)


@router.get("/roadmap/{passport_uuid}")
async def upskilling_roadmap(
    passport_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    """
    3-step upskilling roadmap for a passport holder.

    Each step is specific, free or near-free, time-bounded, and sourced.
    Calibrated to the active country's resource landscape.
    """
    receipts = await _get_receipts(db, passport_uuid)

    isco_counts: dict[str, int] = {}
    for r in receipts:
        if r.get("isco_code"):
            isco_counts[r["isco_code"]] = isco_counts.get(r["isco_code"], 0) + 1
    dominant_isco = max(isco_counts, key=isco_counts.get) if isco_counts else "7422"

    calibration = get_calibration(dominant_isco)
    calibrated_risk = calibration.get("calibrated_risk", 0.37)

    return build_roadmap(
        isco_code=dominant_isco,
        calibrated_risk=calibrated_risk,
        receipts=receipts,
    )


@router.get("/roadmap/isco/{isco_code}")
async def upskilling_roadmap_by_isco(isco_code: str, risk: float = 0.37):
    """3-step roadmap for any ISCO code — no passport required. Uses provided risk score."""
    return build_roadmap(isco_code=isco_code, calibrated_risk=risk)


@router.get("/profile/{passport_uuid}")
async def readiness_profile(
    passport_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Full Readiness Lens profile for a passport holder.
    Combines: calibration summary + weather + time machine + constellation.
    Single call for the readiness web app.
    """
    receipts = await _get_receipts(db, passport_uuid)

    # Pick the dominant ISCO from the passport for calibration headline
    isco_counts: dict[str, int] = {}
    for r in receipts:
        if r.get("isco_code"):
            isco_counts[r["isco_code"]] = isco_counts.get(r["isco_code"], 0) + 1
    dominant_isco = max(isco_counts, key=isco_counts.get) if isco_counts else "7422"

    cfg = get_config()
    risk_profile = get_passport_risk_profile(receipts)
    weather = generate_passport_weather(receipts)
    time_machine_data = build_time_machine(cfg.country.iso_code)
    stars = build_constellation(receipts)
    headline_cal = get_calibration(dominant_isco)

    return {
        "passport_uuid": passport_uuid,
        "country": cfg.country.name,
        "country_iso": cfg.country.iso_code,
        "dominant_isco": dominant_isco,
        "headline_calibration": headline_cal,
        "risk_profile": risk_profile,
        "weather": weather,
        "time_machine": time_machine_data,
        "constellation": stars,
    }
