from typing import Any, Dict
from unittest.mock import AsyncMock, patch, mock_open

import pytest

from app.agent.nodes import check_duplicate, write_to_sheet
from app.agent.state import AgentState


@pytest.mark.asyncio
async def test_check_duplicate_node() -> None:
    """Tests the check_duplicate node logic with mocked sheets service."""
    state: AgentState = {
        "session_id": "test-session",
        "input_type": "image",
        "file_data": None,
        "messages": [],
        "raw_extraction": {
            "name": "Priya Sharma",
            "phone": "9876543210",
            "email": "priya@sharma.com",
            "company": "NovaTech",
        },
        "confirmed_contact": {
            "name": "Priya Sharma",
            "phone": "9876543210",
            "email": "priya@sharma.com",
            "company": "NovaTech",
        },
        "dedup_result": None,
        "active_sheet_row": None,
        "awaiting_confirmation": False,
    }

    # Mock the sheets_service.get_all_rows to return duplicate row
    with patch(
        "app.agent.nodes.sheets_service.get_all_rows", new_callable=AsyncMock
    ) as mock_get_all_rows:
        mock_get_all_rows.return_value = [
            {
                "Name": "Priya Sharma",
                "Phone": "9876543210",
                "Email": "priya@sharma.com",
                "Company": "NovaTech",
            }
        ]

        result = await check_duplicate(state)

        assert result["dedup_result"]["is_duplicate"] is True
        assert result["dedup_result"]["matched_row"]["Name"] == "Priya Sharma"


@pytest.mark.asyncio
async def test_write_to_sheet_guard() -> None:
    """Tests that write_to_sheet node blocks writing fully blank contact data."""
    state: AgentState = {
        "session_id": "test-session",
        "input_type": "image",
        "file_data": None,
        "messages": [],
        "confirmed_contact": {"name": "", "phone": "", "email": "", "company": ""},
        "dedup_result": None,
        "active_sheet_row": None,
        "awaiting_confirmation": False,
    }

    result = await write_to_sheet(state)
    assert "messages" in result
    assert "Could not save" in result["messages"][0].content


@pytest.mark.asyncio
async def test_handle_extraction_error_mapping() -> None:
    """Verify that Gemini API errors (429, 503, general) map to the correct error messages."""
    from app.agent.nodes import handle_extraction_error

    # Case 429
    state_429: AgentState = {
        "session_id": "test-session",
        "input_type": "image",
        "file_data": None,
        "messages": [],
        "raw_extraction": {"_error": "429"},
        "confirmed_contact": None,
        "dedup_result": None,
        "active_sheet_row": None,
        "awaiting_confirmation": False,
    }
    res_429 = await handle_extraction_error(state_429)
    assert "AI service quota reached" in res_429["messages"][0].content
    assert "Please retry shortly" in res_429["messages"][0].content

    # Case 503
    state_503: AgentState = {
        "session_id": "test-session",
        "input_type": "image",
        "file_data": None,
        "messages": [],
        "raw_extraction": {"_error": "503"},
        "confirmed_contact": None,
        "dedup_result": None,
        "active_sheet_row": None,
        "awaiting_confirmation": False,
    }
    res_503 = await handle_extraction_error(state_503)
    assert "AI service temporarily unavailable" in res_503["messages"][0].content
    assert "Please retry." in res_503["messages"][0].content

    # Case General
    state_gen: AgentState = {
        "session_id": "test-session",
        "input_type": "image",
        "file_data": None,
        "messages": [],
        "raw_extraction": {"_error": "Some random APIError or JSON decode failure"},
        "confirmed_contact": None,
        "dedup_result": None,
        "active_sheet_row": None,
        "awaiting_confirmation": False,
    }
    res_gen = await handle_extraction_error(state_gen)
    assert "Could not extract contact details" in res_gen["messages"][0].content
    assert "Try a clearer image" in res_gen["messages"][0].content


@pytest.mark.asyncio
async def test_transcribe_audio_live_lookup_and_fallback() -> None:
    """Verify that transcribe_audio performs live lookup by Session ID first, then falls back to state."""
    from app.agent.nodes import transcribe_audio
    
    state: AgentState = {
        "session_id": "session-test-live-123",
        "input_type": "audio",
        "file_data": b"dummy_audio_bytes",
        "messages": [],
        "raw_extraction": None,
        "confirmed_contact": None,
        "dedup_result": None,
        "active_sheet_row": {"row_index": 99, "data": {}},
        "awaiting_confirmation": False,
    }
    
    # 1. Test live lookup success
    with patch("app.agent.nodes.audio_service.transcribe", new_callable=AsyncMock) as mock_transcribe, \
         patch("app.agent.nodes.sheets_service.get_all_rows", new_callable=AsyncMock) as mock_get_all_rows, \
         patch("app.agent.nodes.sheets_service.update_row_audio", new_callable=AsyncMock) as mock_update_row_audio, \
         patch("app.agent.nodes.storage_service.upload_audio", new_callable=AsyncMock) as mock_upload_audio:
         
        mock_transcribe.return_value = {"success": True, "transcript": "This is a transcribe test"}
        mock_get_all_rows.return_value = [
            {"Session ID": "session-test-live-123", "_row_index": 5},
            {"Session ID": "other-session", "_row_index": 6}
        ]
        mock_upload_audio.return_value = "https://public-url/session-test-live-123.wav"
        
        with patch("os.makedirs"), patch("builtins.open", mock_open()):
            res = await transcribe_audio(state)
            
        assert "Audio note transcribed and linked" in res["messages"][0].content
        mock_update_row_audio.assert_called_once_with(
            row_index=5,
            audio_url="https://public-url/session-test-live-123.wav",
            transcript="This is a transcribe test"
        )

    # 2. Test fallback to state if live lookup fails to find Session ID
    with patch("app.agent.nodes.audio_service.transcribe", new_callable=AsyncMock) as mock_transcribe, \
         patch("app.agent.nodes.sheets_service.get_all_rows", new_callable=AsyncMock) as mock_get_all_rows, \
         patch("app.agent.nodes.sheets_service.update_row_audio", new_callable=AsyncMock) as mock_update_row_audio, \
         patch("app.agent.nodes.storage_service.upload_audio", new_callable=AsyncMock) as mock_upload_audio:
          
        mock_transcribe.return_value = {"success": True, "transcript": "Fallback transcript test"}
        mock_get_all_rows.return_value = [
            {"Session ID": "non-matching-session", "_row_index": 5}
        ]
        mock_upload_audio.return_value = "https://public-url/session-test-live-123.wav"
        
        with patch("os.makedirs"), patch("builtins.open", mock_open()):
            res = await transcribe_audio(state)
            
        assert "Audio note transcribed and linked" in res["messages"][0].content
        mock_update_row_audio.assert_called_once_with(
            row_index=99,
            audio_url="https://public-url/session-test-live-123.wav",
            transcript="Fallback transcript test"
        )


