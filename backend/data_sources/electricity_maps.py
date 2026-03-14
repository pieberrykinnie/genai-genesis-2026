from __future__ import annotations

from datetime import datetime, timezone

import httpx

from config import get_settings
from constants import FALLBACK_CARBON_INTENSITY, PROVINCE_TO_ZONE
from utils.cache import TTLCache

_CACHE: TTLCache[tuple[float, str]] = TTLCache(ttl_seconds=get_settings().cache_ttl_seconds)


async def get_carbon_intensity_g_per_kwh(province: str) -> tuple[float, dict[str, str]]:
    cache_key = f"carbon:{province}"
    cached = _CACHE.get(cache_key)
    if cached is not None:
        value, freshness = cached
        return value, {"electricity_maps": freshness}

    settings = get_settings()
    zone = PROVINCE_TO_ZONE.get(province)
    if not zone or not settings.electricity_maps_api_key:
        fallback = FALLBACK_CARBON_INTENSITY.get(province, 250.0)
        freshness = "fallback_static_2024"
        _CACHE.set(cache_key, (fallback, freshness))
        return fallback, {"electricity_maps": freshness}

    url = "https://api-access.electricitymaps.com/free-tier/carbon-intensity/latest"
    headers = {"auth-token": settings.electricity_maps_api_key}

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            resp = await client.get(url, headers=headers, params={"zone": zone})
            resp.raise_for_status()
            payload = resp.json()
        value = float(payload.get("carbonIntensity", FALLBACK_CARBON_INTENSITY.get(province, 250.0)))
        freshness = payload.get("datetime") or datetime.now(timezone.utc).isoformat()
        _CACHE.set(cache_key, (value, freshness))
        return value, {"electricity_maps": freshness}
    except Exception:
        fallback = FALLBACK_CARBON_INTENSITY.get(province, 250.0)
        freshness = "fallback_static_2024"
        _CACHE.set(cache_key, (fallback, freshness))
        return fallback, {"electricity_maps": freshness}
