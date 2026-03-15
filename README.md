# DataSite Impact Analyzer

AI decision support for Canadian municipalities reviewing new data centre proposals.

Built with railtracks.

## What this project is
DataSite helps councils and residents understand the trade-offs of proposed data centres before approval.

For a proposal, it returns:
- Environmental impact: carbon, water demand, grid pressure
- Economic impact: jobs, tax revenue, net fiscal impact
- Sociological context: community vulnerability, noise exposure, advisory context
- ML signal: grid strain probability from an XGBoost model
- Deterministic policy recommendation + clause selection
- Grounded memo and negotiation playbook

## Why it matters
Municipal decisions on large data centres can lock in infrastructure pressure for years. DataSite turns complex technical assumptions into transparent, auditable outputs that non-technical stakeholders can understand.

## Product flow
1. Proposal Intake (manual form or PDF extraction)
2. Location Context (map, noise radius, local pressure interpretation)
3. Impact Results (plain-language implications)
4. Decision Brief (citizen/councillor actions + memo)

## Architecture
- Frontend: Next.js, TypeScript, Tailwind, Leaflet
- Backend: FastAPI, deterministic calculators, ML inference
- Orchestration: Railtracks workflow (`council_decision_workflow`)
- Model artifact: `backend/models/grid_strain_model.pkl`
- Local data cache/storage: SQLite + local files

Assessment sequence:
1. Geocode address
2. Fetch public context data
3. Run deterministic calculations
4. Run grid model inference
5. Select deterministic policy
6. Run Railtracks memo workflow + verifier

## Repository structure
```text
genai-genesis-2026/
  backend/
    data_sources/
    ingestion/
    orchestrator/
    scripts/
    tests/
    main.py
  frontend/
    src/app/
    src/components/
    src/types/
  docs/
    results/
  projectspec.md
  projectoverview.md
  DATA_DOWNLOAD_MANUAL.md
```

## API
- `GET /health`
- `POST /api/assess`
- `POST /api/assess/stream` (SSE)
- `POST /api/memo-jobs`
- `GET /api/memo-jobs/{job_id}`
- `GET /api/memo-jobs/{job_id}/result`
- `POST /api/extract-proposal`

## Prerequisites
- Python 3.11+ (managed via `uv`)
- Node 20+ and `pnpm`
- Git

## Quickstart
From repo root, run backend and frontend in separate terminals.

### 1) Backend
```bash
cd backend
uv sync
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8010
```

### 2) Frontend
```bash
cd frontend
pnpm install --package-import-method=copy
pnpm dev
```

App URLs:
- Frontend: `http://localhost:3000`
- Backend: `http://127.0.0.1:8010`

## Environment variables

### Backend (`backend/.env`)
```bash
MAPTILER_API_KEY=
NOMINATIM_USER_AGENT=genai-genesis-2026-local-dev/1.0
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_API_BASE=https://api.groq.com/openai/v1
STRICT_DATA_MODE=true
MODEL_PATH=./models/grid_strain_model.pkl
```

### Frontend (`frontend/.env.local`)
```bash
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8010
NEXT_PUBLIC_MAPTILER_API_KEY=
NEXT_PUBLIC_USE_MAPTILER_TILES=false
```

Notes:
- If MapTiler tiles fail, the map falls back to OpenStreetMap tiles.
- Geocoding uses MapTiler first, then Nominatim fallback.

## Data and model workflow
### Download / refresh data
```bash
cd backend
uv run python scripts/download_data.py
```

### Load StatsCan CSVs to SQLite
```bash
uv run python scripts/load_census_to_sqlite.py --db ./data/census_csd.db --census-csv ./data/98-10-0001-01.zip --water-csv ./data/38-10-0250-01.zip
```

### Train grid model
```bash
uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl
```

Use synthetic mode only when explicitly needed:
```bash
uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl --allow-synthetic
```

## Validation
### Backend tests
```bash
cd backend
uv run python -m pytest -q
```

### Frontend checks
```bash
cd frontend
pnpm lint
pnpm build
```

### Railtracks evaluation artifacts
```bash
cd backend
uv run python scripts/evaluate_railtracks_workflow.py --skip-judge
```

Output files:
- `docs/results/railtracks_eval_result.json`
- `docs/results/railtracks_eval_summary.md`

## Railtracks usage in this project
Railtracks is used for substantive orchestration and quality control:
- Session workflow: `council_decision_workflow`
- Memo generation agent
- Memo grounding verifier agent
- Single repair pass on verifier failure
- Evaluation harness to produce reproducible workflow artifacts

## Demo scenarios
For a convincing demo run these presets in the UI:
- Baseline AB
- Balanced QC
- Beacon-like High Load

Then compare directional differences in:
- water-share pressure
- grid strain probability
- recommendation strictness

## Additional docs
- Project spec: `projectspec.md`
- Project overview + judging mapping: `projectoverview.md`
- Data download guide: `DATA_DOWNLOAD_MANUAL.md`
- Backend advanced setup (BitNet, memo jobs, scripts): `backend/README.md`

## License
MIT
