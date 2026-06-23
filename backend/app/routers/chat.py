import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from pydantic import BaseModel
from pymongo import MongoClient

from app.agent.checkpointer import get_checkpointer
from app.agent.graph import builder
from app.config import config as app_config

router = APIRouter()
logger = logging.getLogger(__name__)


class ConfirmRequest(BaseModel):
    name: str
    phone: str
    email: str
    company: str


@router.post("/{session_id}/messages", response_model=Dict[str, Any])
async def send_message(
    session_id: str,
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
) -> Dict[str, Any]:
    """
    Accepts text, image, or audio input for a given session, and executes the LangGraph workflow.

    Args:
        session_id (str): Thread ID for graph execution.
        text (Optional[str]): Text message from the user.
        image (Optional[UploadFile]): Visiting card image to digitize.
        audio (Optional[UploadFile]): Voice note feedback file.

    Returns:
        Dict[str, Any]: Execution status, details on whether confirmation is needed, and last message.
    """
    logger.info(f"Incoming message for session '{session_id}'")

    # Compile graph with saver
    saver = await get_checkpointer()
    graph = builder.compile(checkpointer=saver)

    config = {"configurable": {"thread_id": session_id}}

    # Determine input type
    input_type = "text"
    file_data = None
    if image:
        input_type = "image"
        file_data = await image.read()
        logger.info("Message input type identified as IMAGE")
    elif audio:
        input_type = "audio"
        file_data = await audio.read()
        logger.info("Message input type identified as AUDIO")

    msg_content = text or (f"Uploaded {input_type}" if input_type != "text" else "")

    # Invoke the graph
    initial_state = {
        "session_id": session_id,
        "input_type": input_type,
        "file_data": file_data,
        "messages": [HumanMessage(content=msg_content)],
    }

    # Run the graph
    # Because of interrupt, it will pause if waiting for confirmation
    try:
        async for _ in graph.astream(
            initial_state, config=config, stream_mode="values"
        ):
            pass
    except Exception as e:
        logger.exception("Error executing LangGraph")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again in a moment.")

    state = await graph.aget_state(config)

    # Check if graph is paused/interrupted
    is_interrupted = len(state.next) > 0

    # Extract last AI message if present
    last_ai_message = None
    for m in reversed(state.values.get("messages", [])):
        msg_type = getattr(m, "type", "") or (
            m.get("type") if isinstance(m, dict) else ""
        )
        msg_content = getattr(m, "content", "") or (
            m.get("content") if isinstance(m, dict) else ""
        )
        if msg_type == "ai":
            last_ai_message = msg_content
            break

    logger.info(
        f"Message processed. Interrupted: {is_interrupted}, reply: {last_ai_message}"
    )

    # Update session snippet preview in MongoDB
    try:
        client = MongoClient(app_config.mongo_uri)
        db = client["cardflow"]
        snippet = last_ai_message or text or f"Uploaded {input_type}"
        # Truncate preview snippet to keep it neat
        if len(snippet) > 60:
            snippet = snippet[:57] + "..."
        db["sessions"].update_one(
            {"session_id": session_id}, {"$set": {"last_message": snippet}}, upsert=True
        )
    except Exception as db_err:
        logger.error(
            f"Failed to update session last_message snippet in MongoDB: {db_err}"
        )

    return make_response_payload(state, "send_message")


@router.get("/{session_id}/messages", response_model=Dict[str, Any])
async def get_messages(session_id: str) -> Dict[str, Any]:
    """
    Retrieves and formats the complete chat history for a session from the checkpointer.

    Args:
        session_id (str): Thread ID corresponding to the session.

    Returns:
        Dict[str, Any]: Status, message history list, and active confirmation flags.
    """
    logger.info(f"Retrieving message history for session '{session_id}'")
    saver = await get_checkpointer()
    graph = builder.compile(checkpointer=saver)
    config = {"configurable": {"thread_id": session_id}}
    state = await graph.aget_state(config)

    formatted = []
    messages = state.values.get("messages", []) or []
    for m in messages:
        m_type = getattr(m, "type", "") or (
            m.get("type") if isinstance(m, dict) else ""
        )
        m_content = getattr(m, "content", "") or (
            m.get("content") if isinstance(m, dict) else ""
        )
        if m_content:
            role = "user" if m_type == "human" else "agent"
            formatted.append({"type": role, "text": m_content})

    is_interrupted = len(state.next) > 0
    logger.info(f"Found {len(formatted)} messages. Interrupted: {is_interrupted}")
    return {
        "status": "success",
        "messages": formatted,
        "awaiting_confirmation": is_interrupted,
        "raw_extraction": state.values.get("raw_extraction"),
    }


@router.post("/{session_id}/confirm", response_model=Dict[str, Any])
async def confirm_extraction(
    session_id: str, payload: ConfirmRequest
) -> Dict[str, Any]:
    """
    Resumes graph execution by providing human confirmation data.

    Args:
        session_id (str): Thread ID for graph execution.
        payload (ConfirmRequest): Verified/edited contact details.

    Returns:
        Dict[str, Any]: Saved session response and system messages.
    """
    logger.info(f"Confirming card extraction for session '{session_id}'")
    saver = await get_checkpointer()
    graph = builder.compile(checkpointer=saver)
    config = {"configurable": {"thread_id": session_id}}

    # Resume the graph with the confirmed data
    try:
        await graph.ainvoke(Command(resume=payload.dict()), config=config)
    except Exception as e:
        logger.exception("Error resuming graph")
        raise HTTPException(
            status_code=500, detail="Something went wrong. Please try again in a moment."
        )

    # Extract final AI response from the state after graph resume
    state = await graph.aget_state(config)
    last_ai_message = None
    for m in reversed(state.values.get("messages", [])):
        msg_type = getattr(m, "type", "") or (
            m.get("type") if isinstance(m, dict) else ""
        )
        msg_content = getattr(m, "content", "") or (
            m.get("content") if isinstance(m, dict) else ""
        )
        if msg_type == "ai":
            last_ai_message = msg_content
            break

    # Update the session label and final outcome preview in custom collection
    try:
        client = MongoClient(app_config.mongo_uri)
        db = client["cardflow"]
        label = f"{payload.name} — {payload.company}"
        db["sessions"].update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "label": label,
                    "last_message": last_ai_message or "✓ Confirmed contact details",
                }
            },
            upsert=True,
        )
        logger.info(f"Updated session label to: {label}")
    except Exception as e:
        logger.error(f"Error updating session label: {e}")

    return make_response_payload(state, "confirm")


def make_response_payload(state, action_context: str) -> dict:
    import os
    state_values = state.values or {}
    
    # Extract feature statuses
    ocr_success = state_values.get("ocr_success")
    if ocr_success is None:
        raw_ext = state_values.get("raw_extraction") or {}
        ocr_success = "_error" not in raw_ext
        
    transcription_success = state_values.get("transcription_success", False)

    duplicate_found = False
    dedup = state_values.get("dedup_result")
    if dedup:
        duplicate_found = dedup.get("is_duplicate", False)

    saved_to_sheet = False
    active_row = state_values.get("active_sheet_row")
    if active_row and active_row.get("row_index"):
        saved_to_sheet = True

    whatsapp_sent = state_values.get("notification_sent", False)
    
    enriched_data = state_values.get("enriched_data")
    enrichment_completed = bool(enriched_data and (enriched_data.get("website") or enriched_data.get("linkedin")))

    # Find the last AI message
    last_ai_message = ""
    for m in reversed(state_values.get("messages", [])):
        msg_type = getattr(m, "type", "") or (m.get("type") if isinstance(m, dict) else "")
        msg_content = getattr(m, "content", "") or (m.get("content") if isinstance(m, dict) else "")
        if msg_type == "ai":
            last_ai_message = msg_content
            break

    # Enforce strict assertions and state isolation to prevent LangGraph state pollution
    if duplicate_found:
        saved_to_sheet = False
        whatsapp_sent = False
        enrichment_completed = False

    input_type = state_values.get("input_type", "text")
    if input_type != "audio":
        transcription_success = False
    
    if action_context == "confirm":
        if duplicate_found:
            action = "duplicate_check"
            success = False
            status = "warning"
            message = last_ai_message or "Duplicate found. Contact already exists."
        elif saved_to_sheet:
            action = "sheet_write"
            success = True
            if whatsapp_sent:
                status = "success"
                message = last_ai_message or "Contact saved successfully. Manager notification sent."
            else:
                status = "warning"
                message = last_ai_message or "Contact saved successfully. Manager notification could not be delivered at this time."
        else:
            action = "sheet_write"
            success = False
            status = "error"
            message = "Failed to save contact. Please try again."
    else:
        if input_type == "image":
            action = "ocr"
            if ocr_success:
                success = True
                status = "success"
                message = last_ai_message or "I extracted the following contact info from the card. Please review and confirm:"
            else:
                success = False
                status = "error"
                err_detail = (state_values.get("raw_extraction") or {}).get("_error", "")
                if err_detail == "429":
                    message = "AI service quota reached. Please retry shortly."
                elif err_detail == "503":
                    message = "AI service temporarily unavailable. Please retry."
                else:
                    message = "Could not extract contact details. Try a clearer image."
        elif input_type == "audio":
            action = "transcription"
            if transcription_success:
                success = True
                status = "success"
                message = last_ai_message or f"Audio note transcribed and linked to contact: {state_values.get('audio_transcript')}"
            else:
                success = False
                status = "warning"
                message = last_ai_message or "Audio note uploaded successfully. Transcription is temporarily unavailable."
        else:
            action = "text"
            success = True
            status = "success"
            message = last_ai_message

    return {
        "success": success,
        "action": action,
        "status": status,
        "message": message,
        "awaiting_confirmation": len(state.next) > 0,
        "raw_extraction": state_values.get("raw_extraction"),
        "details": {
            "duplicate_found": duplicate_found,
            "saved_to_sheet": saved_to_sheet,
            "whatsapp_sent": whatsapp_sent,
            "enrichment_completed": enrichment_completed,
            "transcription_completed": transcription_success
        }
    }
