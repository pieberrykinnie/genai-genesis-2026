from __future__ import annotations

import pytest

from config import Settings
from llm import providers


@pytest.mark.asyncio
async def test_check_bitnet_health_cached_uses_ttl_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    providers.clear_bitnet_health_cache()

    calls = {"count": 0}

    async def fake_check(_settings=None):
        calls["count"] += 1
        return {"reachable": True, "models": ["mock-model"], "error": None}

    settings = Settings(
        bitnet_api_base="http://127.0.0.1:8080/v1",
        bitnet_api_key="bitnet-local",
        bitnet_health_cache_ttl_seconds=60,
    )

    monkeypatch.setattr(providers, "check_bitnet_health", fake_check)

    first = await providers.check_bitnet_health_cached(settings)
    second = await providers.check_bitnet_health_cached(settings)

    assert first["reachable"] is True
    assert second["reachable"] is True
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_check_bitnet_health_cached_force_refresh_bypasses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    providers.clear_bitnet_health_cache()

    calls = {"count": 0}

    async def fake_check(_settings=None):
        calls["count"] += 1
        return {"reachable": True, "models": ["mock-model"], "error": None}

    settings = Settings(
        bitnet_api_base="http://127.0.0.1:8080/v1",
        bitnet_api_key="bitnet-local",
        bitnet_health_cache_ttl_seconds=60,
    )

    monkeypatch.setattr(providers, "check_bitnet_health", fake_check)

    await providers.check_bitnet_health_cached(settings)
    await providers.check_bitnet_health_cached(settings, force_refresh=True)

    assert calls["count"] == 2
