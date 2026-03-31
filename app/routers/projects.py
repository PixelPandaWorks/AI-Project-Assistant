"""
Projects router — CRUD operations for projects and briefs.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.database import supabase
from app.models import (
    ProjectCreate,
    ProjectResponse,
    ProjectBriefCreate,
    ProjectBriefResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate):
    """Create a new project with an associated brief."""

    # 1. Create the project
    project_result = (
        supabase.table("projects")
        .insert({"name": body.name})
        .execute()
    )

    if not project_result.data:
        raise HTTPException(status_code=500, detail="Failed to create project")

    project = project_result.data[0]
    project_id = project["id"]

    # 2. Create the brief
    brief_data = {
        "project_id": project_id,
        "title": body.brief.title,
        "description": body.brief.description,
        "goals": body.brief.goals,
        "reference_links": body.brief.reference_links,
        "target_audience": body.brief.target_audience,
        "tech_stack": body.brief.tech_stack,
        "status": body.brief.status,
    }

    brief_result = (
        supabase.table("project_briefs")
        .insert(brief_data)
        .execute()
    )

    brief = brief_result.data[0] if brief_result.data else None

    return ProjectResponse(
        id=project["id"],
        name=project["name"],
        created_at=project.get("created_at"),
        brief=ProjectBriefResponse(**brief) if brief else None,
    )


@router.get("/", response_model=list[ProjectResponse])
async def list_projects():
    """List all projects with their briefs."""
    projects_result = (
        supabase.table("projects")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    projects = projects_result.data or []
    response = []

    for proj in projects:
        # Fetch brief for each project
        brief_result = (
            supabase.table("project_briefs")
            .select("*")
            .eq("project_id", proj["id"])
            .execute()
        )
        brief = brief_result.data[0] if brief_result.data else None

        response.append(
            ProjectResponse(
                id=proj["id"],
                name=proj["name"],
                created_at=proj.get("created_at"),
                brief=ProjectBriefResponse(**brief) if brief else None,
            )
        )

    return response


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a specific project with its brief."""
    project_result = (
        supabase.table("projects")
        .select("*")
        .eq("id", project_id)
        .execute()
    )

    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    proj = project_result.data[0]

    brief_result = (
        supabase.table("project_briefs")
        .select("*")
        .eq("project_id", project_id)
        .execute()
    )
    brief = brief_result.data[0] if brief_result.data else None

    return ProjectResponse(
        id=proj["id"],
        name=proj["name"],
        created_at=proj.get("created_at"),
        brief=ProjectBriefResponse(**brief) if brief else None,
    )


@router.put("/{project_id}/brief", response_model=ProjectBriefResponse)
async def update_brief(project_id: str, body: ProjectBriefCreate):
    """Update a project's brief."""

    # Verify project exists
    project_result = (
        supabase.table("projects")
        .select("id")
        .eq("id", project_id)
        .execute()
    )
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update the brief
    update_data = {
        "title": body.title,
        "description": body.description,
        "goals": body.goals,
        "reference_links": body.reference_links,
        "target_audience": body.target_audience,
        "tech_stack": body.tech_stack,
        "status": body.status,
    }

    result = (
        supabase.table("project_briefs")
        .update(update_data)
        .eq("project_id", project_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Brief not found for this project")

    return ProjectBriefResponse(**result.data[0])
