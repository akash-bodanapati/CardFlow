import pytest
from unittest.mock import patch, MagicMock
from app.config import Settings
from app.services.vision_service import VisionService
from app.services.audio_service import AudioService
from app.services.enrichment_service import EnrichmentService


def test_gemini_keys_configuration():
    """Test that Settings loads specific keys and falls back appropriately."""
    # Test setting all specific keys
    settings_all = Settings(
        gemini_api_key="default_key",
        gemini_ocr_key="ocr_key",
        gemini_audio_key="audio_key",
        gemini_enrichment_key="enrichment_key",
    )
    assert settings_all.gemini_ocr_key == "ocr_key"
    assert settings_all.gemini_audio_key == "audio_key"
    assert settings_all.gemini_enrichment_key == "enrichment_key"
    assert settings_all.gemini_api_key == "default_key"


@patch("google.genai.Client")
def test_services_use_specific_keys(mock_genai_client):
    """Test that each service initializes with its specific key."""
    custom_config = Settings(
        gemini_api_key="default_key",
        gemini_ocr_key="ocr_key",
        gemini_audio_key="audio_key",
        gemini_enrichment_key="enrichment_key",
    )

    with patch("app.services.vision_service.config", custom_config):
        vision = VisionService()
        mock_genai_client.assert_any_call(api_key="ocr_key")

    with patch("app.services.audio_service.config", custom_config):
        audio = AudioService()
        mock_genai_client.assert_any_call(api_key="audio_key")

    with patch("app.services.enrichment_service.config", custom_config):
        enrichment = EnrichmentService()
        mock_genai_client.assert_any_call(api_key="enrichment_key")


@patch("google.genai.Client")
def test_services_fallback_to_default_key(mock_genai_client):
    """Test that services fallback to gemini_api_key if their specific key is missing."""
    fallback_config = Settings(
        gemini_api_key="default_key",
        gemini_ocr_key="",
        gemini_audio_key="",
        gemini_enrichment_key="",
    )

    with patch("app.services.vision_service.config", fallback_config):
        vision = VisionService()
        mock_genai_client.assert_any_call(api_key="default_key")

    with patch("app.services.audio_service.config", fallback_config):
        audio = AudioService()
        mock_genai_client.assert_any_call(api_key="default_key")

    with patch("app.services.enrichment_service.config", fallback_config):
        enrichment = EnrichmentService()
        mock_genai_client.assert_any_call(api_key="default_key")
