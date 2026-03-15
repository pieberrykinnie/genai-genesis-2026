import asyncio
import csv
from pathlib import Path
import httpx

import sys
import os

# Add backend to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from data_sources.drought import get_drought_level
from data_sources.electricity_maps import get_carbon_intensity_g_per_kwh
from ml.site_fit.features import DROUGHT_SCORE

CSV_PATH = Path(__file__).parent.parent.parent / "data" / "site_fit_training_v1_canada.csv"
OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "site_fit_training_v1_canada_completed.csv"

async def get_province_from_lat_lon(client: httpx.AsyncClient, lat: float, lon: float) -> str:
    """Reverse geocode to get the province abbreviation using Nominatim API."""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "jsonv2"
    }
    headers = {
        "User-Agent": "genai-genesis-2026-site-fit"
    }
    try:
        resp = await client.get(url, params=params, headers=headers, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        if "address" in data:
            state = data["address"].get("state", "")
            mapping = {
                "Ontario": "ON",
                "Alberta": "AB",
                "British Columbia": "BC",
                "Québec": "QC",
                "Quebec": "QC",
                "Manitoba": "MB",
                "Saskatchewan": "SK",
                "New Brunswick": "NB",
                "Nova Scotia": "NS",
                "Newfoundland and Labrador": "NL",
                "Prince Edward Island": "PE",
            }
            return mapping.get(state, "ON")
    except Exception as e:
        print(f"Warning: Reverse geocoding failed for {lat}, {lon}: {e}")
    return "ON" # Default fallback

async def fetch_annual_mean_temp(client: httpx.AsyncClient, lat: float, lon: float) -> float:
    """Use Open-Meteo archive API to get an approximate annual mean temp for the last year (2023)."""
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
        resp = await client.get(url, params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        daily_temps = data.get("daily", {}).get("temperature_2m_mean", [])
        valid_temps = [t for t in daily_temps if t is not None]
        if valid_temps:
            return sum(valid_temps) / len(valid_temps)
    except Exception as e:
        print(f"Warning: Failed to fetch temp for {lat}, {lon}: {e}")
    return 5.0  # Safe Canadian fallback

async def process_row(client: httpx.AsyncClient, row: dict) -> dict:
    lat = float(row["lat"])
    lon = float(row["lon"])
    
    # 1. We need the province to get carbon intensity and drought level
    province = await get_province_from_lat_lon(client, lat, lon)
    
    # 2. Get carbon intensity using existing deterministic function
    carbon_intensity, _ = await get_carbon_intensity_g_per_kwh(province)
    
    # 3. Get expected water_stress_score based on your deterministic formulas in features.py
    # Since this is a training point with no proposal load, we assume water_share_pct = 0
    # Formula in repo: min(100.0, water_share_pct * 3.2 + drought_score * 12.0)
    drought_level, _ = get_drought_level(province)
    drought_score = float(DROUGHT_SCORE.get(drought_level, 1))
    water_stress_score = min(100.0, drought_score * 12.0)
    
    # 4. Get annual mean temp (external API since it's not in repo yet)
    annual_mean_temp_c = await fetch_annual_mean_temp(client, lat, lon)
    
    row["annual_mean_temp_c"] = round(annual_mean_temp_c, 2)
    row["grid_carbon_intensity"] = round(carbon_intensity, 2)
    row["water_stress_score"] = round(water_stress_score, 2)
    
    print(f"Processed {row['site_id']} in {province}: "
          f"Temp={row['annual_mean_temp_c']}C, "
          f"Carbon={row['grid_carbon_intensity']}g/kWh, "
          f"WaterStress={row['water_stress_score']}")
    
    return row

async def main():
    if not CSV_PATH.exists():
        print(f"File not found: {CSV_PATH}")
        return

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames)

    fieldnames.extend(["annual_mean_temp_c", "grid_carbon_intensity", "water_stress_score"])
    
    # We use limits on concurrency for APIs like Open-Meteo and Nominatim
    semaphore = asyncio.Semaphore(3)
    
    async with httpx.AsyncClient() as client:
        async def sem_process_row(row):
            async with semaphore:
                # Add a tiny sleep to be nice to free APIs
                await asyncio.sleep(0.5)
                return await process_row(client, row)

        tasks = [sem_process_row(r) for r in rows]
        completed_rows = await asyncio.gather(*tasks)
            
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(completed_rows)
        
    print(f"Saved completed dataset to: {OUTPUT_PATH}")

if __name__ == "__main__":
    asyncio.run(main())
