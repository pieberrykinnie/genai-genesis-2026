from __future__ import annotations

from datetime import datetime, timezone

import numpy as np


def engineer_prediction_features(
    province: str,
    it_load_mw: float,
    pue: float,
    capacity_mw: float,
    current_demand_mw: float,
) -> tuple[np.ndarray, list[str]]:
    now = datetime.now(timezone.utc)
    proposal_draw = it_load_mw * pue
    projected_demand = current_demand_mw + proposal_draw
    utilization = 0.0 if capacity_mw <= 0 else projected_demand / capacity_mw

    features = {
        "proposal_draw_mw": proposal_draw,
        "projected_demand_mw": projected_demand,
        "capacity_mw": capacity_mw,
        "utilization": utilization,
        "month": float(now.month),
        "day_of_week": float(now.weekday()),
        "is_weekend": float(now.weekday() >= 5),
        "is_summer": float(now.month in [6, 7, 8]),
        "is_winter": float(now.month in [12, 1, 2]),
        "province_on": float(province == "ON"),
        "province_ab": float(province == "AB"),
    }
    keys = list(features.keys())
    return np.array([list(features.values())], dtype=float), keys
