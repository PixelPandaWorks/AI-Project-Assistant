"""
Chat router — sends messages to Claude with the full tool loop.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.database import supabase
from app.models import ChatRequest, ChatResponse, ChatMessageResponse
from app.services import claude_service

router = APIRouter(prefix="/projects/{project_id}/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def send_message(project_id: str, body: ChatRequest):
    """
    Send a message to Claude for a specific project.

    Claude will:
    1. Load project memory (via tool call)
    2. Process the message with access to tools
    3. Execute any tool calls (generate image, analyze image, save memory, etc.)
    4. Return the final response

    The full conversation is persisted to the database.
    """
    # Verify project exists
    project_result = (
        supabase.table("projects")
        .select("id")
        .eq("id", project_id)
        .execute()
    )
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        result = await claude_service.chat(project_id, body.message)
        return ChatResponse(
            response=result["response"],
            tool_calls=result.get("tool_calls", []),
            images_generated=result.get("images_generated", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/", response_model=list[ChatMessageResponse])
async def get_conversation_history(project_id: str):
    """Retrieve the full conversation history for a project."""
    result = (
        supabase.table("conversations")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at")
        .execute()
    )

    return [ChatMessageResponse(**msg) for msg in (result.data or [])]
