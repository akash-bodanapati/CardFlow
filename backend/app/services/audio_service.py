import logging
import re

from google import genai
from google.genai import types

from app.config import config

logger = logging.getLogger(__name__)

TRANSCRIPTION_PROMPT_PRIMARY = """
You are an expert audio transcriber.
Please transcribe the spoken words in this audio exactly.
Rules:
1. Transcribe the words exactly as spoken. Do not translate them.
2. Output the result in English characters only.
3. Preserve names, email addresses, and phone numbers exactly as spoken.
4. Do not include any introduction, explanations, summaries, or metadata.
5. Do not include any markdown code fencing or language labels.
6. Do not hallucinate or add words not present in the audio.
"""

TRANSCRIPTION_PROMPT_RETRY = """
CRITICAL: The previous transcription output contained non-English or mixed characters.
You MUST output the transcription in English characters ONLY.
Transcribe the spoken English words exactly. Do not translate. Do not use Hindi/Devanagari characters.
Preserve all names, emails, and numbers exactly. Just the raw English text.
"""


def normalize_text(text: str) -> str:
    """Normalize transcript by removing markdown, prefixes, language labels, and accidental whitespace."""
    if not text:
        return ""
    # Strip markdown code blocks if any
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"```$", "", text).strip()

    # Remove common prefixes like "Transcript:", "Transcription:", "Output:"
    text = re.sub(
        r"^(transcript|transcription|output|result|text)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove language labels like "(English)", "[English]"
    text = re.sub(r"^[\(\[][a-zA-Z\s]+[\)\]]\s*", "", text)

    # Remove extra spaces
    text = " ".join(text.split())
    return text


def contains_non_english(text: str) -> bool:
    """Detect if text contains Devanagari (Hindi) or non-English character ranges."""
    # Check for Devanagari characters (Hindi unicode block: U+0900 to U+097F)
    if re.search(r"[\u0900-\u097f]", text):
        return True
    return False


class AudioService:
    def __init__(self):
        api_key = config.gemini_audio_key or config.gemini_api_key
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    async def transcribe(self, audio_data: bytes) -> dict:
        """Transcribe audio using Gemini 2.5 Flash with normalization and English-only retry logic."""
        if not audio_data:
            logger.warning("Empty audio data passed to AudioService")
            return {
                "success": False,
                "transcript": "",
                "user_message": "No audio data provided."
            }

        logger.info("Transcribing audio via Gemini 2.5 Flash...")
        try:
            mime_type = "audio/webm"
            if audio_data.startswith(b"RIFF"):
                mime_type = "audio/wav"
            elif audio_data.startswith(b"ID3") or audio_data.startswith(b"\xff\xfb"):
                mime_type = "audio/mp3"
            elif audio_data.startswith(b"\x1a\x45\xdf\xa3"):
                mime_type = "audio/webm"

            contents = [
                types.Part.from_bytes(data=audio_data, mime_type=mime_type),
                TRANSCRIPTION_PROMPT_PRIMARY,
            ]

            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
            )
            raw_transcript = response.text.strip()
            normalized = normalize_text(raw_transcript)

            # Retry logic: if non-English characters detected, retry once with explicit prompt
            if contains_non_english(normalized):
                logger.warning(
                    "Non-English characters detected in transcript. Retrying transcription..."
                )
                contents_retry = [
                    types.Part.from_bytes(data=audio_data, mime_type=mime_type),
                    TRANSCRIPTION_PROMPT_RETRY,
                ]
                response_retry = self.client.models.generate_content(
                    model=self.model,
                    contents=contents_retry,
                )
                raw_transcript = response_retry.text.strip()
                normalized = normalize_text(raw_transcript)

            logger.info(f"Gemini Audio Transcript: {normalized}")
            return {
                "success": True,
                "transcript": normalized,
                "user_message": None
            }
        except Exception as e:
            logger.exception("Audio transcription failed due to exception")
            return {
                "success": False,
                "transcript": None,
                "user_message": "Audio note uploaded successfully. Transcription is temporarily unavailable."
            }


audio_service = AudioService()
