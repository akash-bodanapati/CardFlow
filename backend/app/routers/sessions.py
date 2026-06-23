import datetime
import logging
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pymongo import MongoClient

from app.config import config

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=Dict[str, str])
async def create_session() -> Dict[str, str]:
    """
    Creates a new digitization session, initializes it in MongoDB, and returns the session_id.

    Returns:
        Dict[str, str]: A dictionary containing the newly generated 'session_id'.
    """
    session_id = str(uuid.uuid4())
    logger.info(f"Creating new session in database: {session_id}")
    try:
        client = MongoClient(config.mongo_uri)
        db = client["cardflow"]
        from zoneinfo import ZoneInfo
        now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
        date_str = now_ist.strftime("%b %d")
        label = f"New Session · {date_str}"
        db["sessions"].insert_one(
            {
                "session_id": session_id,
                "label": label,
                "created_at": now_ist,
            }
        )
        logger.info(f"Successfully created session: {session_id}")
    except Exception as e:
        logger.error(f"Error creating session record in database: {e}")
        # We still return the session_id so flow can operate in memory if DB fails temporarily

    return {"session_id": session_id}


@router.get("/", response_model=List[Dict[str, Any]])
async def list_sessions() -> List[Dict[str, Any]]:
    """
    Retrieves all digitization sessions from MongoDB. Defaults to inserting a demo session
    at the top of the list if not already present.

    Returns:
        List[Dict[str, Any]]: A list of sessions with 'session_id' and 'label'.
    """
    logger.info("Fetching list of all sessions")
    try:
        client = MongoClient(config.mongo_uri)
        db = client["cardflow"]

        # Load custom sessions collection sorted by creation date
        cursor = db["sessions"].find().sort("created_at", -1)
        sessions_list = []
        for doc in cursor:
            sessions_list.append(
                {
                    "session_id": doc["session_id"],
                    "label": doc.get("label", "New Session"),
                    "last_message": doc.get("last_message", "No messages yet"),
                }
            )

        return sessions_list
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return []


@router.delete("/{session_id}", response_model=Dict[str, str])
async def delete_session(session_id: str) -> Dict[str, str]:
    """
    Deletes a session's history and checkpoint state from MongoDB.

    Args:
        session_id (str): The ID of the session to delete.

    Returns:
        Dict[str, str]: Status message showing success or error.
    """
    logger.info(f"Deleting session and checkpointer history for session: {session_id}")
    try:
        client = MongoClient(config.mongo_uri)
        db = client["cardflow"]

        # Clean checkpointer collections
        chk_res = db["checkpoints"].delete_many({"thread_id": session_id})
        wr_res = db["checkpoint_writes"].delete_many({"thread_id": session_id})

        # Clean sessions collection
        sess_res = db["sessions"].delete_one({"session_id": session_id})

        logger.info(
            f"Deleted checkpoints: {chk_res.deleted_count}, writes: {wr_res.deleted_count}, sessions: {sess_res.deleted_count}"
        )
        return {"status": "success", "message": "Session deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
