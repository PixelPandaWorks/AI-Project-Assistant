"""
Application configuration — loads environment variables via python-dotenv.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central settings object sourced from .env file."""

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Claude model to use
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # Gemini model for vision
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # DALL-E model
    DALLE_MODEL: str = "dall-e-3"

    def validate(self) -> list[str]:
        """Return a list of missing required keys."""
        missing = []
        if not self.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
        if not self.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not self.SUPABASE_URL:
            missing.append("SUPABASE_URL")
        if not self.SUPABASE_KEY:
            missing.append("SUPABASE_KEY")
        return missing


settings = Settings()
