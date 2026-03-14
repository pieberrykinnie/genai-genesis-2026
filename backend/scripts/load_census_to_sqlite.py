from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
import zipfile
from pathlib import Path


def _create_schema(conn: sqlite3.Connection) -> None:
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
        """
        CREATE TABLE IF NOT EXISTS municipal_water_use (
            geo_uid TEXT PRIMARY KEY,
            daily_supply_litres REAL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_census_geo_uid ON census_profile(geo_uid)")


CENSUS_CHAR_MAP = {
    "1": "total_population",
    "560": "median_total_income",
    "5862": "unemployment_rate",
    "4201": "pct_indigenous_identity",
    "1040": "pct_low_income_lim_at",
    "6531": "pct_postsecondary_certificate",
}


GEO_UID_KEYS = ["GEO_UID", "DGUID", "GeoUID", "geo_uid"]
CHAR_KEYS = ["CHARACTERISTIC_ID", "Characteristic_ID", "characteristic_id"]
VALUE_KEYS = ["VALUE", "Value", "value"]
WATER_VALUE_KEYS = ["VALUE", "Value", "value", "Daily_Supply_Litres", "daily_supply_litres"]


def _find_key(row: dict[str, str], candidates: list[str]) -> str | None:
    for key in candidates:
        if key in row:
            return key
    return None


def _resolve_csv_path(source_path: Path, extract_dir: Path) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(f"Input file not found: {source_path}")

    if source_path.suffix.lower() != ".zip":
        return source_path

    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source_path, "r") as zf:
        csv_members = [name for name in zf.namelist() if name.lower().endswith(".csv")]
        if not csv_members:
            raise ValueError(f"No CSV file found inside ZIP: {source_path}")
        first_csv = csv_members[0]
        output_path = extract_dir / f"{source_path.stem}_{Path(first_csv).name}"
        with zf.open(first_csv) as src, output_path.open("wb") as dst:
            dst.write(src.read())
    return output_path


def load_census_csv(conn: sqlite3.Connection, csv_path: Path) -> int:
    inserted = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        # Long-format expected path (CHARACTERISTIC_ID + VALUE)
        has_long_format = any(k in fieldnames for k in CHAR_KEYS) and any(k in fieldnames for k in VALUE_KEYS)
        has_wide_format = any("Population, 2021" in c for c in fieldnames)

        if not has_long_format and not has_wide_format:
            raise ValueError(
                f"Census CSV format not recognised. "
                f"Found columns: {fieldnames}. "
                f"Expected CHARACTERISTIC_ID+VALUE (long format) or 'Population, 2021' (wide format)."
            )

        if has_long_format:
            for row in reader:
                geo_key = _find_key(row, GEO_UID_KEYS)
                char_key = _find_key(row, CHAR_KEYS)
                value_key = _find_key(row, VALUE_KEYS)
                if not geo_key or not char_key or not value_key:
                    continue

                char_id = str(row.get(char_key, "")).strip()
                if char_id not in CENSUS_CHAR_MAP:
                    continue

                geo_uid = str(row.get(geo_key, "")).strip()
                raw_val = str(row.get(value_key, "")).replace(",", "").strip()
                if not geo_uid or not raw_val:
                    continue

                try:
                    value = float(raw_val)
                except Exception:
                    continue

                conn.execute(
                    "INSERT OR REPLACE INTO census_profile (geo_uid, characteristic, value) VALUES (?, ?, ?)",
                    (geo_uid, CENSUS_CHAR_MAP[char_id], value),
                )
                inserted += 1
            return inserted

        # Wide-format fallback path (for aggregate profile tables): only total population is reliably extractable.
        pop_cols = [c for c in fieldnames if "Population, 2021" in c]
        dguid_key = "DGUID" if "DGUID" in fieldnames else _find_key({k: "" for k in fieldnames}, GEO_UID_KEYS)
        if not pop_cols or not dguid_key:
            return 0

        pop_col = pop_cols[0]
        for row in reader:
            dguid = str(row.get(dguid_key, "")).strip()
            raw_val = str(row.get(pop_col, "")).replace(",", "").strip()
            if not dguid or not raw_val:
                continue

            try:
                pop = float(raw_val)
            except Exception:
                continue

            digits = "".join(ch for ch in dguid if ch.isdigit())
            if len(digits) >= 7:
                geo_uid = digits[-7:]
            elif len(digits) >= 2:
                geo_uid = digits[-2:]
            else:
                continue

            conn.execute(
                "INSERT OR REPLACE INTO census_profile (geo_uid, characteristic, value) VALUES (?, ?, ?)",
                (geo_uid, "total_population", pop),
            )
            inserted += 1

    return inserted


def load_water_csv(conn: sqlite3.Connection, csv_path: Path) -> int:
    inserted = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        sample_row = {k: "" for k in fieldnames}
        geo_key_check = _find_key(sample_row, GEO_UID_KEYS)
        value_key_check = _find_key(sample_row, WATER_VALUE_KEYS)
        if not geo_key_check or not value_key_check:
            raise ValueError(
                f"Water CSV format not recognised. "
                f"Found columns: {fieldnames}. "
                f"Expected one of {GEO_UID_KEYS} and one of {WATER_VALUE_KEYS}."
            )

        for row in reader:
            geo_key = _find_key(row, GEO_UID_KEYS)
            value_key = _find_key(row, WATER_VALUE_KEYS)
            if not geo_key or not value_key:
                continue

            geo_uid = str(row.get(geo_key, "")).strip()
            raw_val = str(row.get(value_key, "")).replace(",", "").strip()
            if not geo_uid or not raw_val:
                continue

            try:
                val = float(raw_val)
            except Exception:
                continue

            conn.execute(
                "INSERT OR REPLACE INTO municipal_water_use (geo_uid, daily_supply_litres) VALUES (?, ?)",
                (geo_uid, val),
            )
            inserted += 1

    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="Load StatsCan CSV extracts into SQLite.")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--census-csv", type=Path, required=True, help="Path to census CSV or ZIP")
    parser.add_argument("--water-csv", type=Path, required=True, help="Path to water CSV or ZIP")
    args = parser.parse_args()

    args.db.parent.mkdir(parents=True, exist_ok=True)
    extract_dir = args.db.parent / "_extract"

    census_csv_path = _resolve_csv_path(args.census_csv, extract_dir)
    water_csv_path = _resolve_csv_path(args.water_csv, extract_dir)

    with sqlite3.connect(args.db) as conn:
        _create_schema(conn)
        census_rows = load_census_csv(conn, census_csv_path)
        water_rows = load_water_csv(conn, water_csv_path)
        conn.commit()

    print(f"Loaded census rows: {census_rows}")
    print(f"Loaded water rows: {water_rows}")
    print(f"Census source used: {census_csv_path}")
    print(f"Water source used: {water_csv_path}")
    print(f"SQLite DB: {args.db}")

    if census_rows == 0:
        print(
            "ERROR: No census rows ingested. The input file does not contain expected "
            "CSD profile vectors. Cannot proceed with demographic defaults.",
            file=sys.stderr,
        )
        sys.exit(1)
    if water_rows == 0:
        print(
            "ERROR: No water-use rows ingested. The input file does not contain expected "
            "municipal water supply data.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
