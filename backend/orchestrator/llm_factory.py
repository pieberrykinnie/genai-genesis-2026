from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import railtracks as rt

from config import Settings, get_settings


@dataclass(frozen=True)
class LLMFactoryConfig:
    backend: str
    api_key: str | None
    model_name: str
    api_base: str
    temperature: float | None


def _require_non_empty(value: str | None, env_name: str) -> str:
    if value is None or not value.strip():
        raise ValueError(
            f"Missing required configuration: {env_name}. "
            f"Set {env_name} in your environment or .env file."
        )
    return value.strip()


def _normalize_model_name(model_name: str) -> str:
    # Support accidental "primary#fallback" config values by taking the right-most model identifier.
    if "#" in model_name:
        return model_name.split("#")[-1].strip()
    return model_name


def _build_groq_llm(config: LLMFactoryConfig) -> Any:
    api_key = _require_non_empty(config.api_key, "GROQ_API_KEY")
    model_name = _normalize_model_name(_require_non_empty(config.model_name, "GROQ_MODEL"))
    api_base = _require_non_empty(config.api_base, "GROQ_API_BASE")
    return rt.llm.OpenAICompatibleProvider(
        model_name=model_name,
        api_key=api_key,
        api_base=api_base,
        temperature=config.temperature,
    )


def _to_factory_config(settings: Settings) -> LLMFactoryConfig:
    return LLMFactoryConfig(
        backend=settings.llm_backend,
        api_key=settings.groq_api_key,
        model_name=settings.groq_model,
        api_base=settings.groq_api_base,
        temperature=settings.llm_temperature,
    )


_BUILDERS: dict[str, Callable[[LLMFactoryConfig], Any]] = {
    "groq": _build_groq_llm,
}


def make_railtracks_llm(settings: Settings | None = None) -> Any:
    current_settings = settings or get_settings()
    config = _to_factory_config(current_settings)

    builder = _BUILDERS.get(config.backend)
    if builder is None:
        supported = ", ".join(sorted(_BUILDERS.keys()))
        raise ValueError(
            f"Unsupported LLM backend '{config.backend}'. "
            f"Supported backends: {supported}."
        )
    return builder(config)
