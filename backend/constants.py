from __future__ import annotations

from typing import Literal

CanadianProvince = Literal["ON", "AB", "BC", "QC", "MB", "SK", "NS", "NB", "NL", "PE"]
RagScore = Literal["green", "amber", "red"]

PROVINCE_TO_ZONE: dict[str, str] = {
    "ON": "CA-ON",
    "AB": "CA-AB",
    "BC": "CA-BC",
    "QC": "CA-QC",
    "MB": "CA-MB",
    "SK": "CA-SK",
    "NB": "CA-NB",
    "NS": "CA-NS",
    "NL": "CA-NL",
    "PE": "CA-PE",
}

FALLBACK_CARBON_INTENSITY: dict[str, float] = {
    "QC": 1.8,
    "MB": 3.5,
    "BC": 11.0,
    "ON": 29.0,
    "NL": 30.0,
    "SK": 490.0,
    "AB": 530.0,
    "NB": 200.0,
    "NS": 650.0,
    "PE": 8.0,
}

PROVINCIAL_CAPACITY_MW: dict[str, float] = {
    "ON": 37205,
    "AB": 22000,
    "BC": 16000,
    "QC": 40000,
    "MB": 6000,
    "SK": 5000,
    "NB": 4000,
    "NS": 2700,
    "NL": 2300,
    "PE": 500,
}

PROVINCIAL_SURPLUS_PCT: dict[str, float] = {
    "ON": 0.08,
    "AB": 0.15,
    "BC": 0.12,
    "QC": 0.05,
    "MB": 0.20,
    "SK": 0.10,
    "NB": 0.15,
    "NS": 0.08,
    "NL": 0.25,
    "PE": 0.30,
}

PROVINCIAL_GRID_WATER_INTENSITY_L_PER_KWH: dict[str, float] = {
    "ON": 1.1,
    "AB": 1.9,
    "BC": 1.5,
    "QC": 1.4,
    "MB": 1.2,
    "SK": 1.8,
    "NB": 1.7,
    "NS": 1.9,
    "NL": 1.4,
    "PE": 1.2,
}

DROUGHT_LEVEL_2024: dict[str, str] = {
    "AB": "D2",
    "SK": "D1",
    "MB": "D0",
    "BC": "D1",
    "ON": "D0",
    "QC": "None",
    "NB": "None",
    "NS": "D0",
    "NL": "None",
    "PE": "None",
}

DROUGHT_SCORE: dict[str, int] = {
    "None": 0,
    "D0": 1,
    "D1": 2,
    "D2": 3,
    "D3": 4,
    "D4": 5,
}

CARBON_THRESHOLDS = (50_000.0, 200_000.0)
WATER_PCT_THRESHOLDS = (2.0, 10.0)
GRID_STRAIN_THRESHOLDS = (0.25, 0.55)
CVI_THRESHOLDS = (30.0, 60.0)

AUX_ELECTRICITY_RATE_PER_KWH_CAD: dict[str, float] = {
    "ON": 0.18,
    "AB": 0.16,
    "BC": 0.14,
    "QC": 0.11,
    "MB": 0.11,
    "SK": 0.18,
    "NB": 0.17,
    "NS": 0.20,
    "NL": 0.17,
    "PE": 0.19,
}
