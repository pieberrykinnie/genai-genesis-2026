from __future__ import annotations

from constants import PROVINCIAL_CAPACITY_MW, PROVINCIAL_SURPLUS_PCT


def get_capacity_and_surplus(province: str) -> tuple[float, float, dict[str, str]]:
    capacity = PROVINCIAL_CAPACITY_MW.get(province, 5000.0)
    surplus = PROVINCIAL_SURPLUS_PCT.get(province, 0.10)
    freshness = {
        "provincial_grid_capacity": "2024_static_fallback",
        "provincial_grid_surplus": "2024_static_fallback",
    }
    return capacity, surplus, freshness
