import pandas as pd
import numpy as np
from pathlib import Path
import logging

import json

logger = logging.getLogger(__name__)

# Data Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DC_CSV_PATH = BASE_DIR / "data" / "canada_dc_osm.csv"
CSD_JSON_PATH = BASE_DIR / "data" / "site_fit_csd_lookup.json"

# In-memory caches to avoid reading on every API call.
_DC_LOCATIONS = None
_CSD_LOOKUP = None

def _load_dc_locations() -> tuple[np.ndarray, np.ndarray]:
    global _DC_LOCATIONS
    if _DC_LOCATIONS is not None:
        return _DC_LOCATIONS

    try:
        # Load from the same CSV used during training dataset generation
        df = pd.read_csv(DC_CSV_PATH)
        # Handle coordinate columns (assuming lat/lng or lat/lon based on train script logic)
        lon_col = "lon" if "lon" in df.columns else "lng"
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
        df = df.dropna(subset=["lat", lon_col])
        
        _DC_LOCATIONS = (df["lat"].values, df[lon_col].values)
    except Exception as e:
        logger.error(f"Failed to load datacenter locations for Site Fit calculation: {e}")
        # Return empty arrays safely so math doesn't crash
        _DC_LOCATIONS = (np.array([]), np.array([]))

    return _DC_LOCATIONS

def _haversine_km(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Vectorized Haversine distance in km from a single point to an array of points."""
    R = 6371.0088
    lat1, lon1 = np.radians(lat1), np.radians(lon1)
    lat2, lon2 = np.radians(lat2), np.radians(lon2)
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    # Ensure a stays within [0, 1] due to precision limits
    a = np.clip(a, 0.0, 1.0)
    
    return 2 * R * np.arcsin(np.sqrt(a))

def fetch_site_fit_datacenter_context(lat: float, lon: float) -> dict[str, float]:
    """
    Computes `distance_to_nearest_dc_km` and `dc_count_within_100km`
    for the requested location using known OSM data centers in Canada.
    """
    dc_lats, dc_lons = _load_dc_locations()
    
    if len(dc_lats) == 0:
        return {
            "distance_to_nearest_dc_km": 150.0,
            "dc_count_within_100km": 0.0
        }
        
    distances = _haversine_km(lat, lon, dc_lats, dc_lons)
    
    min_dist = float(np.min(distances))
    count_100 = float(np.sum(distances <= 100.0))
    
    return {
        "distance_to_nearest_dc_km": min_dist,
        "dc_count_within_100km": count_100
    }

def _load_csd_lookup() -> dict[str, dict[str, float]]:
    global _CSD_LOOKUP
    if _CSD_LOOKUP is not None:
        return _CSD_LOOKUP
        
    try:
        if CSD_JSON_PATH.exists():
            with open(CSD_JSON_PATH, "r") as f:
                _CSD_LOOKUP = json.load(f)
        else:
            _CSD_LOOKUP = {}
            logger.warning(f"CSD JSON not found at {CSD_JSON_PATH}. Fallbacks will trigger.")
    except Exception as e:
        logger.error(f"Failed to load CSD features lookup: {e}")
        _CSD_LOOKUP = {}
        
    return _CSD_LOOKUP

def fetch_site_fit_csd_context(csd_id: str) -> dict[str, float]:
    """
    Retrieves the exact `area_km2` and `business_count` recorded for this CSD 
    during offline data preparation, matching the training regime without loading huge CSVs.
    """
    lookup = _load_csd_lookup()
    
    # Defaults mirror the original safe fallbacks in features.py
    if not csd_id or str(csd_id) not in lookup:
        return {
            "area_km2": 250.0,
            "business_count": 500.0,
            "population": 0.0
        }
        
    return lookup[str(csd_id)]
