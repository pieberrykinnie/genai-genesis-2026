from pathlib import Path

from data_sources.statcan import StatCanStore


def test_census_province_aggregate_fallback_from_sqlite(tmp_path: Path) -> None:
    db = tmp_path / "census_csd.db"
    store = StatCanStore(db_path=db)

    with store._connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS census_profile (
                geo_uid TEXT NOT NULL,
                characteristic TEXT NOT NULL,
                value REAL,
                PRIMARY KEY (geo_uid, characteristic)
            )
            """
        )
        conn.execute(
            "INSERT OR REPLACE INTO census_profile (geo_uid, characteristic, value) VALUES (?, ?, ?)",
            ("1000248", "total_population", 4_200_000.0),
        )
        conn.commit()

    out, freshness = store.get_csd_demographics("9999999", "AB")
    assert out["total_population"] == 4_200_000.0
    assert freshness["statcan_census"].startswith("static_reference:sqlite:province_aggregate:")
