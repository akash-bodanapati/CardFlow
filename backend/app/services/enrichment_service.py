import json
import logging
import re
from google import genai
from google.genai import types

from app.config import config

logger = logging.getLogger(__name__)


class EnrichmentService:
    def __init__(self):
        api_key = config.gemini_enrichment_key or config.gemini_api_key
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    async def enrich_company_details(self, company: str) -> dict:
        """Fetch company details (website/LinkedIn) using Gemini."""
        if not company:
            logger.info("EnrichmentService: No company name provided.")
            return {}

        prompt = (
            f"Provide the official website URL and LinkedIn page URL for the company: '{company}'. "
            "Return ONLY a JSON object with keys 'website' and 'linkedin'. If unknown, return empty strings."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            raw_response_text = getattr(response, "text", "")
            logger.info(f"Raw Gemini response for company enrichment: '{raw_response_text}'")

            text = raw_response_text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
                text = re.sub(r"```$", "", text).strip()

            try:
                data = json.loads(text)
                logger.info(f"Company enrichment result for {company}: {data}")
                return data
            except json.JSONDecodeError as decode_err:
                logger.error(
                    f"JSONDecodeError parsing company enrichment response. Raw text: '{text}'. Error: {decode_err}"
                )
                return {}

        except Exception as e:
            logger.warning(f"Failed to enrich company {company}: {e}")
            return {}


enrichment_service = EnrichmentService()
