from unittest.mock import patch

import pytest

from app.agent.nodes import get_validated_public_audio_url


def test_development_localhost_allowed() -> None:
    """PASS: development + localhost -> allowed"""
    with patch("app.agent.nodes.config") as mock_config:
        mock_config.env = "development"
        mock_config.public_base_url = "http://localhost:8000"
        result = get_validated_public_audio_url("session-123")
        assert result == "http://localhost:8000/uploads/session-123.wav"

    with patch("app.agent.nodes.config") as mock_config:
        mock_config.env = "development"
        mock_config.public_base_url = "http://127.0.0.1:8000"
        result = get_validated_public_audio_url("session-123")
        assert result == "http://127.0.0.1:8000/uploads/session-123.wav"


def test_production_public_url_allowed() -> None:
    """PASS: production + public URL -> allowed"""
    with patch("app.agent.nodes.config") as mock_config:
        mock_config.env = "production"
        mock_config.public_base_url = "https://cardflow-app.com"
        result = get_validated_public_audio_url("session-123")
        assert result == "https://cardflow-app.com/uploads/session-123.wav"


def test_production_localhost_rejected() -> None:
    """PASS: production + localhost -> rejected"""
    with patch("app.agent.nodes.config") as mock_config:
        mock_config.env = "production"
        mock_config.public_base_url = "http://localhost:8000"
        with pytest.raises(ValueError) as exc_info:
            get_validated_public_audio_url("session-123")
        assert "localhost and 127.0.0.1 are blocked" in str(exc_info.value)

    with patch("app.agent.nodes.config") as mock_config:
        mock_config.env = "production"
        mock_config.public_base_url = "http://127.0.0.1:8000"
        with pytest.raises(ValueError) as exc_info:
            get_validated_public_audio_url("session-123")
        assert "localhost and 127.0.0.1 are blocked" in str(exc_info.value)


def test_missing_url_in_development() -> None:
    """PASS: missing URL in development -> graceful warning & fallback"""
    with patch("app.agent.nodes.config") as mock_config:
        mock_config.env = "development"
        mock_config.public_base_url = ""
        result = get_validated_public_audio_url("session-123")
        assert result == "http://localhost:8000/uploads/session-123.wav"


def test_missing_url_in_production() -> None:
    """PASS: missing URL in production -> explicit error"""
    with patch("app.agent.nodes.config") as mock_config:
        mock_config.env = "production"
        mock_config.public_base_url = ""
        with pytest.raises(ValueError) as exc_info:
            get_validated_public_audio_url("session-123")
        assert "Missing PUBLIC_BASE_URL" in str(exc_info.value)
