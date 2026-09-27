"""Application settings, loaded from environment variables / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve src/.env by this file's own location (app/core/config.py -> app -> backend -> src),
# not by the process's current working directory — that stays correct whether Settings()
# is instantiated from uvicorn, `python -m app.seed`, a test runner, or anywhere else.
_ENV_FILE = Path(__file__).resolve().parent.parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_port: int = 8010
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"

    # --- Database ---
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5544/cctns_intelligence"

    # --- IBM Bob inference API ---
    bob_api_key: str = ""
    bob_api_base_url: str = "https://api.us-east.bob.ibm.com"
    bob_model: str = ""
    bob_extraction_enabled: bool = True
    bob_request_timeout_seconds: int = 25

    # --- Embeddings ---
    mo_embedding_model: str = "all-MiniLM-L6-v2"
    mo_similarity_threshold: float = 0.80

    # --- Entity resolution ---
    entity_fuzzy_threshold: int = 82

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def bob_configured(self) -> bool:
        return bool(self.bob_api_key) and self.bob_extraction_enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()
