import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Simple centralized settings container for runtime configuration."""

    supabase_url: str | None = None
    supabase_key: str | None = None
    groq_api_key: str | None = None
    google_api_key: str | None = None

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
