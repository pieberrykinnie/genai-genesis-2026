from __future__ import annotations

import pytest

from ml.grid_strain import predict as grid_predict
from ml.grid_strain.predict import _normalize_probability, _strain_level_from_probability


def test_strain_level_from_probability_bands() -> None:
    assert _strain_level_from_probability(0.01) == "low"
    assert _strain_level_from_probability(0.2499) == "low"
    assert _strain_level_from_probability(0.25) == "moderate"
    assert _strain_level_from_probability(0.54) == "moderate"
    assert _strain_level_from_probability(0.55) == "high"


def test_normalize_probability_keeps_tiny_non_zero_visible() -> None:
    assert _normalize_probability(0.0002) == 0.001
    assert _normalize_probability(0.0) == 0.0
    assert _normalize_probability(0.12) == 0.12


@pytest.mark.asyncio
async def test_predict_grid_strain_uses_capacity_stress_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    class _MockModel:
        def predict_proba(self, _features):
            return [[0.9997, 0.0003]]

    artifact = {
        "model": _MockModel(),
        "feature_cols": ["proposal_draw_mw", "month", "hour", "day_of_week", "is_weekend", "is_summer", "is_winter", "province_on", "province_ab"],
        "feature_importances": [0.8, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.07, 0.07],
        "cv_auc": 0.81,
        "version": "test-model",
    }

    monkeypatch.setattr(grid_predict, "_load_model_artifact", lambda: artifact)

    pred = await grid_predict.predict_grid_strain(
        province="AB",
        it_load_mw=200,
        pue=1.5,
        capacity_mw=22000,
        current_utilization=0.5,
    )

    # Tiny model output should be lifted above display-loss range by normalization/stress floor.
    assert pred.strain_probability >= 0.001
    assert pred.model_version == "test-model"
