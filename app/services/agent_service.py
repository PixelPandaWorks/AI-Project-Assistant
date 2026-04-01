"""
Background agent service — organizes project knowledge into structured memory.

This agent is triggered via an API endpoint and runs in the background.
It collects all project data (brief, conversations, images, existing memory),
sends it to Claude with a structuring prompt, and saves the organized
knowledge back into the project_memory table.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import anthropic

from app.config import settings
from app.database import supabase

logger = logging.getLogger(__name__)

# Use a separate client instance for the agent
agent_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

AGENT_SYSTEM_PROMPT = """You are a knowledge organization agent. Your job is to take all available project data and organize it into structured, retrievable memory entries.

You will receive:
- The project brief (title, description, goals, etc.)
- Conversation history
- Generated images and their analyses
- Existing memory entries

Your task:
1. Analyze all the data holistically.
2. Identify key themes, decisions, requirements, and insights.
3. Organize them into clear categories.

Return your output as a JSON array of memory entries, where each entry has:
- "memory_key": A descriptive, snake_case key (e.g., "project_overview", "technical_requirements", "design_decisions", "key_stakeholders", "timeline_milestones")
- "memory_value": A detailed, well-structured description of that knowledge area

Categories to consider:
- project_overview: High-level summary of what the project is about
- project_goals: Specific goals and objectives
- technical_requirements: Tech stack, integrations, constraints
- design_decisions: Any design or architecture decisions made
- key_insights: Important insights from conversations
- action_items: Outstanding tasks or next steps
- reference_materials: Important links and resources
- team_preferences: Preferences expressed during conversations

Return ONLY the JSON array, no other text."""


async def run_organizer_agent(project_id: str, execution_id: str) -> None:
    """
    Background task: organize all project data into structured memory.

    Updates the agent_executions table with status changes throughout.
    """
    try:
        # Mark as running
        _update_execution_status(execution_id, "running")
        logger.info(f"\n{'='*60}")
        logger.info(f"🤖 [AGENT] Background agent started")
        logger.info(f"📁 [AGENT] Project ID: {project_id}")
        logger.info(f"🆔 [AGENT] Execution ID: {execution_id}")

        # 1. Gather all project data
        logger.info(f"📥 [AGENT] Gathering all project data from Supabase...")
        logger.info(f"🔑 [AGENT] Using SUPABASE_KEY for data retrieval")
        project_data = await _gather_project_data(project_id)
        logger.info(f"✅ [AGENT] Data gathered: {len(project_data.get('conversations', []))} conversations, {len(project_data.get('images', []))} images, {len(project_data.get('existing_memory', []))} memory entries")

        # 2. Build the prompt
        prompt = _build_organization_prompt(project_data)

        # 3. Send to Claude
        logger.info(f"🤖 [AGENT] Sending to Claude for organization")
        logger.info(f"🔑 [AGENT] Using ANTHROPIC_API_KEY → Claude API")
        logger.info(f"🤖 [AGENT] Model: {settings.CLAUDE_MODEL}")
        logger.info(f"⏳ [AGENT] Calling Claude API...")
        response = agent_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4096,
            system=AGENT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        logger.info(f"✅ [AGENT] Claude response received")

        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        # 4. Parse the structured output
        logger.info(f"📋 [AGENT] Parsing structured output ({len(response_text)} chars)")
        memory_entries = _parse_agent_output(response_text)
        logger.info(f"✅ [AGENT] Parsed {len(memory_entries)} memory entries")

        # 5. Save each memory entry to the database
        saved_count = 0
        for entry in memory_entries:
            memory_key = entry.get("memory_key", "")
            memory_value = entry.get("memory_value", "")

            if not memory_key or not memory_value:
                continue

            # Wrap string values in JSON
            if isinstance(memory_value, str):
                value_json = {"content": memory_value}
            else:
                value_json = memory_value

            now = datetime.now(timezone.utc).isoformat()

            # Upsert: check if key already exists
            existing = (
                supabase.table("project_memory")
                .select("id")
                .eq("project_id", project_id)
                .eq("memory_key", memory_key)
                .execute()
            )

            if existing.data:
                supabase.table("project_memory").update(
                    {
                        "memory_value": value_json,
                        "source": "agent",
                        "updated_at": now,
                    }
                ).eq("id", existing.data[0]["id"]).execute()
            else:
                supabase.table("project_memory").insert(
                    {
                        "project_id": project_id,
                        "memory_key": memory_key,
                        "memory_value": value_json,
                        "source": "agent",
                        "created_at": now,
                        "updated_at": now,
                    }
                ).execute()

            saved_count += 1

        # 6. Mark as completed
        _update_execution_status(
            execution_id,
            "completed",
            result={
                "memory_entries_saved": saved_count,
                "categories": [e["memory_key"] for e in memory_entries if "memory_key" in e],
                "summary": f"Organized project data into {saved_count} structured memory entries.",
            },
        )
        logger.info(f"✅ [AGENT] Completed! Saved {saved_count} memory entries for project {project_id}")
        logger.info(f"{'='*60}")

    except Exception as e:
        logger.error(f"❌ [AGENT] Failed for project {project_id}: {str(e)}")
        _update_execution_status(
            execution_id,
            "failed",
            result={"error": str(e)},
        )


async def _gather_project_data(project_id: str) -> dict[str, Any]:
    """Fetch all relevant data for a project."""

    # Project info
    project = (
        supabase.table("projects")
        .select("*")
        .eq("id", project_id)
        .execute()
    )

    # Brief
    brief = (
        supabase.table("project_briefs")
        .select("*")
        .eq("project_id", project_id)
        .execute()
    )

    # Conversations
    conversations = (
        supabase.table("conversations")
        .select("role, content, created_at")
        .eq("project_id", project_id)
        .order("created_at")
        .execute()
    )

    # Images
    images = (
        supabase.table("images")
        .select("prompt, url, analysis, created_at")
        .eq("project_id", project_id)
        .order("created_at")
        .execute()
    )

    # Existing memory
    memory = (
        supabase.table("project_memory")
        .select("memory_key, memory_value, source")
        .eq("project_id", project_id)
        .execute()
    )

    return {
        "project": project.data[0] if project.data else {},
        "brief": brief.data[0] if brief.data else {},
        "conversations": conversations.data or [],
        "images": images.data or [],
        "existing_memory": memory.data or [],
    }


def _build_organization_prompt(data: dict[str, Any]) -> str:
    """Build a comprehensive prompt from all project data."""
    sections = []

    # Project info
    if data["project"]:
        sections.append(f"## Project\nName: {data['project'].get('name', 'Unknown')}")

    # Brief
    if data["brief"]:
        brief = data["brief"]
        brief_text = f"""## Project Brief
Title: {brief.get('title', 'N/A')}
Description: {brief.get('description', 'N/A')}
Goals: {json.dumps(brief.get('goals', []))}
Reference Links: {json.dumps(brief.get('reference_links', []))}
Target Audience: {brief.get('target_audience', 'N/A')}
Tech Stack: {brief.get('tech_stack', 'N/A')}
Status: {brief.get('status', 'N/A')}"""
        sections.append(brief_text)

    # Conversations
    if data["conversations"]:
        conv_lines = []
        for msg in data["conversations"][-30:]:  # Last 30 messages
            conv_lines.append(f"[{msg['role']}]: {msg['content']}")
        sections.append("## Conversation History\n" + "\n".join(conv_lines))

    # Images
    if data["images"]:
        img_lines = []
        for img in data["images"]:
            line = f"- Prompt: {img['prompt']}"
            if img.get("analysis"):
                line += f"\n  Analysis: {img['analysis'][:200]}"
            img_lines.append(line)
        sections.append("## Generated Images\n" + "\n".join(img_lines))

    # Existing memory
    if data["existing_memory"]:
        mem_lines = []
        for mem in data["existing_memory"]:
            mem_lines.append(f"- {mem['memory_key']}: {json.dumps(mem['memory_value'])}")
        sections.append("## Existing Memory\n" + "\n".join(mem_lines))

    full_prompt = (
        "Please analyze the following project data and organize it into "
        "structured memory entries:\n\n" + "\n\n".join(sections)
    )
    return full_prompt


def _parse_agent_output(text: str) -> list[dict[str, Any]]:
    """Parse the JSON array from Claude's response."""
    # Try to find a JSON array in the response
    text = text.strip()

    # Handle markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            return [result]
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse agent output as JSON: {text[:200]}")
        # Fallback: create a single memory entry with the raw text
        return [
            {
                "memory_key": "agent_raw_output",
                "memory_value": text[:2000],
            }
        ]

    return []


def _update_execution_status(
    execution_id: str,
    status: str,
    result: dict | None = None,
) -> None:
    """Update the status of an agent execution."""
    update_data: dict[str, Any] = {"status": status}

    if status == "completed" or status == "failed":
        update_data["completed_at"] = datetime.now(timezone.utc).isoformat()

    if result is not None:
        update_data["result"] = result

    supabase.table("agent_executions").update(update_data).eq(
        "id", execution_id
    ).execute()
