"""
VisionService: extracts contact info from business card images using Gemini.

Uses google-genai SDK directly (not langchain wrapper) for reliable
structured output. Model is confirmed via list_models() — gemini-2.5-flash
is the current stable multimodal flash model.
"""

import base64
import json
import re

from google import genai
from google.genai import types, errors

from app.config import config

# Verified available via genai.Client.models.list() inside the container.
# Output: models/gemini-2.5-flash supports generateContent + multimodal input.
VISION_MODEL = "gemini-2.5-flash"

EXTRACTION_PROMPT = """
You are a contact information extractor for business cards.

Examine this business card image and extract ONLY the following fields:
- name: the person's full name
- phone: their phone number (preserve the original format including country code)
- email: their email address
- company: the company or organization name

Return your answer as a single valid JSON object with exactly these four keys.
If a field is not visible on the card, use an empty string "".
Do not include any explanation, markdown fencing, or extra text — just the raw JSON.

Example output:
{"name": "Alice Johnson", "phone": "+1 555 0199", "email": "alice@example.com", "company": "Acme Corp"}
"""


class VisionService:
    def __init__(self):
        self.client = genai.Client(api_key=config.gemini_api_key)
        self.model = VISION_MODEL

    async def extract_contact_info(self, image_data: bytes) -> dict:
        """Extract contact info from a business card image using Gemini Vision."""
        if not image_data:
            raise ValueError("No image data provided to VisionService.")

        print(
            f"VisionService: extracting with model={self.model}, image_size={len(image_data)} bytes"
        )

        # Detect mime type from magic bytes
        mime_type = "image/jpeg"
        if image_data[:8] == b"\x89PNG\r\n\x1a\n":
            mime_type = "image/png"
        elif image_data[:4] == b"GIF8":
            mime_type = "image/gif"
        elif image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
            mime_type = "image/webp"

        contents = [
            types.Part.from_bytes(data=image_data, mime_type=mime_type),
            EXTRACTION_PROMPT,
        ]

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.0,  # deterministic extraction
                    max_output_tokens=256,
                ),
            )
        except errors.APIError as e:
            if getattr(e, "code", None) in (429, 503):
                import asyncio
                print(f"VisionService: transient error {e.code} encountered. Retrying once after 1s delay...")
                await asyncio.sleep(1.0)
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=256,
                    ),
                )
            else:
                raise

        raw_text = response.text.strip()
        print(f"VisionService raw response: {raw_text}")

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```[a-zA-Z]*\n?", "", raw_text)
            raw_text = re.sub(r"```$", "", raw_text).strip()

        parsed = json.loads(raw_text)

        # Validate and normalise keys
        result = {
            "name": str(parsed.get("name", "") or "").strip(),
            "phone": str(parsed.get("phone", "") or "").strip(),
            "email": str(parsed.get("email", "") or "").strip(),
            "company": str(parsed.get("company", "") or "").strip(),
        }

        print(f"VisionService extracted: {result}")
        return result


vision_service = VisionService()
