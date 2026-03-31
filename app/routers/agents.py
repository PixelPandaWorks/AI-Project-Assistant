"""
Agents router — trigger background agents and poll their status.
"""

from __future__ import annotations

import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.database import supabase
from app.models import AgentTriggerResponse, AgentStatusResponse, MemoryEntry
from app.services import agent_service

router = APIRouter(tags=["agents"])


@router.post(
    "/projects/{project_id}/agent/trigger",
    response_model=AgentTriggerResponse,
)
async def trigger_agent(project_id: str, background_tasks: BackgroundTasks):
    """
    Trigger the background knowledge-organization agent for a project.

    The agent will:
    1. Collect all project data (brief, conversations, images, memory).
    2. Send it to Claude to organize into structured memory entries.
    3. Save the structured memory back to the database.

    Returns an execution_id that can be polled for status.
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

    # Create the execution record
    exec_result = (
        supabase.table("agent_executions")
        .insert(
            {
                "project_id": project_id,
                "status": "pending",
                "task_type": "organize_knowledge",
            }
        )
        .execute()
    )

    if not exec_result.data:
        raise HTTPException(status_code=500, detail="Failed to create agent execution")

    execution = exec_result.data[0]
    execution_id = execution["id"]

    # Schedule the background task
    background_tasks.add_task(
        agent_service.run_organizer_agent,
        project_id=project_id,
        execution_id=execution_id,
    )

    return AgentTriggerResponse(
        execution_id=execution_id,
        status="pending",
        message="Background agent has been triggered. Poll /agent/status/{execution_id} for updates.",
    )


@router.get(
    "/agent/status/{execution_id}",
    response_model=AgentStatusResponse,
)
async def get_agent_status(execution_id: str):
    """Poll the status of a background agent execution."""
    result = (
        supabase.table("agent_executions")
        .select("*")
        .eq("id", execution_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Execution not found")

    execution = result.data[0]
    return AgentStatusResponse(**execution)


@router.get(
    "/projects/{project_id}/memory",
    response_model=list[MemoryEntry],
)
async def get_project_memory(project_id: str):
    """View all stored memory entries for a project."""
    result = (
        supabase.table("project_memory")
        .select("*")
        .eq("project_id", project_id)
        .order("updated_at", desc=True)
        .execute()
    )

    return [MemoryEntry(**entry) for entry in (result.data or [])]
