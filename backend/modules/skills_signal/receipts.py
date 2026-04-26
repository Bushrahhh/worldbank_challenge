"""
Skills Receipts Engine

Each claimed skill generates a verifiable receipt. A stack of receipts = Skills Passport.
The receipt metaphor is native to informal economies — market traders already use receipts.

Receipt lifecycle:
  self_report  →  peer_vouched  →  employer_verified
       |
  assessed (via test/demonstration)
"""

import hashlib
import json
import secrets
from datetime import datetime
from typing import Optional

from backend.modules.skills_signal.heritage_skills import HeritageSkill


def make_receipt_dict(
    skill_label: str,
    esco_code: Optional[str],
    isco_code: Optional[str],
    confidence: float,
    evidence_text: Optional[str] = None,
    heritage_skill: Optional[HeritageSkill] = None,
    evidence_type: str = "self_report",
) -> dict:
    """
    Create a receipt dict — the canonical JSON representation of a claimed skill.
    This is what goes into the passport payload.
    """
    return {
        "skill_label": skill_label,
        "esco_code": esco_code,
        "isco_code": isco_code,
        "evidence_type": evidence_type,
        "verified_by": None,
        "confidence": round(min(max(confidence, 0.0), 1.0), 3),
        "is_heritage_skill": heritage_skill is not None,
        "heritage_skill_id": heritage_skill.id if heritage_skill else None,
        "evidence_text": evidence_text,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def generate_vouch_token() -> str:
    """Generate a short, SMS-friendly verification token."""
    return secrets.token_hex(4).upper()  # e.g. "A3F9B2C1"


def compute_receipt_hash(receipt: dict) -> str:
    """
    Deterministic hash of a receipt for integrity checking.
    Excludes verified_by (which changes over time).
    """
    stable = {k: v for k, v in receipt.items() if k not in ("verified_by", "timestamp")}
    canonical = json.dumps(stable, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def upgrade_evidence_type(current: str) -> str:
    """Return the next evidence_type in the trust chain."""
    chain = ["self_report", "peer_vouched", "employer_verified"]
    try:
        idx = chain.index(current)
        return chain[min(idx + 1, len(chain) - 1)]
    except ValueError:
        return current


def confidence_label(confidence: float) -> str:
    """Human-readable confidence label for UI display."""
    if confidence >= 0.85:
        return "strong evidence"
    elif confidence >= 0.65:
        return "good evidence"
    elif confidence >= 0.45:
        return "some evidence"
    else:
        return "self-reported"


def evidence_type_label(evidence_type: str) -> str:
    """Human-readable evidence type for the Skills Passport UI."""
    labels = {
        "self_report": "Self-reported",
        "peer_vouched": "Peer-verified",
        "employer_verified": "Employer-verified",
        "assessed": "Assessed",
    }
    return labels.get(evidence_type, evidence_type)
