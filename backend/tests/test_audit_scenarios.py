import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.routers.chat import make_response_payload
from app.agent.state import AgentState
from google.genai.errors import APIError


class DummyState:
    def __init__(self, values, next_steps=None):
        self.values = values
        self.next = next_steps or []


def test_payload_duplicate_detected():
    """Verify response payload when duplicate contact is detected."""
    state = DummyState({
        "input_type": "text",
        "dedup_result": {"is_duplicate": True},
        "active_sheet_row": {"row_index": 12},
        "notification_sent": True,
        "messages": [{"type": "ai", "content": "Duplicate found! Contact already exists: Priya"}]
    })
    res = make_response_payload(state, "confirm")
    assert res["success"] is False
    assert res["action"] == "duplicate_check"
    assert res["status"] == "warning"
    assert "Duplicate found" in res["message"]
    assert res["details"]["duplicate_found"] is True
    assert res["details"]["saved_to_sheet"] is False
    assert res["details"]["whatsapp_sent"] is False


def test_payload_sheet_save_success_whatsapp_success():
    """Verify response payload on successful Google Sheets save and WhatsApp alert sent."""
    state = DummyState({
        "input_type": "text",
        "active_sheet_row": {"row_index": 12},
        "notification_sent": True,
        "messages": [{"type": "ai", "content": "Contact saved successfully and WhatsApp notification sent."}]
    })
    res = make_response_payload(state, "confirm")
    assert res["success"] is True
    assert res["action"] == "sheet_write"
    assert res["status"] == "success"
    assert res["details"]["saved_to_sheet"] is True
    assert res["details"]["whatsapp_sent"] is True


def test_payload_sheet_save_success_whatsapp_failed():
    """Verify response payload on successful Google Sheets save but failed WhatsApp alert."""
    state = DummyState({
        "input_type": "text",
        "active_sheet_row": {"row_index": 12},
        "notification_sent": False,
        "messages": [{"type": "ai", "content": "Contact saved successfully. Manager notification could not be delivered."}]
    })
    res = make_response_payload(state, "confirm")
    assert res["success"] is True
    assert res["action"] == "sheet_write"
    assert res["status"] == "warning"
    assert res["details"]["saved_to_sheet"] is True
    assert res["details"]["whatsapp_sent"] is False


def test_payload_ocr_quota_exhausted():
    """Verify response payload when OCR API returns quota exhaustion (429)."""
    state = DummyState({
        "input_type": "image",
        "ocr_success": False,
        "raw_extraction": {"_error": "429"}
    })
    res = make_response_payload(state, "send_message")
    assert res["success"] is False
    assert res["action"] == "ocr"
    assert res["status"] == "error"
    assert "quota reached" in res["message"]


def test_payload_audio_quota_exhausted():
    """Verify response payload when audio transcription API fails."""
    state = DummyState({
        "input_type": "audio",
        "transcription_success": False,
        "messages": [{"type": "ai", "content": "Audio note uploaded successfully. Transcription is temporarily unavailable."}]
    })
    res = make_response_payload(state, "send_message")
    assert res["success"] is False
    assert res["action"] == "transcription"
    assert res["status"] == "warning"
    assert "Transcription is temporarily unavailable" in res["message"]
    assert res["details"]["transcription_completed"] is False
