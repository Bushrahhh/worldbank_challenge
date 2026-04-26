"""
Telegram handler — photo/certificate input

When a user sends a photo, we:
1. Download the highest-resolution version from Telegram
2. Send to Gemini Flash for OCR + credential extraction
3. Convert scan result into skill receipts
4. Save receipts to the active passport session
5. Reply with a plain-language summary of what was found
"""

import logging
from io import BytesIO

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle an incoming photo message — scan for credentials."""
    msg = update.message
    if not msg or not msg.photo:
        return

    await msg.reply_text(
        "Got your photo. Reading it now..."
    )

    # Download highest-res version (last in list = largest)
    photo_file = await msg.photo[-1].get_file()
    buf = BytesIO()
    await photo_file.download_to_memory(buf)
    image_bytes = buf.getvalue()

    # Determine MIME type (Telegram always sends JPEG for photos)
    mime_type = "image/jpeg"

    try:
        from backend.modules.skills_signal.certificate_scanner import (
            scan_certificate,
            build_receipts_from_scan,
            format_scan_for_user,
        )
        from backend.config_loader import get_config

        cfg = get_config()
        scan_result = await scan_certificate(image_bytes, mime_type)
        user_text = format_scan_for_user(scan_result)
        await msg.reply_text(user_text)

        # Build skill receipts from scan
        receipts = build_receipts_from_scan(scan_result)
        if receipts:
            # Store in context for the active session
            session_receipts = context.user_data.get("scan_receipts", [])
            session_receipts.extend(receipts)
            context.user_data["scan_receipts"] = session_receipts
            context.user_data["has_scan"] = True

            skill_names = [r["skill_label"] for r in receipts[:3]]
            skills_text = "\n".join(f"  • {s}" for s in skill_names)
            await msg.reply_text(
                f"Added {len(receipts)} credential(s) to your profile:\n{skills_text}\n\n"
                "Continue describing your work experience, or type /passport to see your full profile."
            )
        else:
            await msg.reply_text(
                "I couldn't extract specific skills from this document. "
                "You can describe what you learned or did in your own words."
            )

    except Exception as exc:
        logger.exception("Photo handler error: %s", exc)
        await msg.reply_text(
            "Something went wrong reading that photo. "
            "Try again with better lighting, or describe your credential in text."
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a document/file sent as an attachment (PDF or image file)."""
    msg = update.message
    if not msg or not msg.document:
        return

    doc = msg.document
    mime = doc.mime_type or ""

    if not mime.startswith("image/"):
        await msg.reply_text(
            "I can read photo certificates. For PDFs or other files, "
            "take a clear photo and send that instead."
        )
        return

    await msg.reply_text("Reading your document...")

    file = await doc.get_file()
    buf = BytesIO()
    await file.download_to_memory(buf)
    image_bytes = buf.getvalue()

    try:
        from backend.modules.skills_signal.certificate_scanner import (
            scan_certificate,
            build_receipts_from_scan,
            format_scan_for_user,
        )
        scan_result = await scan_certificate(image_bytes, mime)
        await msg.reply_text(format_scan_for_user(scan_result))

        receipts = build_receipts_from_scan(scan_result)
        if receipts:
            context.user_data.setdefault("scan_receipts", []).extend(receipts)
            context.user_data["has_scan"] = True
            await msg.reply_text(
                f"Added {len(receipts)} credential item(s). "
                "Type /passport to see your profile."
            )
    except Exception as exc:
        logger.exception("Document handler error: %s", exc)
        await msg.reply_text("Couldn't read that file. Try a clear photo instead.")
