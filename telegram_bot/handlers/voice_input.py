"""
Telegram voice input handler — transcribes voice notes via Groq Whisper,
then feeds the transcript into the interview flow.
"""

import logging
import os
from typing import Optional

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.handlers.interview_flow import INTERVIEW, handle_interview_message

logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000"


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Download voice note from Telegram, transcribe via backend Whisper endpoint,
    then process as a regular interview message.
    """
    session_id = context.user_data.get("session_id")
    if not session_id:
        await update.message.reply_text(
            "Start an interview first with /interview, then send voice notes."
        )
        return INTERVIEW

    await update.message.chat.send_action("typing")
    await update.message.reply_text("_Transcribing your voice note..._", parse_mode="Markdown")

    # Download the voice file from Telegram
    voice = update.message.voice
    if not voice:
        await update.message.reply_text("Couldn't read the voice note. Please try again.")
        return INTERVIEW

    try:
        voice_file = await context.bot.get_file(voice.file_id)
        audio_bytes = await voice_file.download_as_bytearray()
    except Exception as exc:
        logger.error("Voice download failed: %s", exc)
        await update.message.reply_text(
            "Couldn't download the voice note. Please type your answer instead."
        )
        return INTERVIEW

    # Send to backend for transcription
    transcript = await _transcribe(bytes(audio_bytes))

    if not transcript:
        await update.message.reply_text(
            "Voice transcription unavailable (GROQ_API_KEY required). "
            "Please type your answer."
        )
        return INTERVIEW

    # Echo the transcript so user can see what was heard
    await update.message.reply_text(
        f"_I heard: \"{transcript}\"_",
        parse_mode="Markdown",
    )

    # Replace message text with transcript and continue interview
    update.message.text = transcript
    return await handle_interview_message(update, context)


async def _transcribe(audio_bytes: bytes) -> Optional[str]:
    """POST audio bytes to the backend /skills/voice endpoint."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{API_BASE}/skills/voice",
                files={"audio": ("voice.ogg", audio_bytes, "audio/ogg")},
                params={"language": "en"},
            )
            if resp.status_code == 200:
                return resp.json().get("transcript", "")
            logger.warning("Transcription API returned %s", resp.status_code)
    except Exception as exc:
        logger.error("Transcription request failed: %s", exc)
    return None
