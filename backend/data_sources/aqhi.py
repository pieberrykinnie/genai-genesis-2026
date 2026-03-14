from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from config import get_settings

# Maps 2-letter province codes to the ECCC region folder name used in:
# backend/data/aqhi/<region>/<YYYYMMDDTHHMMZ>_MSC_AQHI-Observation_<ID>.json
PROVINCE_TO_REGION: dict[str, str] = {
    "ON": "ont",
    "QC": "que",
    "NB": "atl",
    "NS": "atl",
    "PE": "atl",
    "NL": "atl",
    "AB": "pnr",
    "SK": "pnr",
    "MB": "pnr",
    "BC": "pyr",
    "YT": "pyr",
    "NT": "pnr",
    "NU": "pnr",
}

AQHI_DEFAULT_BY_PROVINCE: dict[str, float] = {
    "ON": 3.0,
    "AB": 3.0,
    "BC": 2.0,
    "QC": 2.0,
    "MB": 2.0,
    "SK": 3.0,
    "NB": 2.0,
    "NS": 2.0,
    "NL": 2.0,
    "PE": 2.0,
}


def _read_local_aqhi(region_dir: Path) -> list[float]:
    values: list[float] = []
    if not region_dir.is_dir():
        return values
    for f in region_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            props = data.get("properties", {})
            val = props.get("aqhi")
            if val is not None:
                values.append(float(val))
        except Exception:
            continue
    return values


async def get_aqhi_baseline(province: str) -> tuple[str, dict[str, str]]:
    settings = get_settings()
    province = province.upper()

    url = "https://dd.weather.gc.ca/air_quality/aqhi/observation/realtime/json"
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
        for item in payload:
            if str(item.get("province_code", "")).upper() == province:
                value = item.get("aqhi") or AQHI_DEFAULT_BY_PROVINCE.get(province, 3.0)
                stamp = item.get("forecast_datetime", datetime.now(timezone.utc).isoformat())
                return str(value), {"aqhi": f"live:{stamp}"}
    except Exception:
        pass

    region = PROVINCE_TO_REGION.get(province)
    if region:
        region_dir = settings.data_dir / "aqhi" / region
        values = _read_local_aqhi(region_dir)
        if values:
            peak = max(values)
            return str(round(peak, 2)), {"aqhi": f"static_reference:local_geojson:{region}"}

    default = AQHI_DEFAULT_BY_PROVINCE.get(province, 3.0)
    return str(default), {"aqhi": "unavailable:aqhi_feed_unreachable"}
