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
    nominatim_user_agent: str = "genai-genesis-2026/1.0 (local-dev)"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_api_base: str = "https://api.groq.com/openai/v1"
    llm_backend: str = "groq"
    llm_temperature: float | None = None
    llm_provider: str = "groq"
    bitnet_api_key: str = "bitnet-local"
    bitnet_api_base: str = "http://127.0.0.1:8080/v1"
    bitnet_model: str = "HF1BitLLM/Llama3-8B-1.58-100B-tokens"

    data_dir: Path = BASE_DIR / "data"
    models_dir: Path = BASE_DIR / "models"
    statcan_cache_dir: Path = BASE_DIR / "data" / "statcan_cache"
    model_path: Path = BASE_DIR / "models" / "grid_strain_model.pkl"

    request_timeout_seconds: float = 12.0
    cache_ttl_seconds: int = 1800
    strict_data_mode: bool = True
    memo_job_queue_maxsize: int = 32
    memo_job_worker_count: int = 1
    memo_job_timeout_seconds: float = 180.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    settings.statcan_cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
