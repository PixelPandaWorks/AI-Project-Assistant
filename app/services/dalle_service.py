"""
Image generation service using OpenAI gpt-image-1.

gpt-image-1 always returns base64 data (no URL option).
We save the image locally and serve it via FastAPI static files.
"""

from __future__ import annotations

import base64
import logging
import os
import uuid

from openai import OpenAI
from app.config import settings
from app.database import supabase

logger = logging.getLogger(__name__)

# Directory to save generated images
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger.info(f"📁 [OPENAI] Upload directory: {UPLOAD_DIR}")

# Initialize OpenAI client
logger.info("🔑 [OPENAI] Initializing OpenAI client with OPENAI_API_KEY")
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
logger.info("✅ [OPENAI] OpenAI client ready")


async def generate_image(project_id: str, prompt: str) -> dict:
    """
    Generate an image using OpenAI gpt-image-1 and save the result.

    Steps:
    1. Call OpenAI API (returns base64)
    2. Save image file locally in static/uploads/
    3. Save record to 'images' table with the local URL

    Returns the saved image record including id, url, and prompt.
    """
    logger.info(f"\n{'─'*40}")
    logger.info(f"🎨 [OPENAI IMAGE] Starting image generation")
    logger.info(f"🤖 [OPENAI IMAGE] Model: {settings.DALLE_MODEL}")
    logger.info(f"📝 [OPENAI IMAGE] Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"📝 [OPENAI IMAGE] Prompt: {prompt}")
    logger.info(f"🔑 [OPENAI IMAGE] Using OPENAI_API_KEY → OpenAI Images API")
    logger.info(f"⏳ [OPENAI IMAGE] Calling OpenAI API...")

    # Call OpenAI Images API (gpt-image-1 always returns base64)
    response = openai_client.images.generate(
        model=settings.DALLE_MODEL,
        prompt=prompt,
        size="1024x1024",
        n=1,
    )

    # gpt-image-1 returns base64 data
    image_base64 = response.data[0].b64_json
    logger.info(f"✅ [OPENAI IMAGE] Image generated successfully (base64, {len(image_base64)} chars)")

    # Save image locally
    file_name = f"{uuid.uuid4().hex}.png"
    file_path = os.path.join(UPLOAD_DIR, file_name)

    logger.info(f"💾 [OPENAI IMAGE] Saving image to {file_path}")
    image_bytes = base64.b64decode(image_base64)
    with open(file_path, "wb") as f:
        f.write(image_bytes)
    logger.info(f"✅ [OPENAI IMAGE] Image saved locally ({len(image_bytes)} bytes)")

    # URL served by FastAPI static files
    image_url = f"/static/uploads/{file_name}"
    logger.info(f"🔗 [OPENAI IMAGE] Serving URL: {image_url}")

    # Save to database
    logger.info(f"💾 [OPENAI IMAGE] Saving record to Supabase 'images' table...")
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
    logger.info(f"✅ [OPENAI IMAGE] Saved to database")

    return result.data[0] if result.data else {"prompt": prompt, "url": image_url}
