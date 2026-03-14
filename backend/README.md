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
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_API_BASE=https://api.groq.com/openai/v1
LLM_BACKEND=groq
LLM_TEMPERATURE=
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
  - **NOTE**: All the IESO download will fail, guaranteed. Manually download `PUB_Demand_2020.csv` to `PUB_Demand_2026.csv` to `data/` instead from this link: [https://reports-public.ieso.ca/public/Demand/](https://reports-public.ieso.ca/public/Demand/).
- `uv run python scripts/load_census_to_sqlite.py --db ./data/census_csd.db --census-csv ./data/98-10-0001-01.zip --water-csv ./data/38-10-0250-01.zip`
  - Or, if the `.zip` file names aren't extract, use those instead.
- `uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl`
