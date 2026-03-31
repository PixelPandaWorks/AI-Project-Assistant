"""
Memory service — CRUD operations on the project_memory table.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.database import supabase


async def get_project_memory(project_id: str) -> list[dict[str, Any]]:
    """Retrieve all memory entries for a project."""
    result = (
        supabase.table("project_memory")
        .select("*")
        .eq("project_id", project_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data or []


async def save_memory(
    project_id: str,
    memory_key: str,
    memory_value: Any,
    source: str = "assistant",
) -> dict[str, Any]:
    """
    Upsert a memory entry.  If a memory_key already exists for this project,
    it will be updated; otherwise a new row is inserted.
    """
    # Wrap raw strings in a JSON-compatible dict
    if isinstance(memory_value, str):
        value_json = {"content": memory_value}
    else:
        value_json = memory_value

    now = datetime.now(timezone.utc).isoformat()

    # Try to find existing
    existing = (
        supabase.table("project_memory")
        .select("id")
        .eq("project_id", project_id)
        .eq("memory_key", memory_key)
        .execute()
    )

    if existing.data:
        # Update
        result = (
            supabase.table("project_memory")
            .update({"memory_value": value_json, "source": source, "updated_at": now})
            .eq("id", existing.data[0]["id"])
            .execute()
        )
        return result.data[0] if result.data else {}
    else:
        # Insert
        result = (
            supabase.table("project_memory")
            .insert(
                {
                    "project_id": project_id,
                    "memory_key": memory_key,
                    "memory_value": value_json,
                    "source": source,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            .execute()
        )
        return result.data[0] if result.data else {}


async def delete_memory(project_id: str, memory_key: str) -> bool:
    """Delete a specific memory entry."""
    supabase.table("project_memory").delete().eq(
        "project_id", project_id
    ).eq("memory_key", memory_key).execute()
    return True
