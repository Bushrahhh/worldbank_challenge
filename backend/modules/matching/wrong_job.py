"""
Module 3 — Matching: The Wrong Job Feature

"This is wrong for you — here's why."

A system willing to say 'no' is trusted when it says 'yes.'
This module picks the most instructive mismatch and explains it clearly.

Rules for selecting the wrong job:
  1. Skill overlap < 35% OR a critical barrier is present in wrong_if.
  2. The job looks plausible on the surface (same sector or ISCO major group).
  3. We explain the barrier — never just say "not a good fit."

Uses Groq LLM for the explanation when available; falls back to a
rule-based template that is equally honest.
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

_OPPORTUNITIES_PATH = Path(__file__).parent.parent.parent.parent / "data" / "opportunities.yaml"

# ---------------------------------------------------------------------------
# Barrier detection — rule-based
# ---------------------------------------------------------------------------

_BARRIER_PATTERNS = {
    "capital_required": [
        "capital", "float", "upfront", "minimum", "investment", "GHS", "BDT",
    ],
    "location_constraint": [
        "Accra", "Kumasi", "remote", "rural", "30km", "80km", "field", "travel",
        "village", "mobility", "motorcycle",
    ],
    "credential_gap": [
        "degree", "certificate required", "license", "teaching certificate",
        "CompTIA", "NVTI", "BGMEA",
    ],
    "portfolio_required": [
        "portfolio", "creative", "subjective", "3–6 months",
    ],
    "sector_risk": [
        "hazard", "PPE", "chemical", "fire safety", "overtime",
    ],
    "hiring_slow": [
        "slow", "6–18 months", "government hiring",
    ],
}


def _detect_barriers(wrong_if_text: str) -> list[str]:
    barriers = []
    text_lower = wrong_if_text.lower()
    for barrier_type, keywords in _BARRIER_PATTERNS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            barriers.append(barrier_type)
    return barriers


def _rule_based_explanation(
    opportunity: dict,
    receipts: list[dict],
    skill_overlap_pct: int,
    barriers: list[str],
) -> str:
    title = opportunity["title"]
    wrong_if = opportunity.get("wrong_if", "")
    training_months = opportunity.get("training_gap_months", 0)
    opp_wage = opportunity.get("wage_month", 0)
    currency = opportunity.get("currency", "LOCAL")

    parts = [f"**{title}** is not a good match right now — and here is exactly why."]

    if skill_overlap_pct < 35:
        parts.append(
            f"Your current skills cover about {skill_overlap_pct}% of what this role requires. "
            "The gap is real, not insurmountable, but it would take longer than the options we've shown."
        )

    if "capital_required" in barriers:
        parts.append(
            f"There is an upfront capital requirement. {wrong_if} "
            "That's a real barrier — we won't pretend otherwise."
        )
    elif "location_constraint" in barriers:
        parts.append(
            f"Location is the constraint here. {wrong_if} "
            "Unless your situation changes, the practical barrier is too large."
        )
    elif "credential_gap" in barriers:
        parts.append(
            f"A formal credential is a hard requirement for this role. {wrong_if} "
            f"That means {training_months} months before you're eligible — longer than our other matches."
        )
    elif "portfolio_required" in barriers:
        parts.append(
            f"This role rewards a portfolio, not certificates. {wrong_if} "
            "Our other matches will get you income faster."
        )
    elif "hiring_slow" in barriers:
        parts.append(
            f"The hiring cycle is slow. {wrong_if} "
            "The income gap while waiting is real — our other matches are faster paths."
        )
    elif "sector_risk" in barriers:
        parts.append(
            f"There is a health or safety consideration. {wrong_if} "
            "Worth knowing before you spend training time on it."
        )
    else:
        parts.append(wrong_if)

    if opp_wage:
        parts.append(
            f"The wage ({opp_wage:,} {currency}/month) is competitive, "
            "but the barriers above make it the wrong choice for where you are right now."
        )

    parts.append(
        "This is not a judgment on the job or on you. "
        "It is honest information so you can choose better."
    )

    return "\n\n".join(parts)


async def _llm_explanation(
    opportunity: dict,
    receipts: list[dict],
    skill_overlap_pct: int,
    barriers: list[str],
) -> Optional[str]:
    """Generate a more natural explanation via Groq LLM if available."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=api_key)

        user_skills = [r.get("skill_label", "") for r in receipts if r.get("skill_label")]
        barrier_labels = {
            "capital_required": "upfront capital requirement",
            "location_constraint": "location constraint",
            "credential_gap": "credential gap",
            "portfolio_required": "portfolio requirement",
            "sector_risk": "health/safety consideration",
            "hiring_slow": "slow hiring cycle",
        }
        barrier_text = (
            ", ".join(barrier_labels.get(b, b) for b in barriers)
            if barriers else opportunity.get("wrong_if", "poor skill match")
        )

        system_prompt = """You are UNMAPPED's honest matching engine.
Your job is to explain — with respect and without condescension — why a specific opportunity is NOT the right match for a user right now.

Rules:
- Be honest and specific. Name the actual barrier.
- Never say "low-skilled," "vulnerable," or "disadvantaged."
- Never say "unfortunately." Say what is true.
- Keep it under 100 words.
- End with one sentence about what IS a better path.
- Speak directly to the user (use "you/your")."""

        user_msg = f"""User skills: {', '.join(user_skills) or 'phone repair, multilingual communication'}
Skill overlap with this job: {skill_overlap_pct}%
Job: {opportunity['title']}
Barrier: {barrier_text}
Wrong_if text from catalog: {opportunity.get('wrong_if', '')}

Explain in plain language why this job is wrong for this user right now."""

        resp = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.4,
            max_tokens=200,
        )
        text = resp.choices[0].message.content.strip()
        return text if text else None

    except Exception as exc:
        logger.debug("LLM wrong-job explanation failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_wrong_job(
    receipts: list[dict],
    country_iso: str,
    scored_opportunities: Optional[list[dict]] = None,
) -> Optional[dict]:
    """
    Find the most instructive wrong-job match and explain it.

    Args:
        receipts: list of SkillReceipt dicts from the passport
        country_iso: active country for filtering
        scored_opportunities: pre-scored list from honest_matcher (optional)

    Returns:
        dict with keys: opportunity, skill_overlap_pct, barriers, explanation
        or None if no instructive mismatch found
    """
    if scored_opportunities:
        # Use pre-scored list — look beyond top 5 with barriers
        candidates = [
            o for o in scored_opportunities
            if o.get("skill_overlap_pct", 100) < 40
            and o.get("wrong_if")
            and o.get("id") not in [r.get("id") for r in scored_opportunities[:5]]
        ]
        if not candidates:
            # Fall back to any with a barrier
            candidates = [o for o in scored_opportunities if o.get("wrong_if")]
        if not candidates:
            return None
        # Sort: want something that LOOKS plausible (medium overlap) but has a barrier
        candidates.sort(key=lambda x: abs(x.get("skill_overlap_pct", 0) - 25))
        candidate = candidates[0]
        opportunity = candidate
        skill_overlap_pct = candidate.get("skill_overlap_pct", 0)
    else:
        # Load from catalog directly
        try:
            raw = yaml.safe_load(_OPPORTUNITIES_PATH.read_text(encoding="utf-8"))
            all_opps = raw.get("opportunities", [])
        except Exception as exc:
            logger.warning("Failed to load opportunities.yaml: %s", exc)
            return None

        filtered = [
            o for o in all_opps
            if o.get("country_iso") in (country_iso, "LMIC") and o.get("wrong_if")
        ]
        if not filtered:
            return None

        # Pick one that looks adjacent but has a real barrier
        user_isco_majors = {r.get("isco_code", "")[:1] for r in receipts if r.get("isco_code")}
        adjacent = [
            o for o in filtered
            if o.get("isco_code", "")[:1] in user_isco_majors
        ]
        opportunity = adjacent[0] if adjacent else filtered[0]
        skill_overlap_pct = 25  # approximate

    barriers = _detect_barriers(opportunity.get("wrong_if", ""))

    # Try LLM explanation, fall back to rule-based
    explanation = await _llm_explanation(opportunity, receipts, skill_overlap_pct, barriers)
    if not explanation:
        explanation = _rule_based_explanation(opportunity, receipts, skill_overlap_pct, barriers)

    return {
        "opportunity_id": opportunity.get("id") or opportunity.get("id", "unknown"),
        "title": opportunity.get("title", ""),
        "sector": opportunity.get("sector", ""),
        "isco_code": opportunity.get("isco_code", ""),
        "income_month": opportunity.get("wage_month", 0),
        "income_currency": opportunity.get("currency", "LOCAL"),
        "training_gap_months": opportunity.get("training_gap_months", 0),
        "skill_overlap_pct": skill_overlap_pct,
        "barriers": barriers,
        "wrong_if_raw": opportunity.get("wrong_if", ""),
        "explanation": explanation,
        "tags": opportunity.get("tags", []),
        "meta": {
            "feature": "wrong_job",
            "note": (
                "This is the one match we deliberately set aside. "
                "A system that only says yes is not useful."
            ),
        },
    }
