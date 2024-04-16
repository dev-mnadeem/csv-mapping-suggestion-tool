"""Single source of truth for runtime configuration.

Everything tunable lives here so that no module has to reach for
``os.environ`` on its own. Values come from the process environment or a
``.env`` file sitting next to the backend package.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

KIB = 1024
MIB = 1024 * KIB


class Settings(BaseSettings):
    """Application settings, read once and cached."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "CSV Column Mapper"
    host: str = "0.0.0.0"
    port: int = 7241

    # Which MappingSuggester implementation the API uses. "local" needs no
    # network and no credentials, which is why it is the default.
    suggester_backend: Literal["local", "openai"] = "local"

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 30.0

    # Upload guards. A CSV is parsed in memory, so the cap is what keeps a
    # single request from deciding how much RAM the process uses.
    max_upload_bytes: int = 5 * MIB
    max_rows: int = 50_000
    max_columns: int = 512
    sniff_sample_bytes: int = 16 * KIB
    profile_sample_size: int = 25

    # A candidate below this score is reported as "no confident match"
    # instead of being forced onto a target column.
    min_confidence: float = 0.35
    max_alternatives: int = 3

    database_url: str = "sqlite:///./data/app.db"
    runs_page_size: int = 20
    runs_max_page_size: int = 100

    cors_allow_origins: list[str] = ["http://localhost:7242", "http://127.0.0.1:7242"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
