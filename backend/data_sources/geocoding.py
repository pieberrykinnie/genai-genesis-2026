from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from config import get_settings

PROVINCE_DEFAULT_COORDS: dict[str, tuple[float, float, str, str, str]] = {
    "ON": (43.6532, -79.3832, "Toronto", "3520005", "3520"),
    "AB": (53.5461, -113.4938, "Edmonton", "4811061", "4811"),
    "BC": (49.2827, -123.1207, "Vancouver", "5915022", "5915"),
    "QC": (46.8139, -71.2080, "Quebec City", "2423027", "2423"),
    "MB": (49.8951, -97.1384, "Winnipeg", "4611040", "4611"),
    "SK": (52.1332, -106.6700, "Saskatoon", "4711066", "4711"),
    "NB": (45.9636, -66.6431, "Fredericton", "1310032", "1310"),
    "NS": (44.6488, -63.5752, "Halifax", "1209034", "1209"),
    "NL": (47.5615, -52.7126, "St. John's", "1001519", "1001"),
    "PE": (46.2382, -63.1311, "Charlottetown", "1102075", "1102"),
}


async def geocode_address(address: str, province: str) -> tuple[dict, dict[str, str]]:
    settings = get_settings()
    if settings.maptiler_api_key:
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                url = f"https://api.maptiler.com/geocoding/{quote(address)}.json"
                resp = await client.get(url, params={"key": settings.maptiler_api_key, "country": "ca", "limit": 1})
                resp.raise_for_status()
                payload = resp.json()

            features = payload.get("features", [])
            if features:
                top = features[0]
                lng, lat = top.get("center", [None, None])
                context_items = top.get("context") or []
                municipality = top.get("text") or top.get("place_name") or "Unknown"
                csd = ""
                cd = ""
                for item in context_items:
                    code = str(item.get("short_code") or "")
                    if code.startswith("ca-"):
                        continue
                    if code.isdigit() and len(code) == 7:
                        csd = code
                    if code.isdigit() and len(code) == 4:
                        cd = code
                if lat is not None and lng is not None:
                    return (
                        {
                            "lat": float(lat),
                            "lng": float(lng),
                            "municipality": municipality,
                            "census_subdivision_id": csd or "",
                            "census_division_id": cd or "",
                        },
                        {"maptiler_geocoding": datetime.now(timezone.utc).isoformat()},
                    )
        except Exception:
            pass

    lat, lng, municipality, csd, cd = PROVINCE_DEFAULT_COORDS[province]
    return (
        {
            "lat": lat,
            "lng": lng,
            "municipality": municipality,
            "census_subdivision_id": csd,
            "census_division_id": cd,
        },
        {"maptiler_geocoding": "fallback_province_centroid"},
    )
