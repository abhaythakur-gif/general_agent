"""
app/config/settings.py
-----------------------
Application-wide settings loaded from environment variables.
Uses Pydantic BaseSettings so every field is configurable via .env or
actual env vars without any code changes.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""

    # ── External APIs ────────────────────────────────────────────────────────
    SERPAPI_KEY: str = ""
    WEATHER_API_KEY: str = ""

    # ── MongoDB ───────────────────────────────────────────────────────────────
    MONGODB_URL: str = "mongodb://localhost:27030"
    MONGODB_DB_NAME: str = "universal_agent_platform"

    # ── App ───────────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Legacy — kept for backward compat (not used by new code) ─────────────
    DATABASE_URL: str = "sqlite:///./agent_platform.db"


settings = Settings()
