from __future__ import annotations

import pytest

from config import Settings
from orchestrator.llm_factory import make_railtracks_llm


def test_make_railtracks_llm_builds_groq_model() -> None:
    settings = Settings(
        groq_api_key="test-groq-key",
        groq_model="llama-3.3-70b-versatile",
        groq_api_base="https://api.groq.com/openai/v1",
        llm_backend="groq",
    )

    llm = make_railtracks_llm(settings=settings)

    assert llm.model_name() == "openai/llama-3.3-70b-versatile"


def test_make_railtracks_llm_builds_bitnet_model() -> None:
    settings = Settings(
        bitnet_api_base="http://127.0.0.1:8080/v1",
        bitnet_model="HF1BitLLM/Llama3-8B-1.58-100B-tokens",
        llm_backend="bitnet",
    )

    llm = make_railtracks_llm(settings=settings)

    assert llm.model_name() == "openai/HF1BitLLM/Llama3-8B-1.58-100B-tokens"


def test_make_railtracks_llm_requires_groq_key() -> None:
    settings = Settings(
        groq_api_key="",
        groq_model="llama-3.3-70b-versatile",
        groq_api_base="https://api.groq.com/openai/v1",
        llm_backend="groq",
    )

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        make_railtracks_llm(settings=settings)


def test_make_railtracks_llm_requires_bitnet_api_base() -> None:
    settings = Settings(
        bitnet_api_base="",
        bitnet_model="HF1BitLLM/Llama3-8B-1.58-100B-tokens",
        llm_backend="bitnet",
    )

    with pytest.raises(ValueError, match="BITNET_API_BASE"):
        make_railtracks_llm(settings=settings)


def test_make_railtracks_llm_rejects_unknown_backend() -> None:
    settings = Settings(
        groq_api_key="test-groq-key",
        llm_backend="local",
    )

    with pytest.raises(ValueError, match="Unsupported LLM backend"):
        make_railtracks_llm(settings=settings)
