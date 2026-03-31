"""
DALL-E image generation service.
"""

from __future__ import annotations

from openai import OpenAI
from app.config import settings
from app.database import supabase


# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_image(project_id: str, prompt: str) -> dict:
    """
    Generate an image using DALL-E 3 and save the result to the database.

    Returns the saved image record including id, url, and prompt.
    """
    # Call DALL-E API
    response = openai_client.images.generate(
        model=settings.DALLE_MODEL,
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url

    # Save to database
    result = (
        supabase.table("images")
        .insert(
            {
                "project_id": project_id,
                "prompt": prompt,
                "url": image_url,
            }
        )
        .execute()
    )

    return result.data[0] if result.data else {"prompt": prompt, "url": image_url}
