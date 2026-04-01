"""
Gemini Vision service — image analysis using Google's Gemini model.
"""

from __future__ import annotations

import logging

import httpx
import google.generativeai as genai
from app.config import settings
from app.database import supabase

logger = logging.getLogger(__name__)

# Configure the Gemini SDK
logger.info("🔑 [GEMINI] Configuring Gemini SDK with GEMINI_API_KEY")
genai.configure(api_key=settings.GEMINI_API_KEY)
logger.info("✅ [GEMINI] Gemini SDK ready")


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
    logger.info(f"\n{'─'*40}")
    logger.info(f"👁️ [GEMINI VISION] Starting image analysis")
    logger.info(f"🆔 [GEMINI VISION] Image ID: {image_id}")

    # 1. Fetch image record
    logger.info(f"📥 [GEMINI VISION] Fetching image record from Supabase...")
    result = (
        supabase.table("images")
        .select("*")
        .eq("id", image_id)
        .execute()
    )

    if not result.data:
        logger.error(f"❌ [GEMINI VISION] No image found with ID {image_id}")
        return f"Error: No image found with ID {image_id}"

    image_record = result.data[0]
    logger.info(f"✅ [GEMINI VISION] Image record found")

    # If already analyzed, return cached result
    if image_record.get("analysis"):
        logger.info(f"📦 [GEMINI VISION] Returning cached analysis (already analyzed)")
        return image_record["analysis"]

    image_url = image_record["url"]
    logger.info(f"🔗 [GEMINI VISION] Image URL: {image_url[:80]}...")

    # 2. Download the image
    logger.info(f"⬇️ [GEMINI VISION] Downloading image bytes...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(image_url, timeout=30.0)
            resp.raise_for_status()
            image_bytes = resp.content
            content_type = resp.headers.get("content-type", "image/png")
        logger.info(f"✅ [GEMINI VISION] Downloaded {len(image_bytes)} bytes | Content-Type: {content_type}")
    except Exception as e:
        logger.error(f"❌ [GEMINI VISION] Failed to download image: {str(e)}")
        return f"Error downloading image: {str(e)}"

    # 3. Send to Gemini Vision
    logger.info(f"🤖 [GEMINI VISION] Model: {settings.GEMINI_MODEL}")
    logger.info(f"🔑 [GEMINI VISION] Using GEMINI_API_KEY → Google Gemini API")
    logger.info(f"⏳ [GEMINI VISION] Calling Gemini Vision API...")
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
        logger.info(f"✅ [GEMINI VISION] Analysis complete ({len(analysis_text)} chars)")
    except Exception as e:
        logger.error(f"❌ [GEMINI VISION] Gemini API error: {str(e)}")
        return f"Error analyzing image with Gemini: {str(e)}"

    # 4. Cache analysis in the database
    logger.info(f"💾 [GEMINI VISION] Caching analysis to Supabase...")
    supabase.table("images").update({"analysis": analysis_text}).eq(
        "id", image_id
    ).execute()
    logger.info(f"✅ [GEMINI VISION] Analysis cached successfully")

    # 5. Return
    return analysis_text
