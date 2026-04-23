"""
Application settings loaded from environment / .env (plug-and-play).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _read_text_file(path: str) -> str:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Configured file not found: {p}")
    return p.read_text(encoding="utf-8").strip()


class Settings(BaseSettings):
    """Tunable values from the environment; defaults match prior hard-coded behavior."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = Field(..., description="Google AI Studio / Gemini API key")
    gemini_model: str = Field(default="gemini-2.5-flash")
    gemini_temperature: float = Field(default=0.6)
    gemini_max_output_tokens: int = Field(default=600)

    # --- Logging / observability ---
    token_log_enabled: bool = Field(
        default=True,
        description="If true, write per-request token usage logs",
    )
    token_log_path: str = Field(
        default="sakhi_tokens.jsonl",
        description="Path to JSONL file where token usage logs are appended",
    )

    clinic_context_path: str | None = Field(
        default=None,
        description="If set, clinic knowledge base is read from this UTF-8 file",
    )
    system_prompt_path: str | None = Field(
        default=None,
        description="If set, Sakhi system prompt is read from this UTF-8 file",
    )

    uvicorn_host: str = Field(default="0.0.0.0")
    uvicorn_port: int = Field(default=8000)
    uvicorn_reload: bool = Field(default=False)

    app_title: str = Field(default="Sakhi Clinic Assistant API")
    app_description: str = Field(
        default="AI-powered assistant for Shakti Women's Care Clinic",
    )
    app_version: str = Field(default="1.0.0")

    @field_validator("gemini_temperature", mode="before")
    @classmethod
    def coerce_temperature(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return 0.6
        return float(v)

    @field_validator("gemini_max_output_tokens", "uvicorn_port", mode="before")
    @classmethod
    def coerce_int(cls, v, info):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            if info.field_name == "uvicorn_port":
                return 8000
            if info.field_name == "gemini_max_output_tokens":
                return 600
            return v
        return int(v)

    @field_validator("uvicorn_reload", "token_log_enabled", mode="before")
    @classmethod
    def coerce_bool(cls, v):
        if isinstance(v, bool):
            return v
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return False
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    def load_clinic_context(self, default: str) -> str:
        if self.clinic_context_path:
            return _read_text_file(self.clinic_context_path)
        return default

    def load_system_prompt(self, default: str) -> str:
        if self.system_prompt_path:
            return _read_text_file(self.system_prompt_path)
        return default


@lru_cache
def get_settings() -> Settings:
    return Settings()
