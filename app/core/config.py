"""
app/core/config.py
──────────────────
Centralised settings loaded from .env via pydantic-settings.
All environment variables are validated and typed here.
"""

import os
from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import dotenv_values


class Settings(BaseSettings):
    """Application settings — sourced from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Groq ──────────────────────────────────────
    groq_api_key: str = Field(..., description="Groq API secret key")
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model identifier",
    )

    # ── App ───────────────────────────────────────
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    app_debug: bool = Field(default=False)
    app_title: str = Field(default="VideoMind")
    app_version: str = Field(default="1.0.0")

    # ── RAG pipeline ──────────────────────────────
    chunk_size: int = Field(default=400, ge=100, le=2000)
    chunk_overlap: int = Field(default=60, ge=0, le=200)
    top_k_chunks: int = Field(default=5, ge=1, le=20)
    transcript_auto_translate_to_en: bool = Field(default=True)
    transcript_whisper_fallback_enabled: bool = Field(default=True)
    transcript_whisper_model: str = Field(default="whisper-large-v3-turbo")

    # ── CORS ──────────────────────────────────────
    cors_origins: str = Field(default="*")

    @field_validator("groq_api_key")
    @classmethod
    def validate_groq_key(cls, v: str) -> str:
        if not v or v == "your_groq_api_key_here":
            raise ValueError(
                "GROQ_API_KEY is not set. "
                "Copy .env.example → .env and add your key from https://console.groq.com"
            )
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance (singleton)."""
    # Enforce `.env` values over process/user/machine environment variables.
    for key, value in dotenv_values(".env").items():
        if value is not None:
            os.environ[key] = value
    return Settings()