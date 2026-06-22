from typing import Annotated, List, Literal, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    session_id: str
    messages: Annotated[List[BaseMessage], add_messages]
    input_type: Literal["image", "audio", "text"]
    file_data: Optional[bytes]
    raw_extraction: Optional[dict]  # unverified output from vision_service
    confirmed_contact: Optional[dict]  # name, phone, email, company after HITL confirm
    dedup_result: Optional[dict]  # {"is_duplicate": bool, "matched_row": dict|None}
    active_sheet_row: Optional[
        dict
    ]  # row index + data this session is currently linked to
    audio_transcript: Optional[str]
    notification_sent: bool
    awaiting_confirmation: bool
    enriched_data: Optional[dict]
