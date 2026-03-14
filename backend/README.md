# DataSite Impact Analyzer Backend

## Run

```bash
uv sync
uv run fastapi dev main.py
```

## Environment Variables

```bash
ELECTRICITY_MAPS_API_KEY=
MAPTILER_API_KEY=
GROQ_API_KEY=
STATCAN_CACHE_DIR=./data/statcan_cache
MODEL_PATH=./models/grid_strain_model.pkl
```

## Endpoints

- `GET /health`
- `POST /api/assess`
- `POST /api/assess/stream` (SSE)

## Data + ML Scripts

All scripts exit non-zero on failure (missing data, unrecognised formats, download errors).

- `uv run python scripts/download_data.py` — pass `--strict` to abort on the first download failure
- `uv run python scripts/load_census_to_sqlite.py --db ./data/census_csd.db --census-csv ./data/98-10-0001-01.zip --water-csv ./data/38-10-0250-01.zip`
- `uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl` — requires real CSVs; pass `--allow-synthetic` to train on generated data when no CSVs are found

## IESO Playwright Downloader (for anti-bot pages)

If direct script download returns HTML interstitial pages for IESO files:

1. `uv sync`
2. `uv run playwright install chromium`
3. `uv run python scripts/download_ieso_playwright.py --start-year 2020 --end-year 2025 --out-dir ./data`

Then retrain:

- `uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl`
