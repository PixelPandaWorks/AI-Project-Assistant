"""
Gemini Vision service — image analysis using Google's Gemini model.
"""

from __future__ import annotations

import httpx
import google.generativeai as genai
from app.config import settings
from app.database import supabase

# Configure the Gemini SDK
genai.configure(api_key=settings.GEMINI_API_KEY)


async def analyze_image(image_id: str) -> str:
    """
    Analyze an image using Gemini Vision.

    Steps:
    1. Fetch the image record from the database.
    2. Download the image bytes from the URL.
    3. Send to Gemini for visual analysis.
    4. Cache the analysis result back into the database.
    5. Return the analysis text.
    """
    # 1. Fetch image record
    result = (
        supabase.table("images")
        .select("*")
        .eq("id", image_id)
        .execute()
    )

    if not result.data:
        return f"Error: No image found with ID {image_id}"

    image_record = result.data[0]

    # If already analyzed, return cached result
    if image_record.get("analysis"):
        return image_record["analysis"]

    image_url = image_record["url"]

    # 2. Download the image
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(image_url, timeout=30.0)
            resp.raise_for_status()
            image_bytes = resp.content
            content_type = resp.headers.get("content-type", "image/png")
    except Exception as e:
        return f"Error downloading image: {str(e)}"

    # 3. Send to Gemini Vision
    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL)

        response = model.generate_content(
            [
                {
                    "mime_type": content_type,
                    "data": image_bytes,
                },
                (
                    "Provide a detailed analysis of this image. Describe what you see, "
                    "the composition, colors, style, and any notable elements. "
                    "Also suggest how this image might be relevant to a project context."
                ),
            ]
        )

        analysis_text = response.text
    except Exception as e:
        return f"Error analyzing image with Gemini: {str(e)}"

    # 4. Cache analysis in the database
    supabase.table("images").update({"analysis": analysis_text}).eq(
        "id", image_id
    ).execute()

    # 5. Return
    return analysis_text
