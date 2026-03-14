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
NOMINATIM_USER_AGENT=genai-genesis-2026-local-dev/1.0
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_API_BASE=https://api.groq.com/openai/v1
LLM_BACKEND=groq
LLM_TEMPERATURE=
LLM_PROVIDER=groq
BITNET_API_BASE=http://127.0.0.1:8080/v1
BITNET_MODEL=bitnet-b1.58-2B-4T
STRICT_DATA_MODE=true
STATCAN_CACHE_DIR=./data/statcan_cache
MODEL_PATH=./models/grid_strain_model.pkl
```

Geocoding order is:

1. MapTiler geocoding API (if key works)
2. OpenStreetMap Nominatim fallback
3. Province centroid fallback only when `STRICT_DATA_MODE=false`

## Endpoints

- `GET /health`
- `POST /api/assess`
- `POST /api/assess/stream` (SSE)

## Data + ML Scripts

- `uv run python scripts/download_data.py`
- `uv run python scripts/download_data.py --allow-errors` (optional; default exits non-zero on failures)
- `uv run python scripts/load_census_to_sqlite.py --db ./data/census_csd.db --census-csv ./data/98-10-0001-01.zip --water-csv ./data/38-10-0250-01.zip`
- `uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl`
- `uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl --allow-synthetic` (explicit opt-in only)
- `uv run python scripts/evaluate_railtracks_workflow.py --skip-judge`
- `uv run python scripts/evaluate_railtracks_workflow.py` (requires Groq key for JudgeEvaluator)

## Railtracks Viz (Windows)

Use UTF-8 console encoding to avoid emoji encoding crashes:

```bash
cmd /c "set PYTHONIOENCODING=utf-8 && uv run railtracks viz"
```

## IESO Playwright Downloader (for anti-bot pages)

If direct script download returns HTML interstitial pages for IESO files:

1. `uv sync`
2. `uv run playwright install chromium`
3. `uv run python scripts/download_ieso_playwright.py --start-year 2020 --end-year 2025 --out-dir ./data`

Then retrain:

- `uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl`
