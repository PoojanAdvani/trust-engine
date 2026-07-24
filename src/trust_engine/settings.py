"""Environment-driven settings for the Trust Engine service.

Values are read from ``TRUST_ENGINE_*`` environment variables (or a local
``.env`` file). For example, ``TRUST_ENGINE_DB_PATH`` populates ``db_path``.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration sourced from the environment."""

    model_config = SettingsConfigDict(
        env_prefix="TRUST_ENGINE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    config_path: str = "config.yaml"
    db_path: str = "trust_engine.db"
    # When None, API-key authentication is disabled (open access).
    api_key: str | None = None

    # Vision pipeline. "stub" (default) needs no extra dependencies; "cloud" and
    # "onnx" require the `vision` extra and the relevant fields below.
    vision_provider: str = "stub"
    vision_api_url: str | None = None
    vision_api_key: str | None = None
    vision_model_path: str | None = None
    vision_max_bytes: int = 8_000_000  # reject uploads larger than ~8 MB
