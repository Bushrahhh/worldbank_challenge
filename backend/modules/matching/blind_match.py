"""
Module 3 — Matching: Blind Matching for Employers

Employer sees skills — not name, gender, age, or location — until they
explicitly request a reveal. Reduces first-impression discrimination.
Surfaces the signal that actually matters: what can this person do?

The reveal mechanism uses a time-limited token so the candidate controls
when and to whom their identity is disclosed.

Design:
- Blind profile = ISCO codes + skill labels + evidence tier + heritage flags
- PII stripped: no name, no age, no gender, no phone, no photo
- Candidate identified only by an opaque handle (e.g. "Candidate #A3F7")
- Reveal token: HMAC-SHA256 signed, 48-hour TTL
- Employer "requests reveal" → candidate gets notified (Telegram/SMS)
- Candidate approves → reveal token activated → employer sees name + contact
"""

import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Token TTL in seconds (48 hours)
_TOKEN_TTL = 48 * 3600

_SECRET_KEY = os.getenv("BLIND_MATCH_SECRET", secrets.token_hex(32))


# ---------------------------------------------------------------------------
# Blind profile builder
# ---------------------------------------------------------------------------

# Evidence tier labels (what employer sees — no PII, just quality signal)
_EVIDENCE_LABELS = {
    "employer_verified": "Employer-verified",
    "peer_vouched": "Peer-vouched",
    "assessed": "Assessed by navigator",
    "self_report": "Self-reported",
}

_EVIDENCE_RANK = {
    "employer_verified": 4,
    "peer_vouched": 3,
    "assessed": 2,
    "self_report": 1,
}


def build_blind_profile(
    passport_uuid: str,
    receipts: list[dict],
    country_iso: str,
    education_level: Optional[str] = None,
) -> dict:
    """
    Build an employer-facing blind profile from a Skills Passport.

    Args:
        passport_uuid: internal passport ID (NOT shown to employer)
        receipts: list of SkillReceipt dicts
        country_iso: ISO code for context
        education_level: education tier label (e.g. "secondary_complete")

    Returns:
        dict with opaque_handle, skills_summary, evidence_tier, heritage_count,
        isco_groups, profile_strength — no PII.
    """
    # Deterministic but opaque handle — same passport always gets same handle
    # so employers can refer back without knowing who it is
    handle_hash = hashlib.sha256(
        f"{passport_uuid}:{_SECRET_KEY}".encode()
    ).hexdigest()[:6].upper()
    opaque_handle = f"Candidate #{handle_hash}"

    # Skill summary — labels and ESCO codes only
    skills_by_evidence: dict[str, list[dict]] = {}
    heritage_skills = []
    isco_groups: set[str] = set()

    for r in receipts:
        et = r.get("evidence_type", "self_report")
        tier_label = _EVIDENCE_LABELS.get(et, "Self-reported")

        skill_entry = {
            "label": r.get("skill_label", ""),
            "esco_code": r.get("esco_code", ""),
            "confidence": r.get("confidence", 0.5),
            "is_heritage": r.get("is_heritage_skill", False),
        }

        if tier_label not in skills_by_evidence:
            skills_by_evidence[tier_label] = []
        skills_by_evidence[tier_label].append(skill_entry)

        if r.get("is_heritage_skill"):
            heritage_skills.append(r.get("skill_label", ""))

        if r.get("isco_code"):
            # Show only major group (1 digit) — reduces discrimination by occupation
            major = r["isco_code"][0]
            isco_groups.add(major)

    # Overall evidence tier = highest tier present
    max_rank = max(
        (_EVIDENCE_RANK.get(r.get("evidence_type", "self_report"), 1) for r in receipts),
        default=1,
    )
    overall_tier = {4: "Employer-verified", 3: "Peer-vouched", 2: "Assessed", 1: "Self-reported"}.get(max_rank, "Self-reported")

    # Profile strength score (0–100) — shown to employer as signal quality
    strength = _profile_strength(receipts)

    # ISCO group labels (not codes — reduces specific occupation discrimination)
    _ISCO_MAJOR_LABELS = {
        "1": "Management & Leadership",
        "2": "Professional & Technical",
        "3": "Associate Professional",
        "4": "Clerical & Administrative",
        "5": "Service & Sales",
        "6": "Agricultural & Environmental",
        "7": "Trades & Craft",
        "8": "Plant & Machine Operations",
        "9": "Elementary Occupations",
    }
    isco_group_labels = [_ISCO_MAJOR_LABELS.get(g, f"Group {g}") for g in sorted(isco_groups)]

    return {
        "opaque_handle": opaque_handle,
        "country_iso": country_iso,
        "education_level": education_level or "not_disclosed",
        "skills_by_evidence_tier": skills_by_evidence,
        "heritage_skills_count": len(heritage_skills),
        "heritage_skill_labels": heritage_skills,
        "isco_group_labels": isco_group_labels,
        "overall_evidence_tier": overall_tier,
        "profile_strength": strength,
        "total_skills": len(receipts),
        "meta": {
            "pii_stripped": True,
            "fields_hidden": ["name", "age", "gender", "phone", "location", "photo"],
            "reveal_available": True,
            "reveal_note": (
                "To request candidate identity, use the reveal endpoint. "
                "The candidate will be notified and must approve."
            ),
        },
    }


def _profile_strength(receipts: list[dict]) -> int:
    """0–100 score based on number of skills, evidence tiers, and heritage coverage."""
    if not receipts:
        return 0

    skill_score = min(len(receipts) * 10, 40)

    tier_scores = [_EVIDENCE_RANK.get(r.get("evidence_type", "self_report"), 1) for r in receipts]
    avg_tier = sum(tier_scores) / len(tier_scores)
    evidence_score = int(avg_tier / 4 * 40)  # max 40

    heritage_score = 10 if any(r.get("is_heritage_skill") for r in receipts) else 0

    diversity_score = min(len({r.get("isco_code", "")[:1] for r in receipts}) * 2, 10)

    return min(skill_score + evidence_score + heritage_score + diversity_score, 100)


# ---------------------------------------------------------------------------
# Reveal token management
# ---------------------------------------------------------------------------

def generate_reveal_token(passport_uuid: str, employer_id: str) -> dict:
    """
    Generate a time-limited reveal token for a specific employer request.

    The token is HMAC-signed with the server secret.
    Valid for 48 hours. Single use (enforced at API layer).
    """
    issued_at = int(time.time())
    expires_at = issued_at + _TOKEN_TTL
    nonce = secrets.token_hex(8)

    payload = f"{passport_uuid}:{employer_id}:{issued_at}:{nonce}"
    signature = hmac.new(
        _SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    token = f"{payload}:{signature}"
    # Base64-safe encoding: replace : with - for URL safety
    token_safe = token.replace(":", ".")

    return {
        "token": token_safe,
        "expires_at": expires_at,
        "issued_at": issued_at,
        "passport_uuid": passport_uuid,
        "employer_id": employer_id,
        "ttl_hours": 48,
        "note": (
            "This token requests identity disclosure. "
            "The candidate will be notified and must approve before any PII is shared."
        ),
    }


def verify_reveal_token(token_safe: str) -> Optional[dict]:
    """
    Verify a reveal token. Returns parsed payload if valid, None if invalid/expired.
    """
    try:
        token = token_safe.replace(".", ":")
        parts = token.rsplit(":", 1)
        if len(parts) != 2:
            return None
        payload, provided_sig = parts

        expected_sig = hmac.new(
            _SECRET_KEY.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(provided_sig, expected_sig):
            logger.warning("Reveal token signature mismatch")
            return None

        p_parts = payload.split(":")
        if len(p_parts) != 4:
            return None

        passport_uuid, employer_id, issued_at_str, nonce = p_parts
        issued_at = int(issued_at_str)
        expires_at = issued_at + _TOKEN_TTL

        if time.time() > expires_at:
            logger.info("Reveal token expired for passport %s", passport_uuid)
            return None

        return {
            "passport_uuid": passport_uuid,
            "employer_id": employer_id,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "valid": True,
        }
    except Exception as exc:
        logger.debug("Reveal token parse error: %s", exc)
        return None


def build_revealed_profile(
    passport_uuid: str,
    receipts: list[dict],
    holder_name: str,
    country_iso: str,
    contact_hint: Optional[str] = None,
) -> dict:
    """
    Build the post-reveal profile that the employer sees after candidate approval.
    Still omits phone/email unless candidate explicitly included them.
    """
    blind = build_blind_profile(passport_uuid, receipts, country_iso)
    blind["revealed"] = True
    blind["holder_name"] = holder_name
    blind["contact_hint"] = contact_hint or "Contact via UNMAPPED platform"
    blind["meta"]["pii_stripped"] = False
    blind["meta"]["fields_hidden"] = []
    blind["meta"]["reveal_note"] = "Identity disclosed with candidate approval."
    return blind
