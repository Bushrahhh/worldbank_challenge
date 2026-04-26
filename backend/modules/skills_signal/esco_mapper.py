"""
ESCO Mapper

Maps extracted skill descriptions to ESCO taxonomy codes using Groq LLM + ESCO API.
Falls back to keyword-based ISCO mapping if API is unavailable.
"""

import json
import logging
import os
from typing import Optional

from backend.adapters.esco import ESCOAdapter
from backend.models.sourced_data import DataUnavailable

logger = logging.getLogger(__name__)

# Lightweight ISCO-08 fallback map — used when ESCO API is down
# Maps keyword patterns → (isco_code, isco_label)
ISCO_KEYWORD_MAP: list[tuple[list[str], str, str]] = [
    (["phone", "mobile", "screen", "electronics repair", "device"], "7422", "Electronics mechanics and servicers"),
    (["solar", "panel", "photovoltaic", "off-grid"], "7411", "Building and related electricians"),
    (["motorcycle", "motorbike", "vehicle", "engine", "mechanic"], "7231", "Motor vehicle mechanics"),
    (["sew", "tailor", "dress", "stitch", "fabric", "cloth"], "7531", "Tailors and dressmakers"),
    (["farm", "crop", "plant", "harvest", "agriculture", "cocoa", "maize"], "6111", "Field crop and vegetable growers"),
    (["cook", "food", "kitchen", "catering", "prepare food"], "5120", "Cooks"),
    (["teach", "tutor", "education", "school", "lesson", "class"], "2341", "Primary school teachers"),
    (["sell", "sales", "market", "trade", "shop", "retail"], "5220", "Shop salespersons"),
    (["drive", "taxi", "transport", "delivery", "car", "bus"], "8322", "Car, taxi and van drivers"),
    (["security", "guard", "watch", "protect"], "5414", "Security guards"),
    (["clean", "household", "domestic", "washing", "laundry"], "9111", "Domestic cleaners and helpers"),
    (["construction", "build", "brick", "concrete", "site"], "9312", "Civil engineering labourers"),
    (["carpenter", "wood", "furniture", "joinery"], "7115", "Carpenters and joiners"),
    (["weld", "metal", "fabricat", "steel", "iron"], "7212", "Welders and flamecutters"),
    (["health", "nurse", "care", "patient", "medical", "community health"], "3253", "Community health workers"),
    (["account", "bookkeep", "finance", "money management", "records"], "4311", "Accounting and bookkeeping clerks"),
    (["plumb", "pipe", "water", "sanitation", "drainage"], "7124", "Plumbers and pipe fitters"),
    (["electrician", "wiring", "cable", "electrical"], "7411", "Building and related electricians"),
]


def keyword_isco_fallback(skill_description: str) -> tuple[Optional[str], Optional[str]]:
    """
    Keyword-based ISCO fallback when ESCO API is unavailable.
    Returns (isco_code, isco_label) or (None, None).
    """
    text = skill_description.lower()
    for keywords, code, label in ISCO_KEYWORD_MAP:
        if any(kw in text for kw in keywords):
            return code, label
    return None, None


async def map_skill_to_esco(
    skill_description: str,
    context: Optional[str] = None,
) -> dict:
    """
    Map a skill description to ESCO taxonomy.
    Returns {esco_code, esco_uri, isco_code, isco_label, confidence, source}.
    """
    adapter = ESCOAdapter()

    # Try ESCO API first
    query = f"{skill_description} {context or ''}".strip()
    results = await adapter.search_skills(query, language="en", limit=5)

    if isinstance(results, list) and results:
        top = results[0]
        isco = top.isco_groups[0] if top.isco_groups else None
        # Supplement with keyword fallback if no ISCO from ESCO
        if not isco:
            isco, _ = keyword_isco_fallback(skill_description)
        return {
            "esco_uri": top.uri,
            "esco_label": top.preferred_label,
            "isco_code": isco,
            "confidence": 0.80,
            "source": "esco_api",
        }

    # ESCO API unavailable — use keyword fallback
    isco_code, isco_label = keyword_isco_fallback(skill_description)
    if isco_code:
        return {
            "esco_uri": None,
            "esco_label": skill_description,
            "isco_code": isco_code,
            "confidence": 0.55,
            "source": "keyword_fallback",
        }

    return {
        "esco_uri": None,
        "esco_label": skill_description,
        "isco_code": None,
        "confidence": 0.40,
        "source": "unmatched",
    }
