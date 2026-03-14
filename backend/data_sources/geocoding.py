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

PROVINCE_FULL_NAMES: dict[str, str] = {
    "ON": "Ontario",
    "AB": "Alberta",
    "BC": "British Columbia",
    "QC": "Quebec",
    "MB": "Manitoba",
    "SK": "Saskatchewan",
    "NB": "New Brunswick",
    "NS": "Nova Scotia",
    "NL": "Newfoundland and Labrador",
    "PE": "Prince Edward Island",
}


class GeocodingUnavailableError(RuntimeError):
    pass


def province_centroid(province: str, municipality_hint: str | None = None) -> dict:
    lat, lng, municipality, csd, cd = PROVINCE_DEFAULT_COORDS[province]
    return {
        "lat": lat,
        "lng": lng,
        "municipality": municipality_hint or municipality,
        "census_subdivision_id": csd,
        "census_division_id": cd,
    }


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_maptiler_feature(payload: dict) -> dict:
    features = payload.get("features", [])
    if not features:
        raise GeocodingUnavailableError("maptiler_no_features")

    top = features[0]
    lng, lat = top.get("center", [None, None])
    if lat is None or lng is None:
        raise GeocodingUnavailableError("maptiler_missing_coordinates")

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

    return {
        "lat": float(lat),
        "lng": float(lng),
        "municipality": municipality,
        "census_subdivision_id": csd or "",
        "census_division_id": cd or "",
    }


def _parse_nominatim_result(payload: list[dict]) -> dict:
    if not payload:
        raise GeocodingUnavailableError("nominatim_no_results")

    top = payload[0]
    lat_raw = top.get("lat")
    lng_raw = top.get("lon")
    if lat_raw is None or lng_raw is None:
        raise GeocodingUnavailableError("nominatim_missing_coordinates")

    addr = top.get("address") or {}
    municipality = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
        or addr.get("county")
        or addr.get("state_district")
        or str(top.get("display_name") or "Unknown").split(",")[0].strip()
        or "Unknown"
    )

    return {
        "lat": float(lat_raw),
        "lng": float(lng_raw),
        "municipality": municipality,
        "census_subdivision_id": "",
        "census_division_id": "",
    }


def _candidate_queries(address: str, province: str) -> list[str]:
    parts = [p.strip() for p in address.split(",") if p.strip()]
    queries: list[str] = []

    def _add(query: str) -> None:
        query = query.strip()
        if query and query not in queries:
            queries.append(query)

    _add(address)
    if len(parts) >= 2:
        _add(", ".join(parts[1:]))
    if len(parts) >= 3:
        _add(", ".join(parts[-3:]))

    if parts:
        first = parts[0].lower()
        if first.startswith("municipal district") or first.startswith("regional municipality") or first.startswith("county"):
            if len(parts) >= 2:
                _add(", ".join(parts[1:]))
                province_name = PROVINCE_FULL_NAMES.get(province.upper(), province)
                _add(f"{parts[1]}, {province_name}, Canada")

    if "canada" not in address.lower():
        province_name = PROVINCE_FULL_NAMES.get(province.upper(), province)
        _add(f"{address}, {province_name}, Canada")

    return queries


async def geocode_address(address: str, province: str) -> tuple[dict, dict[str, str]]:
    settings = get_settings()
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        if settings.maptiler_api_key:
            try:
                maptiler_url = f"https://api.maptiler.com/geocoding/{quote(address)}.json"
                maptiler_resp = await client.get(
                    maptiler_url,
                    params={"key": settings.maptiler_api_key, "country": "ca", "limit": 1},
                )
                maptiler_resp.raise_for_status()
                maptiler_location = _parse_maptiler_feature(maptiler_resp.json())
                return maptiler_location, {"maptiler_geocoding": f"live:maptiler:{_timestamp()}"}
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else "unknown"
                errors.append(f"maptiler_http_{status}")
            except Exception as exc:
                errors.append(f"maptiler_{exc.__class__.__name__}")
        else:
            errors.append("maptiler_key_missing")

        nominatim_queries = _candidate_queries(address, province)
        nominatim_errors: list[str] = []
        for query in nominatim_queries:
            try:
                nominatim_resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": query,
                        "format": "jsonv2",
                        "countrycodes": "ca",
                        "limit": 1,
                        "addressdetails": 1,
                    },
                    headers={
                        "User-Agent": settings.nominatim_user_agent,
                        "Accept": "application/json",
                    },
                )
                nominatim_resp.raise_for_status()
                nominatim_location = _parse_nominatim_result(nominatim_resp.json())
                return nominatim_location, {"maptiler_geocoding": f"live:nominatim:{_timestamp()}"}
            except GeocodingUnavailableError as exc:
                nominatim_errors.append(str(exc))
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else "unknown"
                nominatim_errors.append(f"http_{status}")
            except Exception as exc:
                nominatim_errors.append(exc.__class__.__name__)

        if nominatim_errors:
            errors.append(f"nominatim_failed_{len(nominatim_queries)}queries")
        else:
            errors.append("nominatim_not_attempted")

    if settings.strict_data_mode:
        raise GeocodingUnavailableError(" | ".join(errors))

    municipality_hint = address.split(",")[0].strip() if address else None
    return province_centroid(province, municipality_hint=municipality_hint), {
        "maptiler_geocoding": "static_reference:province_centroid"
    }
