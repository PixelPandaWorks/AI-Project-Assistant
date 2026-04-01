"""
Claude service — handles the complete chat + tool loop.

This is the core orchestrator: it sends messages to Claude with tool
definitions, processes any tool_use responses by calling the appropriate
service, feeds tool results back to Claude, and repeats until Claude
produces a final text response.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from app.config import settings
from app.database import supabase
from app.tools.tool_definitions import TOOLS
from app.services import memory_service, dalle_service, gemini_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Anthropic client
logger.info("🔑 [ANTHROPIC] Initializing Claude client with ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
logger.info("✅ [ANTHROPIC] Claude client ready")

SYSTEM_PROMPT = """You are an intelligent AI project assistant. You help users plan, build, and manage their projects.

Key behaviors:
1. ALWAYS call get_project_memory at the start of each conversation to load existing context.
2. When the user shares important project details, decisions, or preferences, save them using save_project_memory.
3. When asked to generate images, use the generate_image tool with a detailed, descriptive prompt.
4. When asked to analyze or describe an image, use the analyze_image tool.
5. Use get_project_brief to understand the project context when needed.
6. Be proactive — if you notice relevant context in memory, reference it naturally.
7. Be helpful, specific, and action-oriented in your responses.

You are scoped to a specific project. All your tools operate within that project's context."""


async def chat(project_id: str, user_message: str) -> dict[str, Any]:
    """
    Process a chat message through Claude with the full tool loop.

    Returns:
        {
            "response": str,           # Claude's final text response
            "tool_calls": [...],        # List of tool invocations made
            "images_generated": [...]   # Any images that were generated
        }
    """
    # 1. Load conversation history from DB
    history_result = (
        supabase.table("conversations")
        .select("role, content")
        .eq("project_id", project_id)
        .order("created_at")
        .limit(50)  # Keep context window manageable
        .execute()
    )
    history = history_result.data or []

    # 2. Build messages array
    messages = []
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add the new user message
    messages.append({"role": "user", "content": user_message})

    # 3. Save user message to DB
    supabase.table("conversations").insert(
        {
            "project_id": project_id,
            "role": "user",
            "content": user_message,
        }
    ).execute()

    # 4. Run the tool loop
    tool_calls_log: list[dict[str, Any]] = []
    images_generated: list[dict[str, Any]] = []
    max_iterations = 10  # Safety limit

    for iteration in range(max_iterations):
        logger.info(f"\n{'='*60}")
        logger.info(f"🔄 [CLAUDE] Iteration {iteration + 1}/{max_iterations}")
        logger.info(f"📨 [CLAUDE] Sending {len(messages)} messages to Claude")
        logger.info(f"🤖 [CLAUDE] Model: {settings.CLAUDE_MODEL}")
        logger.info(f"🔑 [CLAUDE] Using ANTHROPIC_API_KEY → Anthropic API")

        # Call Claude
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        logger.info(f"📩 [CLAUDE] Response received | Stop reason: {response.stop_reason}")

        # Check stop reason
        if response.stop_reason == "end_turn":
            # Claude is done — extract text
            final_text = _extract_text(response)
            logger.info(f"✅ [CLAUDE] Final response ready ({len(final_text)} chars)")
            break

        elif response.stop_reason == "tool_use":
            # Claude wants to use a tool
            # First, add assistant's response to messages
            messages.append({"role": "assistant", "content": response.content})

            # Process each tool use block
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_id = block.id

                    logger.info(f"\n{'─'*40}")
                    logger.info(f"🔧 [TOOL CALL] Claude wants to use: '{tool_name}'")
                    logger.info(f"📥 [TOOL INPUT] {json.dumps(tool_input, indent=2)}")
                    logger.info(f"🆔 [TOOL ID] {tool_id}")

                    # Execute the tool
                    logger.info(f"⏳ [TOOL EXEC] Routing '{tool_name}' to handler...")
                    result = await _execute_tool(
                        project_id, tool_name, tool_input
                    )
                    logger.info(f"✅ [TOOL RESULT] '{tool_name}' completed")
                    logger.info(f"📤 [TOOL OUTPUT] {str(result)[:300]}")

                    # Track the call
                    tool_call_record = {
                        "tool": tool_name,
                        "input": tool_input,
                        "result_preview": str(result)[:200],
                    }
                    tool_calls_log.append(tool_call_record)

                    # If it was an image generation, track it
                    if tool_name == "generate_image" and isinstance(result, dict):
                        logger.info(f"🖼️ [IMAGE] Image generated and tracked")
                        images_generated.append(result)

                    # Build the tool result message (truncate to avoid context overflow)
                    result_content = json.dumps(result) if not isinstance(result, str) else result
                    if len(result_content) > 5000:
                        logger.warning(f"⚠️ [TOOL] Result too large ({len(result_content)} chars), truncating to 5000")
                        result_content = result_content[:5000] + "... [truncated]"

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result_content,
                        }
                    )

            # Add tool results to messages
            logger.info(f"📨 [TOOL] Feeding {len(tool_results)} tool result(s) back to Claude")
            messages.append({"role": "user", "content": tool_results})

        else:
            # Unknown stop reason — just extract text and break
            final_text = _extract_text(response)
            break
    else:
        # Max iterations reached
        final_text = _extract_text(response)

    # 5. Save assistant response to DB
    logger.info(f"\n{'='*60}")
    logger.info(f"💾 [DB] Saving assistant response to conversations table")
    logger.info(f"📊 [SUMMARY] Tool calls made: {len(tool_calls_log)} | Images generated: {len(images_generated)}")
    supabase.table("conversations").insert(
        {
            "project_id": project_id,
            "role": "assistant",
            "content": final_text,
            "tool_calls": tool_calls_log if tool_calls_log else None,
        }
    ).execute()
    logger.info(f"✅ [DB] Response saved successfully")

    return {
        "response": final_text,
        "tool_calls": tool_calls_log,
        "images_generated": images_generated,
    }


async def _execute_tool(
    project_id: str, tool_name: str, tool_input: dict
) -> Any:
    """Route a tool call to the appropriate service function."""

    if tool_name == "generate_image":
        logger.info(f"🖼️ [ROUTE] generate_image → dalle_service (OpenAI API)")
        logger.info(f"🔑 [ROUTE] Will use OPENAI_API_KEY")
        return await dalle_service.generate_image(
            project_id=project_id,
            prompt=tool_input["prompt"],
        )

    elif tool_name == "analyze_image":
        logger.info(f"👁️ [ROUTE] analyze_image → gemini_service (Gemini API)")
        logger.info(f"🔑 [ROUTE] Will use GEMINI_API_KEY")
        analysis = await gemini_service.analyze_image(
            image_id=tool_input["image_id"]
        )
        return analysis

    elif tool_name == "get_project_memory":
        logger.info(f"🧠 [ROUTE] get_project_memory → memory_service (Supabase)")
        logger.info(f"🔑 [ROUTE] Will use SUPABASE_KEY")
        memories = await memory_service.get_project_memory(project_id)
        logger.info(f"📦 [MEMORY] Retrieved {len(memories)} memory entries")
        if not memories:
            return "No memory entries found for this project yet."
        return memories

    elif tool_name == "save_project_memory":
        logger.info(f"💾 [ROUTE] save_project_memory → memory_service (Supabase)")
        logger.info(f"🔑 [ROUTE] Will use SUPABASE_KEY")
        logger.info(f"📝 [MEMORY] Saving key: '{tool_input['memory_key']}'")
        result = await memory_service.save_memory(
            project_id=project_id,
            memory_key=tool_input["memory_key"],
            memory_value=tool_input["memory_value"],
            source="assistant",
        )
        return f"Memory saved: {tool_input['memory_key']}"

    elif tool_name == "get_project_brief":
        logger.info(f"📋 [ROUTE] get_project_brief → Supabase direct query")
        logger.info(f"🔑 [ROUTE] Will use SUPABASE_KEY")
        brief_result = (
            supabase.table("project_briefs")
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        if brief_result.data:
            logger.info(f"✅ [BRIEF] Found brief: {brief_result.data[0].get('title', 'N/A')}")
            return brief_result.data[0]
        logger.info(f"⚠️ [BRIEF] No brief found for project {project_id}")
        return "No brief found for this project."

    elif tool_name == "get_project_images":
        logger.info(f"🖼️ [ROUTE] get_project_images → Supabase direct query")
        logger.info(f"🔑 [ROUTE] Will use SUPABASE_KEY")
        images_result = (
            supabase.table("images")
            .select("*")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )
        if images_result.data:
            logger.info(f"✅ [IMAGES] Found {len(images_result.data)} images")
            return images_result.data
        logger.info(f"⚠️ [IMAGES] No images found for project {project_id}")
        return "No images found for this project."

    else:
        logger.warning(f"❌ [ROUTE] Unknown tool: {tool_name}")
        return f"Unknown tool: {tool_name}"


def _extract_text(response) -> str:
    """Extract all text blocks from a Claude response."""
    texts = []
    for block in response.content:
        if hasattr(block, "text"):
            texts.append(block.text)
    return "\n".join(texts) if texts else "I processed your request."
