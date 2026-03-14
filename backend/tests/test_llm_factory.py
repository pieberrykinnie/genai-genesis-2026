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


def test_make_railtracks_llm_requires_groq_key() -> None:
    settings = Settings(
        groq_api_key="",
        groq_model="llama-3.3-70b-versatile",
        groq_api_base="https://api.groq.com/openai/v1",
        llm_backend="groq",
    )

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        make_railtracks_llm(settings=settings)


def test_make_railtracks_llm_rejects_unknown_backend() -> None:
    settings = Settings(
        groq_api_key="test-groq-key",
        llm_backend="local",
    )

    with pytest.raises(ValueError, match="Unsupported LLM backend"):
        make_railtracks_llm(settings=settings)
