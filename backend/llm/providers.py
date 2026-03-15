from __future__ import annotations

import time
from typing import Any

import httpx

from config import get_settings


_BITNET_HEALTH_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _bitnet_cache_key(base: str, api_key: str) -> str:
    return f"{base}|{api_key}"


async def check_bitnet_health(settings=None) -> dict[str, Any]:
    local_settings = settings or get_settings()
    base = local_settings.bitnet_api_base.rstrip("/")
    if not base:
        return {"reachable": False, "models": [], "error": "bitnet_api_base_missing"}

    headers = {"Content-Type": "application/json"}
    if (local_settings.bitnet_api_key or "").strip():
        headers["Authorization"] = f"Bearer {local_settings.bitnet_api_key}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{base}/models", headers=headers)
            res.raise_for_status()
            body = res.json()

        model_ids: list[str] = []
        for item in body.get("data", []):
            model_id = item.get("id")
            if isinstance(model_id, str) and model_id.strip():
                model_ids.append(model_id)

        return {"reachable": True, "models": model_ids, "error": None}
    except Exception as exc:
        return {"reachable": False, "models": [], "error": str(exc)}


async def check_bitnet_health_cached(
    settings=None,
    *,
    ttl_seconds: int | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    local_settings = settings or get_settings()
    base = local_settings.bitnet_api_base.rstrip("/")
    api_key = (local_settings.bitnet_api_key or "").strip()
    ttl = max(0, int(ttl_seconds if ttl_seconds is not None else local_settings.bitnet_health_cache_ttl_seconds))

    cache_key = _bitnet_cache_key(base, api_key)
    now = time.monotonic()
    if not force_refresh and ttl > 0:
        cached = _BITNET_HEALTH_CACHE.get(cache_key)
        if cached is not None:
            ts, payload = cached
            if (now - ts) <= ttl:
                return payload

    payload = await check_bitnet_health(local_settings)
    _BITNET_HEALTH_CACHE[cache_key] = (now, payload)
    return payload


def clear_bitnet_health_cache() -> None:
    _BITNET_HEALTH_CACHE.clear()
