from __future__ import annotations

from models import SiteFitPrediction

from .features import extract_site_features


async def predict_site_fit(proposal, public_context) -> SiteFitPrediction:
    features = extract_site_features(proposal, public_context)

    penalty = (
        features["water_stress_score"] * 0.010
        + min(features["grid_carbon_intensity"] / 900.0, 0.20)
        + min(features["aqhi_value"] / 20.0, 0.20)
        + min(features["community_vulnerability_index"] / 250.0, 0.25)
        + min(features["population_density"] / 20000.0, 0.12)
        + min(features["dc_count_within_100km"] / 20.0, 0.08)
        + (0.05 if features["indigenous_flag"] else 0.0)
        + features["cooling_penalty"] / 100.0
    )
    resilience = min(features["distance_to_nearest_dc_km"] / 250.0, 0.18)
    fit_probability = max(0.05, min(0.95, 0.78 + resilience - penalty))

    if fit_probability >= 0.70:
        band = "strong"
    elif fit_probability >= 0.40:
        band = "moderate"
    else:
        band = "weak"

    feature_impacts = {
        "water_stress_score": -(features["water_stress_score"] * 0.010),
        "grid_carbon_intensity": -min(features["grid_carbon_intensity"] / 900.0, 0.20),
        "community_vulnerability_index": -min(features["community_vulnerability_index"] / 250.0, 0.25),
        "distance_to_nearest_dc_km": resilience,
    }
    top_features = [
        {"feature": name, "impact": round(value, 4), "value": round(float(features[name]), 4)}
        for name, value in sorted(feature_impacts.items(), key=lambda item: abs(item[1]), reverse=True)
    ]

    return SiteFitPrediction(
        site_fit_probability=round(fit_probability, 4),
        site_fit_band=band,
        confidence=0.66,
        model_version="heuristic_site_fit_v2_public_context",
        top_features=top_features,
        nearest_similar_sites=[],
    )
