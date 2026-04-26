"""
config_loader.py — UNMAPPED country configuration singleton

The entire application reads from one active config. Country is selected via the
ACTIVE_COUNTRY environment variable. No module should ever hard-code a country
name, currency, credential level, or data endpoint.

Usage:
    from backend.config_loader import get_config
    cfg = get_config()
    currency = cfg.country.currency          # "GHS" or "BDT" etc.
    informal_share = cfg.labor_market.informal_sector_share

Swap countries:
    ACTIVE_COUNTRY=ghana ...     → loads configs/ghana.yaml
    ACTIVE_COUNTRY=bangladesh ... → loads configs/bangladesh.yaml
"""

import os
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Project root resolved relative to this file ─────────────────────────────
_ROOT = Path(__file__).parent.parent


# ── Pydantic models for config validation ───────────────────────────────────

class CountryConfig(BaseModel):
    iso_code: str
    name: str
    name_local: str
    currency: str
    currency_symbol: str
    region: str
    context: str


class LanguageConfig(BaseModel):
    primary: str
    secondary: list[str] = Field(default_factory=list)
    rtl: bool = False
    script: str = "latin"
    ui_strings_path: str
    voice_languages: list[str] = Field(default_factory=list)


class LaborMarketConfig(BaseModel):
    wage_source: str
    wage_endpoint: str
    sector_classification: str
    informal_sector_share: float
    informal_sector_share_source: str
    youth_unemployment_rate: float
    youth_unemployment_source: str
    dominant_sectors: list[str] = Field(default_factory=list)
    growing_sectors: list[str] = Field(default_factory=list)
    geo_unit: str = "district"


class EducationLevel(BaseModel):
    id: str
    label: str
    years: int
    isced: int
    credential: Optional[str] = None


class EducationTaxonomy(BaseModel):
    levels: list[EducationLevel]
    credential_mapping_path: str


class AutomationCalibration(BaseModel):
    baseline: str
    infrastructure_adjustment: float
    infrastructure_adjustment_rationale: str
    infrastructure_adjustment_source: str
    informal_economy_adjustment: float
    informal_economy_adjustment_rationale: str
    informal_economy_adjustment_source: str
    combined_calibration_formula: str
    worked_example: dict[str, Any]


class OpportunityTypes(BaseModel):
    formal_employment: bool = True
    self_employment: bool = True
    gig: bool = False
    training_pathways: bool = True
    apprenticeships: bool = False
    cooperative: bool = False


class PeerVouching(BaseModel):
    sms_enabled: bool = False
    short_code: str = "UNMAPPED"
    verification_message_template: str
    language: str = "en"


class DataGap(BaseModel):
    id: str
    severity: str   # low | medium | high
    affects: list[str]
    disclosure: str
    source_used: str


class UnmappedConfig(BaseModel):
    """Root configuration object — represents one country's entire context."""
    country: CountryConfig
    language: LanguageConfig
    labor_market: LaborMarketConfig
    education_taxonomy: EducationTaxonomy
    automation_calibration: AutomationCalibration
    opportunity_types: OpportunityTypes
    peer_vouching: PeerVouching
    data_gaps: list[DataGap] = Field(default_factory=list)


# ── Loader ───────────────────────────────────────────────────────────────────

def _resolve_config_path(country_key: str) -> Path:
    """Resolve the YAML file path for a given country key."""
    key = country_key.strip().lower()
    path = _ROOT / "configs" / f"{key}.yaml"
    if not path.exists():
        available = [p.stem for p in (_ROOT / "configs").glob("*.yaml")]
        raise FileNotFoundError(
            f"No config found for country '{key}'. "
            f"Available: {available}. "
            f"Create configs/{key}.yaml to add support for this country."
        )
    return path


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def get_config() -> UnmappedConfig:
    """
    Load and cache the active country configuration.

    Country is selected via ACTIVE_COUNTRY env var (default: ghana).
    The result is cached after first load — restart the process to swap.
    For tests, call get_config.cache_clear() before each test.
    """
    country_key = os.environ.get("ACTIVE_COUNTRY", "ghana")
    config_path = _resolve_config_path(country_key)
    raw = _load_yaml(config_path)

    logger.info(
        "UNMAPPED config loaded | country=%s | path=%s",
        country_key,
        config_path,
    )
    _log_data_gaps(raw.get("data_gaps", []), country_key)

    return UnmappedConfig(**raw)


def _log_data_gaps(gaps: list[dict], country: str) -> None:
    """Emit a startup warning for every known data gap — these become UI tooltips."""
    for gap in gaps:
        severity = gap.get("severity", "unknown").upper()
        gid = gap.get("id", "?")
        disclosure = gap.get("disclosure", "").strip().replace("\n", " ")
        logger.warning(
            "[DATA GAP %s] [%s/%s] %s | source: %s",
            severity,
            country,
            gid,
            disclosure,
            gap.get("source_used", "unknown"),
        )


def get_data_gaps_for_feature(feature: str) -> list[DataGap]:
    """
    Return all data gaps that affect a given feature — used to render
    source-citation tooltips in the UI.

    Example:
        gaps = get_data_gaps_for_feature("wage_floor")
    """
    cfg = get_config()
    return [gap for gap in cfg.data_gaps if feature in gap.affects]


def calibrate_automation_score(frey_osborne_score: float) -> dict:
    """
    Apply the country-specific calibration to a raw Frey-Osborne score.

    Returns a dict suitable for the "89% → 12%, here's why" UI moment:
        {
            "baseline": 0.89,
            "infrastructure_adjusted": 0.623,
            "calibrated": 0.374,
            "calibration_factors": {...},
            "data_gaps": [...],
        }
    """
    cfg = get_config()
    cal = cfg.automation_calibration

    infra_adj = frey_osborne_score * cal.infrastructure_adjustment
    calibrated = infra_adj * cal.informal_economy_adjustment

    return {
        "baseline": round(frey_osborne_score, 3),
        "infrastructure_adjusted": round(infra_adj, 3),
        "calibrated": round(calibrated, 3),
        "calibration_factors": {
            "infrastructure_adjustment": cal.infrastructure_adjustment,
            "infrastructure_adjustment_source": cal.infrastructure_adjustment_source,
            "informal_economy_adjustment": cal.informal_economy_adjustment,
            "informal_economy_adjustment_source": cal.informal_economy_adjustment_source,
        },
        "formula": cal.combined_calibration_formula,
        "data_gaps": [g.model_dump() for g in get_data_gaps_for_feature("automation_risk")],
    }
