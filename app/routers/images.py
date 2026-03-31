"""
Images router — list and view project images.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.database import supabase
from app.models import ImageResponse

router = APIRouter(prefix="/projects/{project_id}/images", tags=["images"])


@router.get("/", response_model=list[ImageResponse])
async def list_images(project_id: str):
    """List all images generated for a project."""
    result = (
        supabase.table("images")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )

    return [ImageResponse(**img) for img in (result.data or [])]


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(project_id: str, image_id: str):
    """Get a specific image by ID."""
    result = (
        supabase.table("images")
        .select("*")
        .eq("id", image_id)
        .eq("project_id", project_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Image not found")

    return ImageResponse(**result.data[0])
