"""
Skills Passport Assembly

Assembles the portable, verifiable Skills Passport from a stack of receipts.
Signs with ed25519. Generates QR code. Returns shareable link.

Passport structure: see ARCHITECTURE.md — Skills Passport Packet diagram.
"""

import base64
import io
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

import qrcode
import qrcode.image.svg
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

logger = logging.getLogger(__name__)


def generate_keypair() -> tuple[Ed25519PrivateKey, str, str]:
    """
    Generate an ed25519 keypair for a new passport holder.
    Returns (private_key, public_key_b64, private_key_b64).
    """
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    pub_bytes = public_key.public_bytes_raw()
    priv_bytes = private_key.private_bytes_raw()

    return (
        private_key,
        base64.b64encode(pub_bytes).decode(),
        base64.b64encode(priv_bytes).decode(),
    )


def sign_passport(payload: dict, private_key: Ed25519PrivateKey) -> str:
    """
    Sign the passport payload with ed25519.
    Returns base64-encoded signature.
    """
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    sig_bytes = private_key.sign(canonical.encode())
    return base64.b64encode(sig_bytes).decode()


def verify_passport(payload: dict, signature_b64: str, public_key_b64: str) -> bool:
    """Verify a passport signature. Returns True if valid."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.asymmetric import ed25519

        pub_bytes = base64.b64decode(public_key_b64)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        sig_bytes = base64.b64decode(signature_b64)
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        public_key.verify(sig_bytes, canonical.encode())
        return True
    except Exception:
        return False


def assemble_passport(
    user_id: int,
    country_iso: str,
    receipts: list[dict],
    education_level: Optional[str] = None,
    languages: Optional[list[str]] = None,
    private_key: Optional[Ed25519PrivateKey] = None,
    public_key_b64: Optional[str] = None,
) -> dict:
    """
    Assemble a complete Skills Passport from receipts.
    Signs if a keypair is provided.
    """
    passport_id = str(uuid.uuid4())
    issued_at = datetime.utcnow().isoformat() + "Z"

    payload = {
        "passport_id": passport_id,
        "issued_at": issued_at,
        "issuer": "unmapped/v1",
        "schema_version": "1.0",
        "country_iso": country_iso,
        "holder_key": public_key_b64,
        "skills": receipts,
        "context": {
            "education_level": education_level,
            "country_iso": country_iso,
            "languages": languages or ["en"],
        },
    }

    if private_key and public_key_b64:
        # Sign the payload (excluding signature field itself)
        signable = {k: v for k, v in payload.items() if k != "signature"}
        payload["signature"] = sign_passport(signable, private_key)
    else:
        payload["signature"] = None

    return payload


def generate_qr_code(data: str, size: int = 10) -> bytes:
    """
    Generate a QR code PNG for the given data (URL or JSON).
    Returns PNG bytes.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=size,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_qr_svg(data: str) -> str:
    """Generate a QR code as SVG string (for embedding in web pages)."""
    factory = qrcode.image.svg.SvgImage
    qr = qrcode.make(data, image_factory=factory)
    buffer = io.BytesIO()
    qr.save(buffer)
    return buffer.getvalue().decode("utf-8")


def passport_to_shareable_text(passport: dict, base_url: str = "") -> str:
    """
    Format a Skills Passport as a human-readable shareable text
    (for WhatsApp, SMS, etc. when a link isn't available).
    """
    skills = passport.get("skills", [])
    lines = [
        "UNMAPPED Skills Passport",
        f"Issued: {passport['issued_at'][:10]}",
        f"Country: {passport['country_iso']}",
        "",
        f"{len(skills)} verified skills:",
    ]
    for i, skill in enumerate(skills, 1):
        evidence = skill.get("evidence_type", "self_report").replace("_", " ")
        lines.append(f"  {i}. {skill['skill_label']} ({evidence})")

    if base_url and passport.get("passport_id"):
        lines.append(f"\nVerify: {base_url}/passport/{passport['passport_id']}")

    return "\n".join(lines)


def passport_summary(passport: dict) -> dict:
    """Return a summary suitable for Telegram message display."""
    skills = passport.get("skills", [])
    heritage = [s for s in skills if s.get("is_heritage_skill")]
    verified = [s for s in skills if s.get("evidence_type") != "self_report"]

    return {
        "passport_id": passport.get("passport_id", ""),
        "issued_at": (passport.get("issued_at") or "")[:10],
        "total_skills": len(skills),
        "heritage_skills": len(heritage),
        "verified_skills": len(verified),
        "top_skills": [s["skill_label"] for s in skills[:3]],
        "is_signed": passport.get("signature") is not None,
    }
