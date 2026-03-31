"""
FastAPI Application — AI Project Assistant

Entry point that configures the app, mounts routers, and validates settings.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.config import settings
from app.routers import projects, chat, images, agents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # ── Startup ──
    missing = settings.validate()
    if missing:
        logger.warning(
            f"Missing environment variables: {', '.join(missing)}. "
            "Some features may not work. See .env.example for required keys."
        )
    else:
        logger.info("All environment variables loaded successfully.")

    logger.info("AI Project Assistant is ready.")
    yield
    # ── Shutdown ──
    logger.info("Shutting down.")


# Create the FastAPI app
app = FastAPI(
    title="AI Project Assistant",
    description=(
        "An AI-powered project assistant where users can chat with Claude, "
        "generate and analyze images, and organize project knowledge using "
        "AI agents. Built with FastAPI, Claude (Anthropic), Gemini (Google), "
        "DALL-E (OpenAI), and Supabase."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount routers
app.include_router(projects.router)
app.include_router(chat.router)
app.include_router(images.router)
app.include_router(agents.router)


@app.get("/", tags=["ui"])
async def root():
    """Serve the SPA interface."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "UI not built yet. Create app/static/index.html"}


@app.get("/health", tags=["health"])
async def health_check():
    """Detailed health check."""
    missing = settings.validate()
    return {
        "status": "healthy" if not missing else "degraded",
        "missing_keys": missing,
        "services": {
            "claude": bool(settings.ANTHROPIC_API_KEY),
            "gemini": bool(settings.GEMINI_API_KEY),
            "dalle": bool(settings.OPENAI_API_KEY),
            "supabase": bool(settings.SUPABASE_URL and settings.SUPABASE_KEY),
        },
    }
