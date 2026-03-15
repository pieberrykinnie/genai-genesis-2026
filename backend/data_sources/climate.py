import httpx
import logging

logger = logging.getLogger(__name__)

async def get_annual_mean_temp(lat: float, lon: float) -> float:
    """
    Fetches the approximate annual mean temperature for the past available year using Open-Meteo.
    Defaults to 5.0 C (Canadian average fallback) if the request fails.
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "daily": "temperature_2m_mean",
        "timezone": "auto"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            daily_temps = data.get("daily", {}).get("temperature_2m_mean", [])
            valid_temps = [t for t in daily_temps if t is not None]
            if valid_temps:
                return sum(valid_temps) / len(valid_temps)
    except Exception as e:
        logger.warning(f"Failed to fetch annual mean temp for {lat},{lon}: {e}")
    
    return 5.0
