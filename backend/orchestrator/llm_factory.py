from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

import railtracks as rt
from railtracks.llm.models.api_providers._openai_compatable_provider_wrapper import OpenAICompatibleProvider

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
    return _GroqCompatibleProvider(
        model_name=model_name,
        api_key=api_key,
        api_base=api_base,
        temperature=config.temperature,
    )


_JSON_SCHEMA_UNSUPPORTED_PATTERNS = (
    r"does not support response format\s*`?json_schema`?",
    r"invalid_request_error",
    r"response_format",
)


def _is_json_schema_unsupported_error(exc: Exception) -> bool:
    # Railtracks/LiteLLM frequently wrap provider errors, so inspect the full
    # exception chain and args to catch json_schema incompatibility reliably.
    seen: set[int] = set()
    stack: list[BaseException] = [exc]
    texts: list[str] = []

    while stack:
        cur = stack.pop()
        cur_id = id(cur)
        if cur_id in seen:
            continue
        seen.add(cur_id)

        texts.append(str(cur))
        for arg in getattr(cur, "args", ()):
            texts.append(str(arg))

        cause = getattr(cur, "__cause__", None)
        context = getattr(cur, "__context__", None)
        if isinstance(cause, BaseException):
            stack.append(cause)
        if isinstance(context, BaseException):
            stack.append(context)

    haystack = "\n".join(texts).lower()
    if "json_schema" not in haystack:
        return False
    return any(re.search(pat, haystack) for pat in _JSON_SCHEMA_UNSUPPORTED_PATTERNS)


class _GroqCompatibleProvider(OpenAICompatibleProvider):
    """OpenAI-compatible provider that falls back to json_object when json_schema fails.

    Some Groq models reject `response_format={"type":"json_schema"}` while still
    supporting json_object. Structured calls should degrade gracefully so schema
    validation can still run client-side via the base structured handler.
    """

    def _structured(self, messages: Any, schema: Any) -> Any:
        from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper

        try:
            return super()._structured(messages, schema)
        except Exception as exc:
            if not _is_json_schema_unsupported_error(exc):
                raise

        model_resp, elapsed = self._invoke(messages, response_format={"type": "json_object"})
        if isinstance(model_resp, CustomStreamWrapper):
            return self._stream_handler_base(model_resp, elapsed, schema)
        return self._structured_handle_base(
            model_resp, self.extract_message_info(model_resp, elapsed), schema
        )

    async def _astructured(self, messages: Any, schema: Any) -> Any:
        from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper

        try:
            return await super()._astructured(messages, schema)
        except Exception as exc:
            if not _is_json_schema_unsupported_error(exc):
                raise

        model_resp, elapsed = await self._ainvoke(messages, response_format={"type": "json_object"})
        if isinstance(model_resp, CustomStreamWrapper):
            return self._astream_handler_base(model_resp, elapsed, schema)
        return self._structured_handle_base(
            model_resp, self.extract_message_info(model_resp, elapsed), schema
        )


class _BitNetCompatibleProvider(OpenAICompatibleProvider):
    """OpenAICompatibleProvider that forces json_object mode for structured calls.

    Many local OpenAI-compatible servers (including BitNet) don't support
    json_schema response_format. This subclass overrides _structured and
    _astructured to request json_object instead, which is universally supported.
    The response content is plain JSON text, fully compatible with the base
    class's _structured_handle_base parser.
    """

    def _structured(self, messages: Any, schema: Any) -> Any:
        from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper

        model_resp, elapsed = self._invoke(messages, response_format={"type": "json_object"})
        if isinstance(model_resp, CustomStreamWrapper):
            return self._stream_handler_base(model_resp, elapsed, schema)
        return self._structured_handle_base(
            model_resp, self.extract_message_info(model_resp, elapsed), schema
        )

    async def _astructured(self, messages: Any, schema: Any) -> Any:
        from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper

        model_resp, elapsed = await self._ainvoke(messages, response_format={"type": "json_object"})
        if isinstance(model_resp, CustomStreamWrapper):
            return self._astream_handler_base(model_resp, elapsed, schema)
        return self._structured_handle_base(
            model_resp, self.extract_message_info(model_resp, elapsed), schema
        )


def _build_bitnet_llm(config: LLMFactoryConfig) -> Any:
    model_name = _require_non_empty(config.model_name, "BITNET_MODEL")
    api_base = _require_non_empty(config.api_base, "BITNET_API_BASE")
    api_key = (config.api_key or "bitnet-local").strip() or "bitnet-local"
    return _BitNetCompatibleProvider(
        model_name=model_name,
        api_key=api_key,
        api_base=api_base,
        temperature=config.temperature,
    )


def _to_factory_config(settings: Settings) -> LLMFactoryConfig:
    backend = settings.llm_backend.strip().lower()
    if backend == "bitnet":
        return LLMFactoryConfig(
            backend=backend,
            api_key=settings.bitnet_api_key,
            model_name=settings.bitnet_model,
            api_base=settings.bitnet_api_base,
            temperature=settings.llm_temperature,
        )

    return LLMFactoryConfig(
        backend=backend,
        api_key=settings.groq_api_key,
        model_name=settings.groq_model,
        api_base=settings.groq_api_base,
        temperature=settings.llm_temperature,
    )


_BUILDERS: dict[str, Callable[[LLMFactoryConfig], Any]] = {
    "bitnet": _build_bitnet_llm,
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
