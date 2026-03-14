from __future__ import annotations

import json
from pathlib import Path

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
    """Return a list of AQHI float values from all GeoJSON files in region_dir."""
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
    """
    Return (aqhi_label, freshness_dict) for the given 2-letter province code.

    Reads the latest locally downloaded ECCC GeoJSON files from:
        <data_dir>/aqhi/<region>/*.json

    Falls back to static defaults if no local data is available.
    """
    settings = get_settings()
    region = PROVINCE_TO_REGION.get(province.upper())

    if region:
        region_dir = settings.data_dir / "aqhi" / region
        values = _read_local_aqhi(region_dir)
        if values:
            # Use the maximum observed AQHI as a conservative stress baseline.
            peak = max(values)
            return str(round(peak, 2)), {"aqhi": "local_geojson", "region": region, "stations_read": str(len(values))}

    default = AQHI_DEFAULT_BY_PROVINCE.get(province.upper(), 3.0)
    return str(default), {"aqhi": "fallback_static"}
