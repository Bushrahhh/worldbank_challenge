"""
Skills Signal — Certificate Scanner

Takes a photo of any paper credential (school certificate, training card,
apprenticeship letter, NGO participation record) and extracts structured
credential data using Gemini Flash vision.

Works on:
- School leaving certificates (BECE, SSCE, SSC, HSC)
- NVTI / TVET training certificates
- NGO / vocational program completion letters
- Apprenticeship letters
- Informal "recommendation" letters

Graceful degradation: if GEMINI_API_KEY is not set, returns a partial
profile with a clear note that photo scanning is unavailable.
"""

import base64
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_GEMINI_KEY = os.getenv("GEMINI_API_KEY")

_SYSTEM_PROMPT = """You are reading a photo of a credential or certificate from a young person in a developing country.
Extract all structured information you can see. The document may be:
- A school certificate (secondary, vocational, primary)
- A training or TVET certificate
- An apprenticeship completion letter
- An NGO program certificate
- A handwritten recommendation letter

Return ONLY a JSON object with these fields (use null for any field not visible):
{
  "document_type": "school_certificate | tvet_certificate | ngo_certificate | apprenticeship | recommendation_letter | unknown",
  "holder_name": "name as written on document",
  "institution": "school, training center, or organization name",
  "country": "country if visible",
  "credential_label": "exact credential name e.g. BECE, WASSCE, City & Guilds, NVTI Level 2",
  "subject_or_field": "field of study or training e.g. Electronics, Agriculture, Tailoring",
  "grade_or_result": "grade, class, or result if visible e.g. Credit, Pass, Distinction",
  "year_issued": "4-digit year if visible",
  "issuing_authority": "ministry, exam board, or organization that issued it",
  "additional_skills": ["any specific skills, units, or competencies named on the document"],
  "languages_on_document": ["languages the document is written in"],
  "confidence": "high | medium | low — how clearly readable the document is",
  "scanner_note": "one sentence on quality or any issue with reading the document"
}

Do not invent information. If a field is not visible or not applicable, use null.
Return only the JSON — no other text."""


async def scan_certificate(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> dict:
    """
    Send a certificate image to Gemini Flash and extract credential data.

    Args:
        image_bytes: raw image bytes (JPEG, PNG, WebP)
        mime_type: image MIME type

    Returns:
        dict with extracted credential fields + meta.source
    """
    if not _GEMINI_KEY:
        return _no_key_response()

    try:
        import google.generativeai as genai
        genai.configure(api_key=_GEMINI_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        image_part = {
            "inline_data": {
                "mime_type": mime_type,
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }
        }

        response = model.generate_content(
            [_SYSTEM_PROMPT, image_part],
            generation_config={"temperature": 0.1, "max_output_tokens": 512},
        )

        raw = response.text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        import json
        extracted = json.loads(raw)
        extracted["_source"] = "Gemini Flash 1.5 vision scan"
        extracted["_scan_ok"] = True

        logger.info(
            "Certificate scan OK | type=%s | holder=%s | confidence=%s",
            extracted.get("document_type"),
            extracted.get("holder_name", "unknown"),
            extracted.get("confidence"),
        )
        return extracted

    except Exception as exc:
        logger.warning("Certificate scan failed: %s", exc)
        return {
            "_scan_ok": False,
            "_error": str(exc),
            "_source": "Gemini Flash (scan failed)",
            "scanner_note": "Could not read the document. Try a clearer photo in good lighting.",
        }


def build_receipts_from_scan(scan_result: dict) -> list[dict]:
    """
    Convert a Gemini scan result into one or more skill receipts.
    These are lower-confidence than interview-extracted skills but still useful.
    """
    if not scan_result.get("_scan_ok"):
        return []

    receipts = []
    field = scan_result.get("subject_or_field")
    credential = scan_result.get("credential_label")
    institution = scan_result.get("institution")
    year = scan_result.get("year_issued")
    grade = scan_result.get("grade_or_result")

    # Primary credential receipt
    if field or credential:
        label = f"{credential or 'Certificate'}" + (f" in {field}" if field else "")
        receipts.append({
            "skill_label": label,
            "esco_code": None,
            "isco_code": None,
            "evidence_type": "assessed",
            "confidence": 0.7 if scan_result.get("confidence") == "high" else 0.5,
            "verified_by": institution or "document_scan",
            "is_heritage_skill": False,
            "evidence_text": (
                f"Scanned from paper credential. "
                f"Issuer: {institution or 'unknown'}. "
                f"Year: {year or 'unknown'}. "
                f"Grade: {grade or 'not stated'}."
            ),
            "_from_scan": True,
        })

    # Additional skills named on document
    for skill in scan_result.get("additional_skills") or []:
        if skill and len(skill) > 3:
            receipts.append({
                "skill_label": skill,
                "esco_code": None,
                "isco_code": None,
                "evidence_type": "assessed",
                "confidence": 0.55,
                "verified_by": institution or "document_scan",
                "is_heritage_skill": False,
                "evidence_text": f"Named on scanned credential from {institution or 'unknown'}.",
                "_from_scan": True,
            })

    return receipts


def format_scan_for_user(scan_result: dict, currency_label: str = "") -> str:
    """
    Format the scan result as a readable Telegram message.
    """
    if not scan_result.get("_scan_ok"):
        note = scan_result.get("scanner_note", "Could not read the document.")
        return f"I couldn't read that clearly. {note}\n\nTry: good lighting, flat surface, whole document in frame."

    lines = ["I can see this credential:"]

    if scan_result.get("credential_label"):
        lines.append(f"  Credential: {scan_result['credential_label']}")
    if scan_result.get("subject_or_field"):
        lines.append(f"  Field: {scan_result['subject_or_field']}")
    if scan_result.get("institution"):
        lines.append(f"  Issued by: {scan_result['institution']}")
    if scan_result.get("year_issued"):
        lines.append(f"  Year: {scan_result['year_issued']}")
    if scan_result.get("grade_or_result"):
        lines.append(f"  Result: {scan_result['grade_or_result']}")

    skills = scan_result.get("additional_skills") or []
    if skills:
        lines.append(f"  Skills listed: {', '.join(skills[:4])}")

    conf = scan_result.get("confidence", "medium")
    if conf == "low":
        lines.append("\nThe photo is a bit hard to read — I've done my best. You can describe it in your own words too.")

    lines.append("\nI've added this to your Skills Passport.")
    return "\n".join(lines)


def _no_key_response() -> dict:
    return {
        "_scan_ok": False,
        "_error": "GEMINI_API_KEY not set",
        "_source": "Gemini Flash (not configured)",
        "scanner_note": (
            "Photo scanning requires a Gemini API key. "
            "You can describe your certificate in text instead."
        ),
        "document_type": None,
        "holder_name": None,
        "credential_label": None,
    }
