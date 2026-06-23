import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

def simulate_frontend_toasts(response_payload):
    """
    Simulates the frontend's triggerResponseToasts(res) logic
    and returns a set of currently visible toasts.
    """
    toasts = set()
    if not response_payload:
        return toasts
        
    details = response_payload.get("details", {})
    action = response_payload.get("action")
    
    if details.get("duplicate_found") or action == "duplicate_check":
        toasts.add("Duplicate contact found")
        return toasts
        
    # In the frontend, triggerResponseToasts uses an if-else if chain:
    if action == "ocr":
        if response_payload.get("success"):
            toasts.add("Verification required")
        else:
            toasts.add("OCR failed")
    elif action == "transcription":
        if details.get("transcription_completed"):
            toasts.add("Voice note transcribed")
            toasts.add("Google Sheet updated")
        else:
            toasts.add("Audio uploaded, transcription failed")
    elif action == "sheet_write" or details.get("saved_to_sheet"):
        if details.get("saved_to_sheet"):
            toasts.add("Saved to Google Sheets")
        if details.get("whatsapp_sent"):
            toasts.add("WhatsApp notification sent")
        else:
            toasts.add("WhatsApp failed to send")
            
    return toasts

@pytest.mark.asyncio
async def test_successful_save_followed_by_duplicate_toasts():
    """
    Integration test verifying:
    - successful save
    - immediately followed by duplicate upload
    Expected result:
    - duplicate warning visible
    - no save success toast visible
    - no WhatsApp success toast visible
    """
    client = TestClient(app)
    
    # 1. Create a session
    resp = client.post("/api/sessions/")
    session_id = resp.json()["session_id"]
    
    mock_extraction = {
        "name": "ANANYA KRISHNAN",
        "phone": "+91 99999 88888",
        "email": "ananya@google.com",
        "company": "Google"
    }
    
    # FIRST UPLOAD
    with patch("app.services.vision_service.vision_service.extract_contact_info", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_extraction
        files = {"image": ("card.png", b"dummy png content", "image/png")}
        resp_msg1 = client.post(f"/api/sessions/{session_id}/messages", data={"text": "Here is my card"}, files=files)
        assert resp_msg1.status_code == 200
        assert resp_msg1.json()["awaiting_confirmation"] is True

    # FIRST CONFIRMATION (Clean Save)
    # Mock sheets service to return empty sheet (no duplicate)
    with patch("app.services.sheets_service.sheets_service.get_all_rows", new_callable=AsyncMock) as mock_get_rows, \
         patch("app.services.sheets_service.sheets_service.append_row", new_callable=AsyncMock) as mock_append, \
         patch("app.services.whatsapp_service.whatsapp_service.send_notification", new_callable=AsyncMock) as mock_whatsapp:
         
         mock_get_rows.return_value = []
         mock_append.return_value = {"row_index": 2, "data": mock_extraction}
         mock_whatsapp.return_value = True
         
         resp_confirm1 = client.post(f"/api/sessions/{session_id}/confirm", json=mock_extraction)
         res1 = resp_confirm1.json()
         
         # Simulate toasts after first confirmation
         toasts1 = simulate_frontend_toasts(res1)
         assert "Saved to Google Sheets" in toasts1
         assert "WhatsApp notification sent" in toasts1
         assert "Duplicate contact found" not in toasts1

    # SECOND UPLOAD (Same Session)
    with patch("app.services.vision_service.vision_service.extract_contact_info", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_extraction
        files = {"image": ("card.png", b"dummy png content", "image/png")}
        resp_msg2 = client.post(f"/api/sessions/{session_id}/messages", data={"text": "Here is my card"}, files=files)
        assert resp_msg2.status_code == 200
        assert resp_msg2.json()["awaiting_confirmation"] is True

    # SECOND CONFIRMATION (Duplicate)
    # Mock sheets service to return the duplicate row
    second_rows = [
        {
            "Name": "ANANYA KRISHNAN",
            "Phone": "+91 99999 88888",
            "Email": "ananya@google.com",
            "Company": "Google",
            "_row_index": 2
        }
    ]
    with patch("app.services.sheets_service.sheets_service.get_all_rows", new_callable=AsyncMock) as mock_get_rows, \
         patch("app.services.sheets_service.sheets_service.append_row", new_callable=AsyncMock) as mock_append:
         
         mock_get_rows.return_value = second_rows
         
         resp_confirm2 = client.post(f"/api/sessions/{session_id}/confirm", json=mock_extraction)
         res2 = resp_confirm2.json()
         
         # Simulate toasts after second confirmation
         toasts2 = simulate_frontend_toasts(res2)
         
         # Expected result:
         # - duplicate warning visible
         # - no save success toast visible
         # - no WhatsApp success toast visible
         assert "Duplicate contact found" in toasts2
         assert "Saved to Google Sheets" not in toasts2
         assert "WhatsApp notification sent" not in toasts2
