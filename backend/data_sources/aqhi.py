from __future__ import annotations

from datetime import datetime, timezone

import httpx

from config import get_settings

AQHI_DEFAULT_BY_PROVINCE: dict[str, str] = {
    "ON": "3-Moderate",
    "AB": "3-Moderate",
    "BC": "2-Low",
    "QC": "2-Low",
    "MB": "2-Low",
    "SK": "3-Moderate",
    "NB": "2-Low",
    "NS": "2-Low",
    "NL": "2-Low",
    "PE": "2-Low",
}


async def get_aqhi_baseline(province: str) -> tuple[str, dict[str, str]]:
    settings = get_settings()
    url = "https://dd.weather.gc.ca/air_quality/aqhi/observation/realtime/json"
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
        for item in payload:
            if str(item.get("province_code", "")).upper() == province:
                value = item.get("aqhi") or AQHI_DEFAULT_BY_PROVINCE.get(province, "3-Moderate")
                return str(value), {"aqhi": item.get("forecast_datetime", datetime.now(timezone.utc).isoformat())}
    except Exception:
        pass

    return AQHI_DEFAULT_BY_PROVINCE.get(province, "3-Moderate"), {"aqhi": "fallback_static"}
