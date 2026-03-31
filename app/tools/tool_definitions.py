"""
Tool definitions for Claude's function calling.

Each tool is specified in the Anthropic tool-use format.
These are passed to the Claude API so it can invoke them during chat.
"""

TOOLS = [
    {
        "name": "generate_image",
        "description": (
            "Generate an image using DALL-E based on a text prompt. "
            "Use this when the user asks you to create, generate, draw, or design an image. "
            "The generated image URL will be saved to the project automatically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A detailed description of the image to generate.",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "analyze_image",
        "description": (
            "Analyze a project image using Gemini Vision. "
            "Use this when the user asks you to look at, describe, or analyze a generated image. "
            "Pass the image ID to get a detailed visual analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "image_id": {
                    "type": "string",
                    "description": "The UUID of the image to analyze. You can get this from the image generation result or from project images.",
                },
            },
            "required": ["image_id"],
        },
    },
    {
        "name": "get_project_memory",
        "description": (
            "Retrieve all stored memory/knowledge for the current project. "
            "ALWAYS call this at the start of a conversation to check for existing context. "
            "Returns a list of key-value memory entries scoped to this project."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "save_project_memory",
        "description": (
            "Save a piece of knowledge/fact to the project's persistent memory. "
            "Use this when the user tells you something important about the project, "
            "makes a decision, or when you discover something worth remembering. "
            "Memory persists across conversations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "memory_key": {
                    "type": "string",
                    "description": "A short, descriptive key for this memory (e.g., 'preferred_color_scheme', 'database_choice', 'main_goal').",
                },
                "memory_value": {
                    "type": "string",
                    "description": "The actual content/fact to remember. Be detailed and specific.",
                },
            },
            "required": ["memory_key", "memory_value"],
        },
    },
    {
        "name": "get_project_brief",
        "description": (
            "Retrieve the current project's brief including title, description, goals, "
            "reference links, target audience, and tech stack. "
            "Use this to understand the project context when answering questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_project_images",
        "description": (
            "Retrieve all images that have been generated for this project. "
            "Returns a list of images with their IDs, prompts, URLs, and any analysis. "
            "Use this when the user asks about previously generated images."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
