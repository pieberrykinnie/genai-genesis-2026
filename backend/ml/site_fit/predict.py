from __future__ import annotations

import logging
from pathlib import Path

from catboost import CatBoostClassifier

from models import SiteFitPrediction
from .features import extract_site_features

logger = logging.getLogger(__name__)

# Load the model exactly once per worker
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "models" / "site_fit_catboost.cbm"

_CATBOOST_MODEL = None

def _get_model() -> CatBoostClassifier:
    global _CATBOOST_MODEL
    if _CATBOOST_MODEL is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Site Fit model not found at {MODEL_PATH}")
        logger.info("Loading CatBoost Site Fit model into memory...")
        _CATBOOST_MODEL = CatBoostClassifier()
        _CATBOOST_MODEL.load_model(str(MODEL_PATH))
    return _CATBOOST_MODEL


async def predict_site_fit(proposal, public_context) -> SiteFitPrediction:
    features = extract_site_features(proposal, public_context)

    # Required features must strictly match the train.py ordering:
    # 1. annual_mean_temp_c, 2. grid_carbon_intensity, 3. water_stress_score,
    # 4. population_density, 5. business_density, 6. distance_to_nearest_dc_km, 7. dc_count_within_100km
    
    # Safely convert to float and use medians/defaults if None
    annual_mean_temp_c = float(features.get("annual_mean_temp_c") or 5.0)
    grid_carbon_intensity = float(features.get("grid_carbon_intensity") or 250.0)
    water_stress_score = float(features.get("water_stress_score") or 15.0)
    population_density = float(features.get("population_density") or 300.0)
    business_density = float(features.get("business_density") or 1.0)
    distance_to_nearest_dc_km = float(features.get("distance_to_nearest_dc_km") or 100.0)
    dc_count_within_100km = float(features.get("dc_count_within_100km") or 0.0)

    input_vector = [
        annual_mean_temp_c,
        grid_carbon_intensity,
        water_stress_score,
        population_density,
        business_density,
        distance_to_nearest_dc_km,
        dc_count_within_100km
    ]

    try:
        model = _get_model()
        # predict_proba returns [prob_class_0, prob_class_1]
        fit_probability = float(model.predict_proba([input_vector])[0][1])
    except Exception as e:
        logger.error(f"CatBoost inference failed: {e}. Falling back to heuristic.")
        # Fallback heuristic if the model crashes (prevents blocking)
        penalty = (water_stress_score * 0.01 + min(grid_carbon_intensity / 900.0, 0.20))
        resilience = min(distance_to_nearest_dc_km / 250.0, 0.18)
        fit_probability = max(0.05, min(0.95, 0.78 + resilience - penalty))

    # Calculate band
    if fit_probability >= 0.70:
        band = "high"
    elif fit_probability >= 0.40:
        band = "moderate"
    else:
        band = "low"

    # Quick heuristics to supply reasons to the frontend
    feature_impacts = {
        "water_stress_score": -(water_stress_score * 0.010),
        "grid_carbon_intensity": -min(grid_carbon_intensity / 900.0, 0.20),
        "distance_to_nearest_dc": min(distance_to_nearest_dc_km / 250.0, 0.18),
        "dc_density": min(dc_count_within_100km / 20.0, 0.08)
    }
    
    top_features = [
        {"feature": name, "impact": round(value, 4), "value": round(float(features.get(name) or 0.0), 4)}
        for name, value in sorted(feature_impacts.items(), key=lambda item: abs(item[1]), reverse=True)
    ]

    return SiteFitPrediction(
        site_fit_probability=round(fit_probability, 4),
        site_fit_band=band,
        confidence=0.85,
        model_version="catboost_site_fit_v1",
        top_features=top_features[:3],
        nearest_similar_sites=[],
    )
