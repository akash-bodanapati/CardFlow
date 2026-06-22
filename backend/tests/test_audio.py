from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.audio_service import (audio_service, contains_non_english,
                                        normalize_text)


def test_normalize_text() -> None:
    """Verify normalize_text strips markdown, prefixes, labels, and whitespace."""
    assert normalize_text("```\nTranscript: Hello world\n```") == "Hello world"
    assert normalize_text("Transcription: (English) Priya Sharma") == "Priya Sharma"
    assert normalize_text("[English]   Jane Doe  ") == "Jane Doe"
    assert normalize_text("") == ""


def test_contains_non_english() -> None:
    """Verify contains_non_english detects Devanagari characters."""
    assert contains_non_english("Priya Sharma") is False
    assert contains_non_english("Priya शर्मा") is True
    assert contains_non_english("नमस्ते") is True


@pytest.mark.asyncio
async def test_transcribe_english_success() -> None:
    """Test successful English transcription path."""
    mock_response = MagicMock()
    mock_response.text = "Hello, this is a clean English transcript."

    with patch.object(
        audio_service.client.models, "generate_content", return_value=mock_response
    ) as mock_gen:
        result = await audio_service.transcribe(b"RIFFdummywavbytes")
        assert result == "Hello, this is a clean English transcript."
        mock_gen.assert_called_once()


@pytest.mark.asyncio
async def test_transcribe_mixed_audio_retry() -> None:
    """Test mixed audio path triggering the English-only retry flow."""
    # First response contains Devanagari, second contains normalized English
    response_1 = MagicMock()
    response_1.text = "Transcript: नमस्ते Priya Sharma"

    response_2 = MagicMock()
    response_2.text = "Hello Priya Sharma"

    with patch.object(
        audio_service.client.models,
        "generate_content",
        side_effect=[response_1, response_2],
    ) as mock_gen:
        result = await audio_service.transcribe(b"RIFFdummywavbytes")
        assert result == "Hello Priya Sharma"
        assert mock_gen.call_count == 2


@pytest.mark.asyncio
async def test_transcribe_empty_audio_graceful_failure() -> None:
    """Test empty audio results in graceful failure (empty string)."""
    result = await audio_service.transcribe(b"")
    assert result == ""
