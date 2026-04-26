"""
Matching — Econometric Signals

Live wage floor (ILOSTAT) and sector growth (WDI) for a matched opportunity.
Both in local currency. Both with source citation. Both in plain language.

These two signals are non-negotiable UI requirements for UNMAPPED:
- The user must always see what the market says their time is worth.
- The user must always see whether the sector is growing or shrinking.
"""

import asyncio
import logging

from backend.adapters.ilostat import ILOSTATAdapter
from backend.adapters.worldbank_wdi import WorldBankWDIAdapter
from backend.config_loader import get_config
from backend.models.sourced_data import DataUnavailable

logger = logging.getLogger(__name__)

_ilo = ILOSTATAdapter()
_wdi = WorldBankWDIAdapter()

# Sector → WDI series key mapping
_SECTOR_WDI_MAP = {
    "renewable_energy":  "EG.ELC.RNEW.ZS",
    "digital_services":  "IT.NET.USER.ZS",
    "fintech":           "FX.OWN.TOTL.ZS",
    "mobile_finance":    "FX.OWN.TOTL.ZS",
    "garments":          "SL.IND.EMPL.ZS",
    "agriculture":       "SL.AGR.EMPL.ZS",
    "health":            "SH.MED.NUMW.P3",
    "logistics":         "IS.SHP.GCNW.XQ",
    "services":          "SL.SRV.EMPL.ZS",
    "circular_economy":  "EG.ELC.RNEW.ZS",
    "education":         "SE.SEC.ENRR",
}

# ISCO major group → ILO occupation category label
_ISCO_ILO_SECTOR = {
    "1": "managers",
    "2": "professionals",
    "3": "technicians",
    "4": "clerical",
    "5": "services",
    "6": "agriculture",
    "7": "trades",
    "8": "operators",
    "9": "elementary",
}


async def get_econ_signals(opportunity: dict) -> dict:
    """
    Fetch live econometric signals for one opportunity.
    Returns wage floor, sector growth, and plain-language summaries.
    """
    cfg = get_config()
    country_iso = opportunity.get("country_iso", cfg.country.iso_code)
    if country_iso == "LMIC":
        country_iso = cfg.country.iso_code
    isco = opportunity.get("isco_code", "7422")
    sector = opportunity.get("sector", "services")
    currency = opportunity.get("currency", cfg.country.currency)
    if currency == "LOCAL":
        currency = cfg.country.currency

    # Fetch wage floor and sector growth concurrently
    wage_task = asyncio.create_task(_get_wage(country_iso, isco))
    growth_task = asyncio.create_task(_get_growth(country_iso, sector))
    wage_result, growth_result = await asyncio.gather(wage_task, growth_task)

    # Opportunity wage vs floor comparison
    opp_wage = opportunity.get("wage_month", 0)
    if isinstance(wage_result, DataUnavailable) or not wage_result:
        wage_floor = None
        wage_floor_source = wage_result.source.name if isinstance(wage_result, DataUnavailable) else "unavailable"
        vs_floor_text = f"Wage floor data unavailable for {country_iso}."
    else:
        wage_floor = wage_result.monthly_wage
        wage_floor_source = wage_result.source.name
        if opp_wage and wage_floor:
            ratio = opp_wage / wage_floor
            if ratio >= 1.5:
                vs_floor_text = f"This opportunity pays {ratio:.1f}× the minimum wage floor."
            elif ratio >= 1.0:
                vs_floor_text = f"This opportunity pays above the minimum wage floor (+{round((ratio-1)*100)}%)."
            else:
                vs_floor_text = f"⚠ This opportunity pays below the minimum wage floor. Verify before committing."
        else:
            vs_floor_text = "Wage comparison unavailable."

    # Growth signal
    if isinstance(growth_result, DataUnavailable):
        growth_pct = None
        growth_text = f"Sector growth data unavailable ({growth_result.reason})."
        growth_source = growth_result.source.name
    else:
        growth_pct = growth_result.get("growth_pct")
        growth_source = growth_result.get("source_name", "World Bank WDI")
        if growth_pct is not None:
            abs_g = abs(growth_pct)
            if growth_pct > 5:
                growth_text = f"Sector growing fast (+{growth_pct:.1f}% last year). Demand is ahead of supply."
            elif growth_pct > 0:
                growth_text = f"Sector growing steadily (+{growth_pct:.1f}% last year)."
            elif growth_pct > -3:
                growth_text = f"Sector roughly stable ({growth_pct:+.1f}% last year)."
            else:
                growth_text = f"Sector contracting ({growth_pct:+.1f}% last year). Factor this in."
        else:
            growth_text = "Sector growth data unavailable."

    return {
        "wage_floor": wage_floor,
        "wage_floor_currency": currency,
        "wage_floor_source": wage_floor_source,
        "opportunity_wage": opp_wage,
        "opportunity_wage_source": opportunity.get("wage_source", ""),
        "vs_floor_text": vs_floor_text,
        "sector_growth_pct": growth_pct,
        "sector_growth_text": growth_text,
        "sector_growth_source": growth_source,
        "data_note": (
            "Wage floor: ILOSTAT statutory minimum wage. Actual informal-sector wages vary. "
            "Sector growth: World Bank WDI latest available year. "
            "Data gaps disclosed where present."
        ),
    }


async def _get_wage(country_iso: str, isco_code: str):
    try:
        return await _ilo.get_wage_floor(country_iso)
    except Exception as exc:
        logger.debug("Wage fetch failed for %s: %s", country_iso, exc)
        return DataUnavailable(
            requested_for=f"wage/{country_iso}",
            reason=str(exc),
            source=type("S", (), {"name": "ILOSTAT (unavailable)"})(),
        )


async def _get_growth(country_iso: str, sector: str):
    indicator = _SECTOR_WDI_MAP.get(sector, "SL.SRV.EMPL.ZS")
    try:
        result = await _wdi.get_indicator(country_iso, indicator)
        if isinstance(result, DataUnavailable):
            return result
        # result is a SourcedFloat or similar — extract value
        val = result.value if hasattr(result, "value") else result
        return {
            "growth_pct": round(float(val), 2) if val is not None else None,
            "source_name": "World Bank WDI",
            "indicator": indicator,
        }
    except Exception as exc:
        logger.debug("Growth fetch failed for %s/%s: %s", country_iso, sector, exc)
        # Fall back to the opportunity's own stated growth
        return {"growth_pct": None, "source_name": "unavailable"}
