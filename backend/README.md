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

- `uv run python scripts/download_data.py`
- `uv run python scripts/load_census_to_sqlite.py --db ./data/census_csd.db --census-csv ./data/98-10-0001-01.csv --water-csv ./data/38-10-0250-01.csv`
- `uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl`
