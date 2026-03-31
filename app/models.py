"""
Pydantic models for request/response validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Project ──────────────────────────────────────────

class ProjectBriefCreate(BaseModel):
    """Fields for creating/updating a project brief."""
    title: str
    description: Optional[str] = None
    goals: list[str] = Field(default_factory=list)
    reference_links: list[str] = Field(default_factory=list)
    target_audience: Optional[str] = None
    tech_stack: Optional[str] = None
    status: str = "active"


class ProjectCreate(BaseModel):
    """Request body for creating a new project."""
    name: str
    brief: ProjectBriefCreate


class ProjectBriefResponse(BaseModel):
    """Response model for a project brief."""
    id: str
    project_id: str
    title: str
    description: Optional[str] = None
    goals: list[str] = Field(default_factory=list)
    reference_links: list[str] = Field(default_factory=list)
    target_audience: Optional[str] = None
    tech_stack: Optional[str] = None
    status: str = "active"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProjectResponse(BaseModel):
    """Response model for a project."""
    id: str
    name: str
    created_at: Optional[str] = None
    brief: Optional[ProjectBriefResponse] = None


# ── Chat ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request body for sending a chat message."""
    message: str


class ChatMessageResponse(BaseModel):
    """A single conversation message."""
    id: str
    project_id: str
    role: str
    content: str
    tool_calls: Optional[Any] = None
    created_at: Optional[str] = None


class ChatResponse(BaseModel):
    """Response after processing a chat message through Claude."""
    response: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    images_generated: list[dict[str, Any]] = Field(default_factory=list)


# ── Images ───────────────────────────────────────────

class ImageResponse(BaseModel):
    """Response model for a generated image."""
    id: str
    project_id: str
    prompt: str
    url: str
    analysis: Optional[str] = None
    created_at: Optional[str] = None


# ── Agent ────────────────────────────────────────────

class AgentTriggerResponse(BaseModel):
    """Response when an agent execution is triggered."""
    execution_id: str
    status: str
    message: str


class AgentStatusResponse(BaseModel):
    """Response when polling an agent execution status."""
    id: str
    project_id: str
    status: str
    task_type: Optional[str] = None
    result: Optional[Any] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ── Memory ───────────────────────────────────────────

class MemoryEntry(BaseModel):
    """A single memory entry."""
    id: str
    project_id: str
    memory_key: str
    memory_value: Any
    source: str = "user"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
