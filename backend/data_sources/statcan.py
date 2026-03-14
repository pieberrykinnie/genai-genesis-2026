from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import get_settings


DEFAULT_DEMOGRAPHICS: dict[str, float] = {
    "total_population": 150000.0,
    "median_total_income": 76000.0,
    "unemployment_rate": 6.1,
    "pct_indigenous_identity": 4.5,
    "pct_low_income_lim_at": 13.0,
    "pct_postsecondary_certificate": 64.0,
}


class StatCanStore:
    def __init__(self, db_path: Path | None = None) -> None:
        settings = get_settings()
        self.db_path = db_path or settings.data_dir / "census_csd.db"

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_csd_demographics(self, csd_uid: str, province: str) -> tuple[dict[str, float], dict[str, str]]:
        if self.db_path.exists():
            try:
                with self._connect() as conn:
                    rows = conn.execute(
                        """
                        SELECT characteristic, value
                        FROM census_profile
                        WHERE geo_uid = ?
                        """,
                        (csd_uid,),
                    ).fetchall()
                if rows:
                    mapped = {str(r["characteristic"]): float(r["value"]) for r in rows}
                    out = {
                        "total_population": mapped.get("total_population", DEFAULT_DEMOGRAPHICS["total_population"]),
                        "median_total_income": mapped.get("median_total_income", DEFAULT_DEMOGRAPHICS["median_total_income"]),
                        "unemployment_rate": mapped.get("unemployment_rate", DEFAULT_DEMOGRAPHICS["unemployment_rate"]),
                        "pct_indigenous_identity": mapped.get("pct_indigenous_identity", DEFAULT_DEMOGRAPHICS["pct_indigenous_identity"]),
                        "pct_low_income_lim_at": mapped.get("pct_low_income_lim_at", DEFAULT_DEMOGRAPHICS["pct_low_income_lim_at"]),
                        "pct_postsecondary_certificate": mapped.get(
                            "pct_postsecondary_certificate", DEFAULT_DEMOGRAPHICS["pct_postsecondary_certificate"]
                        ),
                    }
                    return out, {"statcan_census": self.db_path.stat().st_mtime_ns.__str__()}
            except Exception:
                pass

        demo = dict(DEFAULT_DEMOGRAPHICS)
        if province == "AB":
            demo["pct_indigenous_identity"] = 7.0
            demo["unemployment_rate"] = 6.8
        return demo, {"statcan_census": "fallback_defaults"}

    def get_municipal_supply_l_day(self, csd_uid: str, population: int) -> tuple[float, dict[str, str]]:
        if self.db_path.exists():
            try:
                with self._connect() as conn:
                    row = conn.execute(
                        """
                        SELECT daily_supply_litres
                        FROM municipal_water_use
                        WHERE geo_uid = ?
                        LIMIT 1
                        """,
                        (csd_uid,),
                    ).fetchone()
                if row and row["daily_supply_litres"] is not None:
                    return float(row["daily_supply_litres"]), {"statcan_water": self.db_path.stat().st_mtime_ns.__str__()}
            except Exception:
                pass

        estimated = float(population) * 220.0
        return estimated, {"statcan_water": "fallback_population_estimate"}


def get_statcan_store() -> StatCanStore:
    return StatCanStore()
