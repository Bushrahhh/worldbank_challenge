"""
AI Skills Interview

Conversational behavioral interview that extracts competencies from lived experience.
Not a form. A conversation.

Uses Groq Llama 3.3 70B for the demo. Documented fallback: Ollama Mistral 7B local.
Each exchange extracts skills, maps to ESCO, checks for Heritage Skills, and returns
structured data alongside the conversational response.
"""

import json
import logging
import os
from typing import Optional

from backend.modules.skills_signal.heritage_skills import (
    HERITAGE_SKILLS,
    HeritageSkill,
    match_heritage_skills,
)
from backend.modules.skills_signal.receipts import make_receipt_dict

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MODEL_FALLBACK = "llama-3.1-8b-instant"


def _groq_key() -> str:
    return os.environ.get("GROQ_API_KEY", "")

# ── System prompt ─────────────────────────────────────────────────────────────

INTERVIEW_SYSTEM_PROMPT = """You are UNMAPPED's Skills Interviewer — a skilled, respectful professional
who helps people articulate the real value of their work experience.

YOUR JOB: Extract competencies from lived experience through natural conversation.
Every person you speak with has real skills. Your job is to surface them.

CORE RULES:
1. Ask ONE question at a time. Never use lists, bullets, or forms.
2. Use behavioral interview technique: "Walk me through...", "Tell me about a time...",
   "What exactly do you do when...", "What was the hardest part of..."
3. Build on what the person says. If they mention fixing phones, ask HOW they fix them.
4. Recognize Heritage Skills — competencies LMIC employers value but global taxonomies miss:
   mobile money, repair mindset, multilingual service, community trust, informal trading,
   solar maintenance, motorcycle repair, community health, low-bandwidth digital skills,
   self-directed learning, agricultural knowledge, local interpretation, savings groups.
5. NEVER use these words: low-skilled, vulnerable, beneficiary, disadvantaged, uneducated.
   The person you're talking to is capable. Your job is to make that visible.
6. Be warm but efficient. The interview has 5-8 exchanges total.
7. In EACH response, return a JSON block with any extracted skills.

INTERVIEW STAGES:
  greeting → work_exploration → skill_deepdive → heritage_check → wrap_up → complete

RESPONSE FORMAT — you MUST include this JSON at the end of every response, after a blank line:
```json
{
  "message": "your conversational response",
  "extracted_skills": [
    {
      "label": "human-readable skill name",
      "esco_hint": "closest ESCO skill concept (leave empty if unsure)",
      "isco_code": "4-digit ISCO-08 code (leave empty if unsure)",
      "confidence": 0.0_to_1.0,
      "evidence": "what the user said that demonstrates this skill",
      "heritage_skill_id": "heritage skill ID from list or null"
    }
  ],
  "stage": "current_stage",
  "complete": false,
  "follow_up_area": "what aspect to explore next"
}
```

Heritage skill IDs: hs_mobile_money, hs_repair_mindset, hs_multilingual_service,
hs_community_trust, hs_informal_trading, hs_solar_maintenance, hs_moto_maintenance,
hs_community_health, hs_low_end_digital, hs_video_learning, hs_agri_calendar,
hs_local_interpreter, hs_susu_management, hs_crossborder_trade, hs_food_processing,
hs_water_sanitation, hs_conflict_mediation, hs_informal_teaching, hs_remote_logistics,
hs_crowd_event

CRITICAL: If complete is true, wrap up warmly and explain what happens next
(their Skills Passport is being generated).
"""

GREETING_PROMPT = """The person has just started the interview. Ask them one warm, open question
about what work they do day-to-day. Make it feel like a human conversation, not a survey.
Examples: "What does a typical day look like for you?" or "Tell me about the work you do —
what are you good at?"

Do not ask about formal credentials or qualifications. Start with what they actually DO."""


async def run_interview_turn(
    messages: list[dict],
    user_message: str,
    stage: str = "greeting",
) -> dict:
    """
    Process one turn of the interview.
    Returns {message, extracted_skills, stage, complete, raw_response}.
    """
    updated_messages = list(messages)
    if user_message:
        updated_messages.append({"role": "user", "content": user_message})

    # Add stage context to system prompt
    system = INTERVIEW_SYSTEM_PROMPT
    if not messages:  # First turn
        system += f"\n\nCURRENT STAGE: greeting\n{GREETING_PROMPT}"
    else:
        system += f"\n\nCURRENT STAGE: {stage}\nMessages so far: {len(messages)}"
        if len(messages) >= 10:
            system += "\nThis is the final exchange — wrap up and set complete: true."

    if _groq_key():
        return await _groq_turn(system, updated_messages)
    else:
        logger.warning("No GROQ_API_KEY — using mock interview responses")
        return _mock_turn(user_message, stage, len(messages))


async def _groq_turn(system: str, messages: list[dict]) -> dict:
    """Call Groq API and parse the structured response."""
    from groq import AsyncGroq

    client = AsyncGroq(api_key=_groq_key())

    # Try primary model, fall back to faster model
    for model in [GROQ_MODEL, GROQ_MODEL_FALLBACK]:
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}] + messages,
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "text"},
            )
            raw = resp.choices[0].message.content
            return _parse_interview_response(raw)
        except Exception as exc:
            logger.warning("Groq model %s failed: %s — trying fallback", model, exc)

    return _error_turn("Interview service temporarily unavailable. Please try again.")


def _parse_interview_response(raw: str) -> dict:
    """
    Extract the JSON block from the LLM response.
    The LLM is instructed to put JSON in a ```json block.
    """
    result = {
        "message": raw,
        "extracted_skills": [],
        "stage": "interview",
        "complete": False,
        "follow_up_area": None,
        "raw_response": raw,
    }

    # Extract JSON block
    if "```json" in raw:
        try:
            start = raw.index("```json") + 7
            end = raw.index("```", start)
            json_str = raw[start:end].strip()
            parsed = json.loads(json_str)

            result["message"] = parsed.get("message", raw.split("```")[0].strip())
            result["extracted_skills"] = parsed.get("extracted_skills", [])
            result["stage"] = parsed.get("stage", "interview")
            result["complete"] = parsed.get("complete", False)
            result["follow_up_area"] = parsed.get("follow_up_area")
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("JSON parse error in interview response: %s", exc)
            # Message is the text before the json block
            result["message"] = raw.split("```")[0].strip()
    elif "{" in raw and "extracted_skills" in raw:
        # LLM put JSON inline without code fence
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            parsed = json.loads(raw[start:end])
            result.update(parsed)
            result["raw_response"] = raw
        except Exception:
            pass

    # Heritage skill auto-detection: scan message + user text for triggers
    combined = raw
    additional_hs = match_heritage_skills(combined)
    existing_hs_ids = {s.get("heritage_skill_id") for s in result["extracted_skills"]}
    for hs in additional_hs:
        if hs.id not in existing_hs_ids:
            result["extracted_skills"].append({
                "label": hs.label,
                "esco_hint": hs.esco_proxy,
                "isco_code": hs.isco_proxy,
                "confidence": 0.65,
                "evidence": "Detected from conversation context",
                "heritage_skill_id": hs.id,
            })

    return result


def _mock_turn(user_message: str, stage: str, turn_count: int) -> dict:
    """
    Mock interview responses for demo when no GROQ_API_KEY is set.
    Simulates a realistic interview flow for Amara's phone repair profile.
    """
    mock_flow = [
        {
            "message": (
                "Great to meet you! Tell me about the work you do — "
                "what does a typical day look like for you?"
            ),
            "extracted_skills": [],
            "stage": "greeting",
            "complete": False,
        },
        {
            "message": (
                "That sounds like real hands-on work. When a customer brings you a phone "
                "with a cracked screen, walk me through exactly what you do — "
                "from the moment they hand it to you."
            ),
            "extracted_skills": [
                {
                    "label": "Mobile device repair and diagnosis",
                    "esco_hint": "repair and maintenance of electronic equipment",
                    "isco_code": "7422",
                    "confidence": 0.82,
                    "evidence": user_message,
                    "heritage_skill_id": "hs_repair_mindset",
                }
            ],
            "stage": "work_exploration",
            "complete": False,
        },
        {
            "message": (
                "That's a real skill — knowing which part to replace and sourcing it "
                "is half the job. How do you communicate with customers who don't speak "
                "English — do you work in local languages?"
            ),
            "extracted_skills": [
                {
                    "label": "Electronic screen replacement and soldering",
                    "esco_hint": "repair and maintenance of electronic equipment",
                    "isco_code": "7422",
                    "confidence": 0.88,
                    "evidence": user_message,
                    "heritage_skill_id": None,
                },
            ],
            "stage": "skill_deepdive",
            "complete": False,
        },
        {
            "message": (
                "That's genuinely valuable — serving customers across language boundaries "
                "is a real competency. Do you use mobile money for your business — "
                "receiving payments or managing your float?"
            ),
            "extracted_skills": [
                {
                    "label": "Multilingual customer service",
                    "esco_hint": "communicate with customers",
                    "isco_code": "5220",
                    "confidence": 0.78,
                    "evidence": user_message,
                    "heritage_skill_id": "hs_multilingual_service",
                }
            ],
            "stage": "heritage_check",
            "complete": False,
        },
        {
            "message": (
                "Mobile money operations — that's a critical skill for running any "
                "business here. One last thing: you taught yourself a lot of this from "
                "YouTube and practice. Tell me about the last thing you learned on your own."
            ),
            "extracted_skills": [
                {
                    "label": "Mobile money operations",
                    "esco_hint": "use financial services",
                    "isco_code": "4312",
                    "confidence": 0.85,
                    "evidence": user_message,
                    "heritage_skill_id": "hs_mobile_money",
                }
            ],
            "stage": "heritage_check",
            "complete": False,
        },
        {
            "message": (
                "That's exactly what UNMAPPED is here for — making skills like yours "
                "visible to the people who need them. I've captured everything. "
                "Your Skills Passport is being generated now — "
                "it will show 6 verified competencies. Type /passport to see it."
            ),
            "extracted_skills": [
                {
                    "label": "Self-directed technical learning",
                    "esco_hint": "learning agility",
                    "isco_code": "2356",
                    "confidence": 0.75,
                    "evidence": user_message,
                    "heritage_skill_id": "hs_video_learning",
                }
            ],
            "stage": "complete",
            "complete": True,
        },
    ]
    idx = min(turn_count, len(mock_flow) - 1)
    return mock_flow[idx]


def _error_turn(message: str) -> dict:
    return {
        "message": message,
        "extracted_skills": [],
        "stage": "error",
        "complete": False,
        "raw_response": message,
    }


async def transcribe_voice(audio_bytes: bytes, language: str = "en") -> str:
    """
    Transcribe voice input using Groq Whisper.
    Returns the transcription text, or empty string on failure.
    """
    if not _groq_key():
        return "[Voice transcription requires GROQ_API_KEY]"

    import io
    from groq import AsyncGroq

    client = AsyncGroq(api_key=_groq_key())
    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "voice.ogg"  # Telegram sends OGG
        transcription = await client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3-turbo",
            language=language if language != "tw" else None,  # Whisper doesn't have Twi
            response_format="text",
        )
        return str(transcription).strip()
    except Exception as exc:
        logger.error("Whisper transcription failed: %s", exc)
        return ""
