"""
Skills Signal Engine — API routes

POST /skills/interview/start     start an interview session
POST /skills/interview/message   send a message and get AI response
POST /skills/voice               transcribe voice and return text
GET  /skills/passport/{id}       get a passport by UUID
GET  /skills/passport/{id}/qr    get passport QR code (PNG)
POST /skills/vouch/{token}       submit peer vouch (mock or real)
GET  /skills/heritage            list all heritage skills
"""

import base64
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config_loader import get_config
from backend.models.db import (
    AsyncSessionLocal,
    InterviewSession,
    PeerVouch,
    SkillReceipt,
    SkillsPassport,
    User,
    get_db,
)
from backend.modules.skills_signal.heritage_skills import HERITAGE_SKILLS
from backend.modules.skills_signal.interview import run_interview_turn, transcribe_voice
from backend.modules.skills_signal.passport import (
    assemble_passport,
    generate_keypair,
    generate_qr_code,
    passport_summary,
    passport_to_shareable_text,
)
from backend.modules.skills_signal.peer_vouch import confirm_vouch, generate_demo_vouch_link
from backend.modules.skills_signal.receipts import (
    generate_vouch_token,
    make_receipt_dict,
    upgrade_evidence_type,
)
from backend.modules.skills_signal.esco_mapper import map_skill_to_esco

logger = logging.getLogger(__name__)
router = APIRouter()

APP_BASE_URL = "http://localhost:8000"


# ── Request/Response schemas ─────────────────────────────────────────────────

class StartInterviewRequest(BaseModel):
    telegram_id: Optional[str] = None
    display_name: Optional[str] = None
    country_iso: Optional[str] = None
    education_level: Optional[str] = None
    languages: Optional[list[str]] = None


class InterviewMessageRequest(BaseModel):
    session_id: int
    message: str
    stage: str = "greeting"


class VouchRequest(BaseModel):
    reply: str = "YES"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_create_user(
    db: AsyncSession,
    telegram_id: Optional[str],
    display_name: Optional[str],
    country_iso: str,
) -> User:
    if telegram_id:
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            return user

    import json
    user = User(
        telegram_id=telegram_id,
        display_name=display_name or "Anonymous",
        country_iso=country_iso,
        languages=json.dumps(["en"]),
    )
    db.add(user)
    await db.flush()
    return user


async def _receipts_to_dicts(db: AsyncSession, passport_id: int) -> list[dict]:
    result = await db.execute(
        select(SkillReceipt).where(SkillReceipt.passport_id == passport_id)
    )
    receipts = result.scalars().all()
    return [
        {
            "skill_label": r.skill_label,
            "esco_code": r.esco_code,
            "isco_code": r.isco_code,
            "evidence_type": r.evidence_type,
            "verified_by": r.verified_by,
            "confidence": r.confidence,
            "is_heritage_skill": r.is_heritage_skill,
            "heritage_skill_id": r.heritage_skill_id,
            "evidence_text": r.evidence_text,
            "timestamp": r.timestamp.isoformat() + "Z",
        }
        for r in receipts
    ]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/interview/start")
async def start_interview(
    req: StartInterviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Start a new AI skills interview session."""
    cfg = get_config()
    country = req.country_iso or cfg.country.iso_code

    user = await _get_or_create_user(db, req.telegram_id, req.display_name, country)

    session = InterviewSession(user_id=user.id, stage="greeting")
    db.add(session)
    await db.flush()

    # Run the first AI turn (no user message yet)
    turn = await run_interview_turn([], "", stage="greeting")

    session.add_message("assistant", turn["message"])
    session.stage = turn.get("stage", "greeting")
    await db.commit()

    return {
        "session_id": session.id,
        "message": turn["message"],
        "stage": turn.get("stage", "greeting"),
    }


@router.post("/interview/message")
async def interview_message(
    req: InterviewMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a message in an active interview session."""
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == req.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status == "complete":
        raise HTTPException(400, "Interview already complete — use /passport to view results")

    messages = session.get_messages()
    session.add_message("user", req.message)

    turn = await run_interview_turn(messages, req.message, stage=req.stage or session.stage)

    session.add_message("assistant", turn["message"])
    session.stage = turn.get("stage", session.stage)

    # Persist any extracted skills to the DB as receipts
    extracted = turn.get("extracted_skills", [])
    receipt_dicts = []

    if extracted:
        # Get or create passport for this session's user
        passport = await _get_or_create_passport(db, session.user_id)

        # Load existing skill labels to prevent duplicates
        existing_result = await db.execute(
            select(SkillReceipt.skill_label).where(SkillReceipt.passport_id == passport.id)
        )
        existing_labels = {row[0].lower() for row in existing_result.all()}

        for skill_data in extracted:
            label = skill_data.get("label", "Unknown skill")
            if label.lower() in existing_labels:
                continue  # skip duplicate

            # ESCO mapping (async)
            mapping = await map_skill_to_esco(label, skill_data.get("evidence", ""))

            receipt = SkillReceipt(
                passport_id=passport.id,
                skill_label=label,
                esco_code=mapping.get("esco_uri") or skill_data.get("esco_hint"),
                isco_code=mapping.get("isco_code") or skill_data.get("isco_code"),
                evidence_type="self_report",
                confidence=float(skill_data.get("confidence", 0.7)),
                is_heritage_skill=bool(skill_data.get("heritage_skill_id")),
                heritage_skill_id=skill_data.get("heritage_skill_id"),
                evidence_text=skill_data.get("evidence"),
            )
            db.add(receipt)
            existing_labels.add(label.lower())
            receipt_dicts.append(skill_data)

    if turn.get("complete"):
        session.status = "complete"
        from datetime import datetime
        session.completed_at = datetime.utcnow()

    await db.commit()

    response = {
        "message": turn["message"],
        "stage": session.stage,
        "complete": turn.get("complete", False),
        "extracted_skills_count": len(extracted),
    }
    if turn.get("complete"):
        response["next_step"] = "GET /skills/passport to view your Skills Passport"

    return response


@router.post("/voice")
async def voice_transcription(
    audio: UploadFile = File(...),
    language: str = "en",
):
    """Transcribe a voice note using Groq Whisper."""
    audio_bytes = await audio.read()
    text = await transcribe_voice(audio_bytes, language=language)
    if not text:
        raise HTTPException(500, "Transcription failed — check GROQ_API_KEY")
    return {"transcript": text, "language": language}


@router.get("/passport/by_user/{telegram_id}")
async def get_passport_by_user(
    telegram_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the most recent Skills Passport for a Telegram user ID."""
    user_result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    passport_result = await db.execute(
        select(SkillsPassport)
        .where(SkillsPassport.user_id == user.id)
        .order_by(SkillsPassport.issued_at.desc())
    )
    passport_row = passport_result.scalars().first()
    if not passport_row:
        raise HTTPException(404, "No passport found for this user")

    receipts = await _receipts_to_dicts(db, passport_row.id)
    import json
    context = json.loads(passport_row.context_json or "{}")
    return {
        "passport_id": passport_row.passport_uuid,
        "issued_at": passport_row.issued_at.isoformat() + "Z",
        "issuer": "unmapped/v1",
        "schema_version": passport_row.schema_version,
        "country_iso": passport_row.country_iso,
        "holder_key": passport_row.holder_public_key,
        "skills": receipts,
        "context": context,
        "signature": passport_row.signature,
        "summary": passport_summary({"passport_id": passport_row.passport_uuid, "skills": receipts}),
    }


@router.get("/users_with_passports")
async def users_with_passports(db: AsyncSession = Depends(get_db)):
    """
    Return all users who have at least one Skills Passport.
    Used by the monthly check-in job to send nudge messages.
    """
    result = await db.execute(
        select(User, SkillsPassport)
        .join(SkillsPassport, SkillsPassport.user_id == User.id)
        .where(User.telegram_id.isnot(None))
        .order_by(SkillsPassport.issued_at.desc())
    )
    rows = result.unique().all()

    seen_users: set[int] = set()
    output = []
    for user, passport in rows:
        if user.id in seen_users:
            continue
        seen_users.add(user.id)

        receipt_result = await db.execute(
            select(SkillReceipt).where(SkillReceipt.passport_id == passport.id)
        )
        skill_count = len(receipt_result.scalars().all())

        output.append({
            "telegram_id": user.telegram_id,
            "display_name": user.display_name,
            "passport_uuid": passport.passport_uuid,
            "country_iso": passport.country_iso,
            "skill_count": skill_count,
            "last_updated": passport.updated_at.isoformat() + "Z",
        })

    return output


@router.get("/passport/{passport_uuid}")
async def get_passport(
    passport_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a Skills Passport by UUID."""
    result = await db.execute(
        select(SkillsPassport).where(SkillsPassport.passport_uuid == passport_uuid)
    )
    passport_row = result.scalar_one_or_none()
    if not passport_row:
        raise HTTPException(404, "Passport not found")

    receipts = await _receipts_to_dicts(db, passport_row.id)
    import json
    context = json.loads(passport_row.context_json or "{}")

    passport = {
        "passport_id": passport_row.passport_uuid,
        "issued_at": passport_row.issued_at.isoformat() + "Z",
        "issuer": "unmapped/v1",
        "schema_version": passport_row.schema_version,
        "country_iso": passport_row.country_iso,
        "holder_key": passport_row.holder_public_key,
        "skills": receipts,
        "context": context,
        "signature": passport_row.signature,
        "summary": passport_summary({"passport_id": passport_row.passport_uuid, "skills": receipts}),
    }
    return passport


@router.get("/passport/{passport_uuid}/qr")
async def get_passport_qr(passport_uuid: str):
    """Generate a QR code PNG for a passport shareable link."""
    url = f"{APP_BASE_URL}/passport/{passport_uuid}"
    png_bytes = generate_qr_code(url)
    return Response(content=png_bytes, media_type="image/png")


@router.get("/passport/{passport_uuid}/text")
async def get_passport_text(passport_uuid: str, db: AsyncSession = Depends(get_db)):
    """Return a plain-text shareable version of the passport."""
    result = await db.execute(
        select(SkillsPassport).where(SkillsPassport.passport_uuid == passport_uuid)
    )
    passport_row = result.scalar_one_or_none()
    if not passport_row:
        raise HTTPException(404, "Passport not found")
    receipts = await _receipts_to_dicts(db, passport_row.id)
    passport_dict = {"passport_id": passport_row.passport_uuid, "skills": receipts, "country_iso": passport_row.country_iso, "issued_at": passport_row.issued_at.isoformat()}
    text = passport_to_shareable_text(passport_dict, APP_BASE_URL)
    return {"text": text}


@router.post("/vouch/{token}")
async def peer_vouch(
    token: str,
    req: VouchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit a peer vouch response. Upgrades receipt evidence_type."""
    result = await db.execute(
        select(PeerVouch).where(PeerVouch.voucher_token == token)
    )
    vouch_row = result.scalar_one_or_none()
    if not vouch_row:
        raise HTTPException(404, "Vouch token not found or already used")
    if vouch_row.verified:
        return {"status": "already_verified", "message": "This skill has already been peer-verified."}

    confirmed = confirm_vouch(token, req.reply)
    if not confirmed:
        return {"status": "rejected", "message": "Reply not recognized as confirmation."}

    # Upgrade the receipt's evidence type
    receipt_result = await db.execute(
        select(SkillReceipt).where(SkillReceipt.id == vouch_row.receipt_id)
    )
    receipt = receipt_result.scalar_one_or_none()
    if receipt:
        receipt.evidence_type = upgrade_evidence_type(receipt.evidence_type)
        receipt.verified_by = f"peer:{token}"

    from datetime import datetime
    vouch_row.verified = True
    vouch_row.verified_at = datetime.utcnow()
    await db.commit()

    return {
        "status": "verified",
        "message": "Skill verified! The Skills Passport has been updated.",
        "skill_label": receipt.skill_label if receipt else "Unknown",
        "new_evidence_type": receipt.evidence_type if receipt else "peer_vouched",
    }


@router.get("/heritage")
async def list_heritage_skills():
    """Return the full Heritage Skills registry."""
    return {
        "count": len(HERITAGE_SKILLS),
        "source_note": "Heritage Skills are competencies LMIC employers value but global taxonomies miss.",
        "skills": [
            {
                "id": hs.id,
                "label": hs.label,
                "description": hs.description,
                "employer_value": hs.employer_value,
                "isco_proxy": hs.isco_proxy,
                "country_relevance": hs.country_relevance,
            }
            for hs in HERITAGE_SKILLS
        ],
    }


@router.post("/scan_certificate")
async def scan_certificate_endpoint(
    file: UploadFile = File(...),
    passport_uuid: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a photo of a paper credential — Gemini Flash reads it and extracts
    structured credential data, which is converted into skill receipts.

    Accepts: JPEG, PNG, WebP images.
    Returns: scan result + list of receipts added to the passport.

    Graceful degradation: if GEMINI_API_KEY is not set, returns a clear
    data-gap disclosure rather than an error.
    """
    from backend.modules.skills_signal.certificate_scanner import (
        scan_certificate,
        build_receipts_from_scan,
    )

    content_type = file.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(400, "Only image files are supported (JPEG, PNG, WebP).")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "Image too large. Maximum 10MB.")

    scan_result = await scan_certificate(image_bytes, content_type)
    receipts = build_receipts_from_scan(scan_result)

    saved_receipts = []
    if receipts and passport_uuid:
        result = await db.execute(
            select(SkillsPassport).where(SkillsPassport.passport_uuid == passport_uuid)
        )
        passport = result.scalar_one_or_none()
        if passport:
            for r in receipts:
                row = SkillReceipt(
                    passport_id=passport.id,
                    skill_label=r["skill_label"],
                    esco_code=r.get("esco_code"),
                    isco_code=r.get("isco_code"),
                    evidence_type=r.get("evidence_type", "assessed"),
                    confidence=r.get("confidence", 0.5),
                    verified_by=r.get("verified_by"),
                    is_heritage_skill=False,
                    evidence_text=r.get("evidence_text"),
                )
                db.add(row)
                saved_receipts.append(r["skill_label"])
            await db.commit()

    return {
        "scan_ok": scan_result.get("_scan_ok", False),
        "source": "Gemini Flash 1.5",
        "scan_result": scan_result,
        "receipts_extracted": len(receipts),
        "receipts_saved": len(saved_receipts),
        "saved_skills": saved_receipts,
        "data_note": (
            "Certificate scan uses Gemini Flash vision model. "
            "Confidence depends on image quality. "
            "Scan results are labeled 'assessed' evidence — below peer-vouched and employer-verified."
        ),
    }


# ── Internal helper ───────────────────────────────────────────────────────────

async def _get_or_create_passport(db: AsyncSession, user_id: int) -> SkillsPassport:
    """Get the active passport for a user, or create one."""
    result = await db.execute(
        select(SkillsPassport).where(SkillsPassport.user_id == user_id)
    )
    passport = result.scalars().first()
    if passport:
        return passport

    cfg = get_config()
    _, public_key_b64, _ = generate_keypair()

    import json
    passport = SkillsPassport(
        user_id=user_id,
        passport_uuid=str(__import__("uuid").uuid4()),
        country_iso=cfg.country.iso_code,
        holder_public_key=public_key_b64,
        context_json=json.dumps({"country_iso": cfg.country.iso_code}),
    )
    db.add(passport)
    await db.flush()
    return passport
