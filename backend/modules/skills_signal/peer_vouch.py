"""
Peer Vouching via SMS (mock for demo; Twilio in production)

A customer texts a short code to verify "yes, Amara fixed my phone."
Social proof as informal credential. Upgrades receipt evidence_type:
  self_report → peer_vouched

Demo: the "verify" button in Telegram triggers the same webhook flow.
Production: Twilio webhook receives the SMS and calls /skills/vouch/{token}.
"""

import hashlib
import logging
import os
from datetime import datetime
from typing import Optional

from backend.modules.skills_signal.receipts import generate_vouch_token, upgrade_evidence_type

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")

DEMO_MODE = not bool(TWILIO_ACCOUNT_SID)


def hash_phone(phone: str) -> str:
    """One-way hash of a phone number for privacy (we store hash, not number)."""
    return hashlib.sha256(phone.strip().encode()).hexdigest()[:32]


def build_vouch_sms(
    holder_name: str,
    service_description: str,
    token: str,
    country_config,
) -> str:
    """Build the SMS text sent to a voucher."""
    # Use country-specific template if available
    template = country_config.peer_vouching.verification_message_template
    msg = template.format(
        holder_name=holder_name,
        service_description=service_description,
    )
    return f"{msg}\n\nVerification code: {token}\nReply YES {token} to verify."


async def send_vouch_request(
    voucher_phone: str,
    holder_name: str,
    service_description: str,
    token: str,
    country_config,
) -> dict:
    """
    Send a peer vouch request SMS. Returns {sent, method, message}.
    In demo mode: returns mock success without sending.
    """
    sms_text = build_vouch_sms(holder_name, service_description, token, country_config)

    if DEMO_MODE:
        logger.info(
            "[PEER VOUCH MOCK] Would send to %s: %s",
            voucher_phone[:6] + "****",
            sms_text[:80],
        )
        return {
            "sent": True,
            "method": "mock",
            "message": sms_text,
            "token": token,
            "demo_note": (
                "Demo mode: no SMS sent. "
                "Tap 'Verify' in the Telegram bot to simulate the response."
            ),
        }

    # Production: Twilio
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=sms_text,
            from_=TWILIO_FROM_NUMBER,
            to=voucher_phone,
        )
        logger.info("Vouch SMS sent: SID=%s", message.sid)
        return {"sent": True, "method": "twilio", "sid": message.sid}
    except Exception as exc:
        logger.error("Twilio send failed: %s", exc)
        return {"sent": False, "method": "twilio", "error": str(exc)}


def confirm_vouch(token: str, reply: str) -> bool:
    """
    Parse a SMS reply to confirm or reject a vouch.
    Accepts: YES <token>, Y, CONFIRM, 1
    """
    cleaned = reply.strip().upper()
    if cleaned.startswith("YES"):
        # Check token matches if included
        parts = cleaned.split()
        if len(parts) == 1 or (len(parts) == 2 and parts[1] == token.upper()):
            return True
    return cleaned in ("Y", "CONFIRM", "1", "OK")


def generate_demo_vouch_link(base_url: str, token: str) -> str:
    """Generate a demo vouch link for the Telegram bot 'Verify' button."""
    return f"{base_url}/skills/vouch/{token}?demo=1"
