from __future__ import annotations

from constants import DROUGHT_LEVEL_2024


def get_drought_level(province: str) -> tuple[str, dict[str, str]]:
    level = DROUGHT_LEVEL_2024.get(province, "D0")
    return level, {"drought_monitor": "fallback_2024_provincial"}
