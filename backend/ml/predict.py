from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np

from config import get_settings
from models import GridStrainPrediction
from ml.features import engineer_prediction_features

_MODEL_ARTIFACT: dict[str, Any] | None = None


def _heuristic_probability(utilization: float, proposal_draw_mw: float) -> float:
    base = 0.15 + max(0.0, utilization - 0.70) * 1.6 + min(0.25, proposal_draw_mw / 1500.0)
    return max(0.01, min(0.99, base))


def _load_model_artifact() -> dict[str, Any] | None:
    global _MODEL_ARTIFACT
    if _MODEL_ARTIFACT is not None:
        return _MODEL_ARTIFACT

    settings = get_settings()
    path = Path(settings.model_path)
    if not path.exists():
        return None

    try:
        artifact = joblib.load(path)
    except Exception:
        return None

    if not isinstance(artifact, dict) or "model" not in artifact:
        return None

    _MODEL_ARTIFACT = artifact
    return artifact


def predict_grid_strain(
    province: str,
    it_load_mw: float,
    pue: float,
    capacity_mw: float,
    current_demand_mw: float,
) -> GridStrainPrediction:
    features_arr, feature_keys = engineer_prediction_features(
        province=province,
        it_load_mw=it_load_mw,
        pue=pue,
        capacity_mw=capacity_mw,
        current_demand_mw=current_demand_mw,
    )

    artifact = _load_model_artifact()
    model = artifact.get("model") if artifact else None

    if model is not None and hasattr(model, "predict_proba"):
        probability = float(model.predict_proba(features_arr)[0, 1])
        importance_values = getattr(model, "feature_importances_", np.array([0.0] * len(feature_keys)))
        top_features = sorted(
            [
                {"feature": k, "importance": round(float(v), 4)}
                for k, v in zip(feature_keys, importance_values, strict=False)
            ],
            key=lambda x: -x["importance"],
        )[:5]
        model_version = str(artifact.get("version", "xgboost_v1_ieso_aeso_2024"))
        confidence = float(artifact.get("cv_auc", artifact.get("train_auc", 0.75)))
    else:
        utilization = float(features_arr[0, 3])
        proposal_draw = float(features_arr[0, 0])
        probability = _heuristic_probability(utilization=utilization, proposal_draw_mw=proposal_draw)
        top_features = [
            {"feature": "utilization", "importance": 0.45},
            {"feature": "proposal_draw_mw", "importance": 0.35},
            {"feature": "projected_demand_mw", "importance": 0.20},
        ]
        model_version = "heuristic_fallback_v1"
        confidence = 0.62

    rate_increase_probability = min(1.0, probability * 0.85)
    if probability < 0.25:
        level = "low"
    elif probability < 0.50:
        level = "moderate"
    elif probability < 0.75:
        level = "high"
    else:
        level = "critical"

    return GridStrainPrediction(
        strain_probability=round(probability, 4),
        rate_increase_probability=round(rate_increase_probability, 4),
        predicted_strain_level=level,
        confidence=round(confidence, 3),
        model_version=model_version,
        top_features=top_features,
    )
