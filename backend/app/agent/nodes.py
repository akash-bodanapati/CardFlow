import json
import logging
import os
import re
from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt

from app.agent.state import AgentState
from app.config import config
from app.services.audio_service import audio_service
from app.services.dedup_service import is_duplicate
from app.services.sheets_service import sheets_service
from app.services.vision_service import vision_service
from app.services.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)


def _extraction_looks_valid(extraction: Optional[Dict[str, Any]]) -> bool:
    """
    Validates if the raw extraction dictionary contains sufficient contact information.

    Args:
        extraction (Optional[Dict[str, Any]]): The extracted contact fields.

    Returns:
        bool: True if at least one of Name, Phone, or Email is present and non-empty.
    """
    if not extraction:
        return False
    return bool(
        (extraction.get("name") or "").strip()
        or (extraction.get("phone") or "").strip()
        or (extraction.get("email") or "").strip()
    )


async def extract_card(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node to extract contact info from a business card image using Gemini.

    Args:
        state (AgentState): Current graph state containing the uploaded image.

    Returns:
        Dict[str, Any]: A dictionary updating the raw_extraction field.
    """
    logger.info("LangGraph Node: extract_card - starting extraction")
    file_data = state.get("file_data")
    if not file_data:
        logger.error("No file_data found in state during card extraction")
        raise ValueError("No file_data found in state")

    try:
        # Save card image to disk so the frontend can retrieve it as a thumbnail
        session_id = state.get("session_id", "default")
        os.makedirs("uploads", exist_ok=True)
        file_path = f"uploads/{session_id}_card.png"
        with open(file_path, "wb") as f:
            f.write(file_data)
        logger.info(f"Saved uploaded card image locally to {file_path}")

        extraction = await vision_service.extract_contact_info(file_data)
        logger.info(
            f"Card extraction completed. Found: {extraction.get('name')} from {extraction.get('company')}"
        )
        msg = AIMessage(
            content="I extracted the following contact info from the card. Please review and confirm:"
        )
        return {"raw_extraction": extraction, "messages": [msg]}
    except Exception as e:
        from google.genai import errors
        if isinstance(e, errors.APIError):
            logger.exception("Gemini API error during extraction")
            code = getattr(e, "code", None)
            err_msg = "429" if code == 429 else ("503" if code == 503 else f"APIError {code}: {e}")
        else:
            logger.exception("Failed to extract contact info from card image")
            err_msg = str(e)
        # Signal failure with a sentinel so graph can route to error node
        return {
            "raw_extraction": {
                "_error": err_msg,
                "name": "",
                "phone": "",
                "email": "",
                "company": "",
            }
        }


async def request_confirmation(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node that pauses graph execution via interrupt, waiting for human confirmation.

    Args:
        state (AgentState): Current graph state.

    Returns:
        Dict[str, Any]: A dictionary updating confirmed_contact and resetting awaiting_confirmation.
    """
    logger.info(
        "LangGraph Node: request_confirmation - triggering human-in-the-loop interrupt"
    )
    # LangGraph interrupt pauses execution here until human input is received
    user_confirmation = interrupt(
        {"type": "request_confirmation", "data": state.get("raw_extraction")}
    )

    logger.info(f"Graph resumed with user confirmation: {user_confirmation}")
    conf_msg = HumanMessage(
        content=f"✓ Confirmed: {user_confirmation.get('name')} ({user_confirmation.get('company')})"
    )
    # user_confirmation is the resumed data sent back by the /confirm endpoint
    return {
        "confirmed_contact": user_confirmation,
        "awaiting_confirmation": False,
        "messages": [conf_msg],
    }


async def handle_extraction_error(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node that runs when card extraction fails or returns completely empty data.

    Args:
        state (AgentState): Current graph state.

    Returns:
        Dict[str, Any]: A dictionary appending a system failure notification message.
    """
    logger.info(
        "LangGraph Node: handle_extraction_error - card OCR failed or returned invalid data"
    )
    error_detail = (state.get("raw_extraction") or {}).get(
        "_error", ""
    )
    
    if error_detail == "429":
        msg_content = "AI service quota reached.\nPlease retry shortly."
    elif error_detail == "503":
        msg_content = "AI service temporarily unavailable.\nPlease retry."
    else:
        msg_content = "Could not extract contact details.\nTry a clearer image."
        
    msg = AIMessage(content=msg_content)
    return {"messages": [msg]}


async def check_duplicate(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node to verify if the contact already exists in Google Sheets.

    Args:
        state (AgentState): Current graph state containing the confirmed contact info.

    Returns:
        Dict[str, Any]: A dictionary updating dedup_result.
    """
    logger.info("LangGraph Node: check_duplicate - starting de-duplication check")
    contact = state.get("confirmed_contact")
    if not contact:
        logger.warning("No confirmed contact found in state for duplicate check")
        return {"dedup_result": {"is_duplicate": False}}

    rows = await sheets_service.get_all_rows()
    matched = is_duplicate(contact.get("phone", ""), contact.get("email", ""), rows)

    if matched:
        logger.info(
            f"Duplicate contact found in row: {matched.get('Name')} ({matched.get('Company')})"
        )
    else:
        logger.info("No duplicate found. Clean record.")

    return {
        "dedup_result": {"is_duplicate": matched is not None, "matched_row": matched}
    }


async def handle_duplicate(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node executing when a duplicate contact is detected in Google Sheets.

    Args:
        state (AgentState): Current graph state.

    Returns:
        Dict[str, Any]: A dictionary containing a duplication alert message.
    """
    logger.info(
        "LangGraph Node: handle_duplicate - contact already exists, aborting save"
    )
    matched = state.get("dedup_result", {}).get("matched_row", {})
    msg = AIMessage(
        content=f"Duplicate found! Contact already exists: {matched.get('Name')}"
    )
    return {"messages": [msg]}


async def write_to_sheet(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node that appends the confirmed contact data to the Google Sheet.

    Args:
        state (AgentState): Current graph state.

    Returns:
        Dict[str, Any]: A dictionary containing the saved sheet row indices and data.
    """
    logger.info("LangGraph Node: write_to_sheet - saving contact to Google Sheets")
    contact = state.get("confirmed_contact")

    # Guard: never write a blank row — at least name or phone must be present
    name = (contact.get("name") or "").strip() if contact else ""
    phone = (contact.get("phone") or "").strip() if contact else ""
    email = (contact.get("email") or "").strip() if contact else ""
    company = (contact.get("company") or "").strip() if contact else ""

    if not name and not phone and not email:
        logger.warning(
            "write_to_sheet: BLOCKED — Name, Phone, and Email are empty. Refusing write."
        )
        msg = AIMessage(
            content="Could not save: contact data is empty. Please try uploading a clearer card image."
        )
        return {"messages": [msg]}

    result = await sheets_service.append_row(
        name=name,
        phone=phone,
        email=email,
        company=company,
        session_id=state.get("session_id", ""),
    )
    logger.info(
        f"Saved contact successfully to Google Sheets row index {result.get('row_index')}"
    )
    return {"active_sheet_row": result}


async def notify_whatsapp(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node to alert the manager via WhatsApp Cloud API about a newly added contact.

    Args:
        state (AgentState): Current graph state.

    Returns:
        Dict[str, Any]: A dictionary tracking notification success and adding a success response.
    """
    logger.info("LangGraph Node: notify_whatsapp - sending manager notification")
    contact = state.get("confirmed_contact") or {}
    success = await whatsapp_service.send_notification(
        name=contact.get("name", ""), company=contact.get("company", "")
    )
    if success:
        content = "Contact saved successfully and WhatsApp notification sent."
    else:
        content = (
            "Contact saved successfully, but the WhatsApp notification failed to send."
        )
    msg = AIMessage(content=content)
    logger.info(f"WhatsApp notification dispatch status: {success}")
    return {"notification_sent": success, "messages": [msg]}


def get_validated_public_audio_url(session_id: str) -> str:
    """Constructs and validates the public audio note URL, blocking localhost and 127.0.0.1 in production."""
    base_url = (config.public_base_url or "").strip()
    env_mode = (config.env or "development").strip().lower()

    if env_mode == "development":
        if not base_url:
            logger.warning("Missing PUBLIC_BASE_URL in development mode. Falling back to http://localhost:8000")
            base_url = "http://localhost:8000"
        return f"{base_url.rstrip('/')}/uploads/{session_id}.wav"
    else:
        # production
        if not base_url:
            raise ValueError("Missing PUBLIC_BASE_URL environment variable.")
        if "localhost" in base_url or "127.0.0.1" in base_url:
            raise ValueError(
                "Invalid PUBLIC_BASE_URL: localhost and 127.0.0.1 are blocked for external reviewers."
            )
        return f"{base_url.rstrip('/')}/uploads/{session_id}.wav"


async def transcribe_audio(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node that transcribes a voice note and links it to the active sheet contact.

    Args:
        state (AgentState): Current graph state containing the voice note audio file data.

    Returns:
        Dict[str, Any]: A dictionary mapping the transcription results.
    """
    logger.info("LangGraph Node: transcribe_audio - transcribing voice note")
    file_data = state.get("file_data") or b""
    transcript = await audio_service.transcribe(file_data)

    active_row = state.get("active_sheet_row")
    session_id = state.get("session_id", "default")
    logger.info(f"Audio linking process - Session ID used: '{session_id}'")

    # Live lookup: find row by scanning sheet for Session ID
    row_index = None
    try:
        rows = await sheets_service.get_all_rows()
        for r in rows:
            if r.get("Session ID") == session_id:
                row_index = r.get("_row_index")
                logger.info(f"Live Lookup: row found in sheet for Session ID '{session_id}' at row_index: {row_index}")
                break
    except Exception as e:
        logger.warning(f"Live Lookup by Session ID failed: {e}")

    # Fallback to state if not found live
    if not row_index and active_row:
        row_index = active_row.get("row_index")
        logger.info(f"Fallback: row_index resolved from state: {row_index}")

    if row_index:
        os.makedirs("uploads", exist_ok=True)
        file_path = f"uploads/{session_id}.wav"
        with open(file_path, "wb") as f:
            f.write(file_data)
        logger.info(f"Saved audio file locally to {file_path}")

        try:
            audio_url = get_validated_public_audio_url(session_id)
            logger.info(f"Column mapping used: Audio URL -> Column F, Audio Notes -> Column G")
            await sheets_service.update_row_audio(
                row_index=row_index,
                audio_url=audio_url,
                transcript=transcript,
            )
            logger.info(
                f"Updated Google Sheet row successfully - row number updated: {row_index}"
            )
            msg = AIMessage(
                content=f"Audio note transcribed and linked to contact: {transcript}"
            )
        except ValueError as e:
            logger.error(f"Audio URL validation failed: {e}")
            msg = AIMessage(content=f"Error linking audio: {str(e)}")
    else:
        logger.warning(
            "Voice note received but no active contact row (live or in state) could be found. Session ID: %s",
            session_id,
        )
        msg = AIMessage(
            content="Transcribed audio, but no active contact session found to link to."
        )

    return {"audio_transcript": transcript, "messages": [msg]}


async def enrich_company(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node that fetches company details using Gemini (website/LinkedIn).

    Args:
        state (AgentState): Current graph state.

    Returns:
        Dict[str, Any]: A dictionary containing website and linkedin URLs.
    """
    logger.info("LangGraph Node: enrich_company - enriching company metadata")
    contact = state.get("confirmed_contact") or {}
    company = contact.get("company", "")
    if not company:
        logger.info("No company name present in contact. Skipping enrichment.")
        return {}
    try:
        prompt = (
            f"Provide the official website URL and LinkedIn page URL for the company: '{company}'. "
            "Return ONLY a JSON object with keys 'website' and 'linkedin'. If unknown, return empty strings."
        )
        response = vision_service.client.models.generate_content(
            model=vision_service.model,
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
            return {"enriched_data": data}
        except json.JSONDecodeError as decode_err:
            logger.error(f"JSONDecodeError parsing company enrichment response. Raw text: '{text}'. Error: {decode_err}")
            return {}
            
    except Exception as e:
        logger.warning(f"Failed to enrich company {company}: {e}")
        return {}


async def process_text(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node executing on user text follow-up to support contextual conversation.

    Args:
        state (AgentState): Current graph state.

    Returns:
        Dict[str, Any]: A dictionary containing the LLM-generated contextual response.
    """
    logger.info("LangGraph Node: process_text - handling text message")
    messages = state.get("messages", [])
    user_text = ""
    for m in reversed(messages):
        m_type = getattr(m, "type", "") or (
            m.get("type") if isinstance(m, dict) else ""
        )
        m_content = getattr(m, "content", "") or (
            m.get("content") if isinstance(m, dict) else ""
        )
        if m_type == "human" and m_content:
            user_text = m_content
            break

    active_row = state.get("active_sheet_row")

    if not active_row:
        if state.get("raw_extraction") and state.get("awaiting_confirmation"):
            logger.info(
                "Graph is waiting for confirmation. Prompting user to confirm details."
            )
            msg = AIMessage(
                content="Please review and confirm the extracted contact details above to save them."
            )
            return {"messages": [msg]}

        logger.info("No active session found. Prompting user to upload a card.")
        msg = AIMessage(content="Please upload a business card image to get started.")
        return {"messages": [msg]}

    contact = active_row.get("data", {})
    name = (
        contact.get("Name", "")
        or active_row.get("Name", "")
        or state.get("confirmed_contact", {}).get("name", "")
    )
    company = (
        contact.get("Company", "")
        or active_row.get("Company", "")
        or state.get("confirmed_contact", {}).get("company", "")
    )

    try:
        prompt = f"""
        The user is in a session where they have already successfully digitized a business card for '{name}' from the company '{company}'.
        The user just typed this follow-up message: "{user_text}"
        
        Analyze if this message is a contextual follow-up (e.g. asking about the contact, asking to add a note, greeting/polite conversation about the card, etc.) or if it is completely unrelated to the workflow of business card digitization/the saved contact.
        
        If it is RELATED to the contact or workflow:
        Respond to their query contextually, acknowledging the saved contact '{name}' of '{company}'. If they want to add a note, tell them they can upload a voice note or ask them to clarify. Keep the response helpful and friendly.
        
        If it is UNRELATED:
        Respond exactly: "I'm a business card digitizer. Please upload a card image or voice note."
        
        Return ONLY your response to the user.
        """
        response = vision_service.client.models.generate_content(
            model=vision_service.model,
            contents=prompt,
        )
        msg_content = response.text.strip()
        msg = AIMessage(content=msg_content)
        logger.info("Contextual reply generated successfully")
        return {"messages": [msg]}
    except Exception as e:
        logger.exception("Failed contextual text processing")
        msg = AIMessage(
            content="I'm a business card digitizer. Please upload a card image or voice note."
        )
        return {"messages": [msg]}
