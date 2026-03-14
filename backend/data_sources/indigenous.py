from __future__ import annotations

import csv
import json
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

from config import get_settings


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return radius * 2 * atan2(sqrt(a), sqrt(1 - a))


class IndigenousData:
    def __init__(self) -> None:
        settings = get_settings()
        self.centroids_path = settings.data_dir / "reserves_centroids.csv"
        self.advisories_path = settings.data_dir / "water_advisories.json"

    def _load_centroids(self) -> list[dict]:
        if not self.centroids_path.exists():
            return []
        out: list[dict] = []
        with self.centroids_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    out.append(
                        {
                            "name": row.get("NAME", "Unknown"),
                            "treaty": row.get("TREATY") or None,
                            "lat": float(row.get("centroid_lat", "0")),
                            "lng": float(row.get("centroid_lng", "0")),
                        }
                    )
                except Exception:
                    continue
        return out

    def _load_advisories(self) -> set[str]:
        if not self.advisories_path.exists():
            return set()
        try:
            with self.advisories_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            entries = payload if isinstance(payload, list) else payload.get("communities", [])
            return {str(item).strip().lower() for item in entries}
        except Exception:
            return set()

    def nearest_reserve(self, lat: float, lng: float) -> tuple[dict, dict[str, str]]:
        centroids = self._load_centroids()
        advisory_set = self._load_advisories()

        if not centroids:
            return (
                {
                    "name": "Unknown",
                    "distance_km": 120.0,
                    "treaty": None,
                    "active_water_advisories_nearby": 0,
                    "indigenous_flag": False,
                },
                {"indigenous_data": "fallback_defaults"},
            )

        nearest = min(
            centroids,
            key=lambda r: haversine_km(lat, lng, float(r["lat"]), float(r["lng"])),
        )
        distance = haversine_km(lat, lng, float(nearest["lat"]), float(nearest["lng"]))
        has_advisory = nearest["name"].strip().lower() in advisory_set
        indigenous_flag = distance <= 50.0 or has_advisory

        return (
            {
                "name": nearest["name"],
                "distance_km": round(distance, 2),
                "treaty": nearest.get("treaty"),
                "active_water_advisories_nearby": int(has_advisory),
                "indigenous_flag": indigenous_flag,
            },
            {"indigenous_data": "local_cache"},
        )


def get_indigenous_data() -> IndigenousData:
    return IndigenousData()
