from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (_extraction_looks_valid, check_duplicate,
                             enrich_company, extract_card, handle_duplicate,
                             handle_extraction_error, notify_whatsapp,
                             process_text, request_confirmation,
                             transcribe_audio, write_to_sheet)
from app.agent.state import AgentState


def route_input(
    state: AgentState,
) -> Literal["extract_card", "transcribe_audio", "process_text", "__end__"]:
    print(f"Routing input type: {state.get('input_type')}")
    input_type = state.get("input_type")
    if input_type == "image":
        return "extract_card"
    elif input_type == "audio":
        return "transcribe_audio"
    elif input_type == "text":
        return "process_text"
    else:
        return "__end__"


def route_after_extraction(
    state: AgentState,
) -> Literal["request_confirmation", "handle_extraction_error"]:
    """
    After extract_card runs, check whether the extraction produced usable data.
    An all-empty result (or one tagged with _error) routes to the error node,
    preventing a blank row from ever reaching the sheet.
    """
    extraction = state.get("raw_extraction") or {}
    if _extraction_looks_valid(extraction):
        return "request_confirmation"
    return "handle_extraction_error"


def route_dedup(state: AgentState) -> Literal["handle_duplicate", "write_to_sheet"]:
    is_dup = state.get("dedup_result", {}).get("is_duplicate", False)
    if is_dup:
        return "handle_duplicate"
    return "write_to_sheet"


builder = StateGraph(AgentState)

# --- Nodes ---
builder.add_node("extract_card", extract_card)
builder.add_node("handle_extraction_error", handle_extraction_error)
builder.add_node("request_confirmation", request_confirmation)
builder.add_node("check_duplicate", check_duplicate)
builder.add_node("handle_duplicate", handle_duplicate)
builder.add_node("write_to_sheet", write_to_sheet)
builder.add_node("notify_whatsapp", notify_whatsapp)
builder.add_node("transcribe_audio", transcribe_audio)
builder.add_node("enrich_company", enrich_company)
builder.add_node("process_text", process_text)

# --- Edges ---
builder.add_conditional_edges(START, route_input)

# After extraction: success → confirmation interrupt; failure → error message
builder.add_conditional_edges("extract_card", route_after_extraction)
builder.add_edge("handle_extraction_error", END)

# After human confirms → dedup check
builder.add_edge("request_confirmation", "check_duplicate")

# Dedup routing
builder.add_conditional_edges("check_duplicate", route_dedup)
builder.add_edge("handle_duplicate", END)

# Happy path: write → enrich → notify
builder.add_edge("write_to_sheet", "enrich_company")
builder.add_edge("enrich_company", "notify_whatsapp")
builder.add_edge("notify_whatsapp", END)

# Audio path
builder.add_edge("transcribe_audio", END)

# Text path
builder.add_edge("process_text", END)
