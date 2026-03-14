from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DataSite Impact Analyzer API"
    app_env: str = "dev"

    backend_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    electricity_maps_api_key: str | None = None
    maptiler_api_key: str | None = None
    groq_api_key: str | None = None

    data_dir: Path = Path("./data")
    models_dir: Path = Path("./models")
    statcan_cache_dir: Path = Path("./data/statcan_cache")
    model_path: Path = Path("./models/grid_strain_model.pkl")

    request_timeout_seconds: float = 12.0
    cache_ttl_seconds: int = 1800


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    settings.statcan_cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
