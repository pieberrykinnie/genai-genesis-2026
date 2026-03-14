from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DataSite Impact Analyzer API"
    app_env: str = "dev"

    backend_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    electricity_maps_api_key: str | None = None
    maptiler_api_key: str | None = None
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_api_base: str = "https://api.groq.com/openai/v1"
    llm_backend: str = "groq"
    llm_temperature: float | None = None

    data_dir: Path = BASE_DIR / "data"
    models_dir: Path = BASE_DIR / "models"
    statcan_cache_dir: Path = BASE_DIR / "data" / "statcan_cache"
    model_path: Path = BASE_DIR / "models" / "grid_strain_model.pkl"

    request_timeout_seconds: float = 12.0
    cache_ttl_seconds: int = 1800


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    settings.statcan_cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
