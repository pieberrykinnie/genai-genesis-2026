from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from config import get_settings
from models import GridStrainPrediction

from .train import engineer_prediction_features


def _strain_level_from_probability(strain_probability: float) -> str:
    if strain_probability < 0.25:
        return "low"
    if strain_probability < 0.55:
        return "moderate"
    return "high"


def _normalize_probability(value: float) -> float:
    clamped = max(0.0, min(0.9999, float(value)))
    # Keep tiny non-zero values visible to downstream consumers that round display.
    if 0.0 < clamped < 0.001:
        return 0.001
    return clamped


@lru_cache(maxsize=1)
def _load_model_artifact() -> dict[str, Any] | None:
    settings = get_settings()
    model_path = Path(settings.model_path)
    if not model_path.exists():
        return None
    try:
        artifact = joblib.load(model_path)
    except Exception:
        return None
    return artifact if isinstance(artifact, dict) else None


def _fallback_prediction(total_power_draw_mw: float, utilization: float | None) -> GridStrainPrediction:
    strain_probability = _normalize_probability(max(0.02, min(0.98, total_power_draw_mw / 850.0 + (utilization or 0.0) * 0.35)))
    rate_increase_probability = _normalize_probability(max(0.01, min(0.95, strain_probability * 0.7 + (utilization or 0.0) * 0.2)))
    level = _strain_level_from_probability(strain_probability)
    return GridStrainPrediction(
        strain_probability=round(strain_probability, 4),
        rate_increase_probability=round(rate_increase_probability, 4),
        predicted_strain_level=level,
        confidence=0.62,
        model_version="heuristic-grid-fallback-v1",
        top_features=[
            {"feature": "proposal_draw_mw", "importance": 1.0, "value": round(total_power_draw_mw, 2)},
            {"feature": "current_utilization", "importance": 0.7, "value": round(utilization or 0.0, 4)},
        ],
    )


async def predict_grid_strain(
    province: str,
    it_load_mw: float,
    pue: float,
    capacity_mw: int,
    current_utilization: float | None = None,
) -> GridStrainPrediction:
    total_power_draw_mw = max(0.0, float(it_load_mw) * float(pue))
    capacity_mw = max(1, int(capacity_mw))
    artifact = _load_model_artifact()
    if artifact is None:
        return _fallback_prediction(total_power_draw_mw, current_utilization)

    model = artifact.get("model")
    feature_cols = artifact.get("feature_cols")
    if model is None or not isinstance(feature_cols, list):
        return _fallback_prediction(total_power_draw_mw, current_utilization)

    try:
        features = engineer_prediction_features(
            province=province,
            proposal_draw_mw=total_power_draw_mw,
            feature_cols=feature_cols,
            when=datetime.now(timezone.utc),
        )
        probabilities = model.predict_proba(features)[0]
        strain_probability = float(probabilities[1]) if len(probabilities) > 1 else float(probabilities[0])
    except Exception:
        return _fallback_prediction(total_power_draw_mw, current_utilization)

    utilization = float(current_utilization or 0.0)
    capacity_pressure = total_power_draw_mw / float(capacity_mw)
    stress_floor = min(0.05, capacity_pressure * 0.8 + utilization * 0.02)
    strain_probability = _normalize_probability(max(strain_probability, stress_floor))
    rate_increase_probability = _normalize_probability(max(0.01, min(0.95, strain_probability * 0.72 + utilization * 0.24)))
    level = _strain_level_from_probability(strain_probability)

    importances = np.asarray(artifact.get("feature_importances", []), dtype=float)
    feature_values = {col: float(features[0][idx]) for idx, col in enumerate(feature_cols)}
    ranked_indices = np.argsort(importances)[::-1] if importances.size else np.arange(len(feature_cols))
    top_features = [
        {
            "feature": feature_cols[idx],
            "importance": round(float(importances[idx]) if importances.size else 0.0, 4),
            "value": round(feature_values[feature_cols[idx]], 4),
        }
        for idx in ranked_indices[:4]
    ]
    model_confidence = artifact.get("cv_auc") or artifact.get("train_auc") or 0.75

    return GridStrainPrediction(
        strain_probability=round(strain_probability, 6),
        rate_increase_probability=round(rate_increase_probability, 6),
        predicted_strain_level=level,
        confidence=round(float(model_confidence), 4),
        model_version=str(artifact.get("version", "xgboost-grid-model")),
        top_features=top_features,
    )
