# ClearSite

ClearSite translates complex data center proposals into transparent, auditable community impact assessments.

It is a full-stack application for municipalities, planners, and residents evaluating proposed Canadian data centers. The system combines deterministic calculators, public-data lookups, local ML models, and optional LLM-assisted memo generation to answer practical questions such as:

- How much grid strain could this facility add?
- How much water would it consume relative to local supply?
- What are the likely economic upsides and limits?
- How well does the site fit community and environmental context?
- What policy recommendation and permit conditions should council consider?

## Why ClearSite Exists

Data center proposals are dense, technical, and difficult for non-specialists to audit. At the same time, the consequences are local and concrete: power demand, water use, emissions, noise, infrastructure pressure, and political opposition.

ClearSite turns a proposal into a structured assessment with:

- environmental impact metrics
- economic and fiscal estimates
- sociological and community-fit signals
- grid-strain probability modeling
- deterministic policy recommendations
- memo-ready council language with verification and fallback behavior

The goal is not to let an LLM invent decisions. The goal is to make the decision process legible, grounded, and faster.

## What The Product Does

Typical workflow:

1. A user enters proposal fields manually or uploads a proposal PDF.
2. The backend geocodes the site and pulls contextual public data.
3. Deterministic calculators estimate carbon, water, jobs, fiscal impact, and community pressure.
4. ML models add site-fit and grid-strain signals.
5. A deterministic policy engine selects a recommendation and clause set.
6. An optional Railtracks workflow generates memo content and validates it against structured evidence.

In the frontend, that becomes an interactive dashboard with scorecards, maps, risk summaries, and memo-generation flows.

## Current Stack

- Frontend: Next.js 16, React 19, TypeScript, Tailwind, Leaflet
- Backend: FastAPI, Python, Pydantic Settings
- ML: XGBoost-style grid-strain model, CatBoost site-fit model
- Agentic workflow: Railtracks
- Optional LLM backends: local BitNet-compatible OpenAI server or Groq
- Data sources: IESO, StatsCan, Electricity Maps, AAFC drought data, AQHI feeds, Indigenous and location context sources

## Repository Layout

```text
.
├── backend/
│   ├── calculator/        # Deterministic impact formulas
│   ├── data/              # Cached public datasets and manifests
│   ├── data_sources/      # External data fetchers and fallbacks
│   ├── ingestion/         # PDF extraction and proposal normalization
│   ├── llm/               # LLM provider integrations
│   ├── ml/                # Grid-strain and site-fit inference/training code
│   ├── orchestrator/      # Railtracks workflow, memo jobs, validators
│   ├── policy/            # Deterministic recommendation engine and clauses
│   ├── scripts/           # Data download, training, evaluation utilities
│   ├── tests/             # Backend and API tests
│   └── main.py            # FastAPI entrypoint
├── frontend/
│   ├── src/app/           # Next.js app routes and UI
│   ├── src/components/    # Reusable frontend components
│   └── src/types/         # Shared frontend types
├── docs/                  # Hackathon and evaluation artifacts
├── scripts/               # Root-level developer scripts
├── DATA_DOWNLOAD_MANUAL.md
├── AGENTS.md
└── projectoverview.md
```

## Features

- Manual structured proposal intake
- Proposal PDF extraction via local parsing with deterministic fallback
- Environmental scoring for water use, carbon, and grid pressure
- Economic scoring for jobs, tax revenue, and fiscal impact
- Sociological scoring for vulnerability, noise-zone population, and context signals
- Grid-strain prediction using ON and AB demand data
- Site-fit prediction using a CatBoost model
- Deterministic policy recommendation and clause selection
- Async memo jobs and streaming progress events
- Graceful fallback behavior when external APIs or LLMs are unavailable

## API Surface

Backend routes currently exposed by the FastAPI app:

- `GET /health`
- `GET /health/llm`
- `POST /api/assess`
- `POST /api/assess/stream`
- `POST /api/extract-proposal`
- `POST /api/impact-summary`
- `POST /api/memo-jobs`
- `GET /api/memo-jobs/{job_id}`
- `GET /api/memo-jobs/{job_id}/result`

## Setup

These instructions are written for local development on Linux/macOS first, with notes where the repo already includes Windows-oriented guidance.

### Prerequisites

Install the following before starting:

- Python 3.14
- `uv` for Python dependency management
- Node.js 20 or newer
- `pnpm`
- Git

Optional but useful:

- `jq` for inspecting JSON responses
- Playwright browser binaries for the IESO downloader fallback script
- A MapTiler API key if you want MapTiler geocoding or tiles instead of pure fallback behavior
- A Groq API key or a local BitNet-compatible server if you want LLM-backed memo generation and richer extraction

### 1. Clone The Repository

```bash
git clone <your-repo-url>
cd genai-genesis-2026
```

### 2. Install Backend Dependencies

```bash
cd backend
uv sync
cd ..
```

This creates the backend virtual environment and installs the FastAPI app, ML dependencies, tests, and developer tooling.

### 3. Install Frontend Dependencies

If `pnpm` is not already available:

```bash
corepack enable
corepack prepare pnpm@latest --activate
```

Then install frontend packages:

```bash
cd frontend
pnpm install
cd ..
```

### 4. Configure Backend Environment

Create a backend environment file from the example:

```bash
cp backend/.env.example backend/.env
```

Then edit `backend/.env` as needed.

Minimum useful variables:

```dotenv
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
STRICT_DATA_MODE=true
MODEL_PATH=./models/grid_strain_model.pkl
STATCAN_CACHE_DIR=./data/statcan_cache
```

Optional live-data and LLM variables:

```dotenv
ELECTRICITY_MAPS_API_KEY=
MAPTILER_API_KEY=

LLM_BACKEND=bitnet
BITNET_API_BASE=http://127.0.0.1:8080/v1
BITNET_MODEL=1bitLLM/bitnet_b1_58-large

# Or switch to Groq instead:
# LLM_BACKEND=groq
# GROQ_API_KEY=
# GROQ_MODEL=llama-3.3-70b-versatile
# GROQ_API_BASE=https://api.groq.com/openai/v1
```

Important behavior notes:

- Core scoring does not require an LLM.
- PDF extraction can fall back to deterministic regex parsing.
- Memo jobs can fall back to deterministic output when the LLM is unavailable.
- `STRICT_DATA_MODE=true` prevents overly permissive location fallbacks.

### 5. Configure Frontend Environment

Create `frontend/.env.local` with at least:

```dotenv
BACKEND_URL=http://127.0.0.1:8000
NEXT_PUBLIC_MAPTILER_API_KEY=
NEXT_PUBLIC_USE_MAPTILER_TILES=false
```

Important:

- The frontend currently reads `BACKEND_URL`, not `NEXT_PUBLIC_BACKEND_URL`.
- If you run the backend on a non-default port, update `BACKEND_URL` to match.
- Map tiles work with OpenStreetMap fallback even when `NEXT_PUBLIC_MAPTILER_API_KEY` is blank.

### 6. Start The Backend

From one terminal:

```bash
cd backend
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The backend will be available at:

- `http://127.0.0.1:8000`
- health check: `http://127.0.0.1:8000/health`

### 7. Start The Frontend

From a second terminal:

```bash
cd frontend
pnpm dev
```

The frontend will be available at:

- `http://localhost:3000`

### 8. Verify The App

Basic backend health:

```bash
curl -s http://127.0.0.1:8000/health
```

LLM health and configuration:

```bash
curl -s http://127.0.0.1:8000/health/llm | jq .
```

If everything is wired correctly, open:

```text
http://localhost:3000
```

## Running An Assessment

ClearSite expects a proposal payload with these minimum fields:

- `address`
- `province`
- `it_load_mw`
- `pue`
- `wue`
- `cooling_type`
- `facility_type`
- `capex_cad`
- `construction_months`
- `has_onsite_generation`
- `renewable_ppa`

Example API call:

```bash
curl -s -X POST http://127.0.0.1:8000/api/assess \
  -H 'Content-Type: application/json' \
  -d '{
    "address": "Municipal District of Greenview, Grande Prairie, Alberta",
    "province": "AB",
    "it_load_mw": 200,
    "pue": 1.5,
    "wue": 1.9,
    "cooling_type": "evaporative",
    "facility_type": "hyperscale",
    "capex_cad": 5000,
    "construction_months": 36,
    "has_onsite_generation": true,
    "renewable_ppa": false
  }' | jq .
```

For streaming progress updates:

```bash
curl -N -X POST http://127.0.0.1:8000/api/assess/stream \
  -H 'Content-Type: application/json' \
  -d '{
    "address": "Municipal District of Greenview, Grande Prairie, Alberta",
    "province": "AB",
    "it_load_mw": 200,
    "pue": 1.5,
    "wue": 1.9,
    "cooling_type": "evaporative",
    "facility_type": "hyperscale",
    "capex_cad": 5000,
    "construction_months": 36,
    "has_onsite_generation": true,
    "renewable_ppa": false
  }'
```

## PDF Proposal Extraction

Upload a proposal PDF through the frontend or directly via the API:

```bash
curl -s -X POST http://127.0.0.1:8000/api/extract-proposal \
  -F 'file=@/absolute/path/to/proposal.pdf' | jq .
```

Behavior:

- Extracts PDF text locally.
- Uses the configured LLM when available.
- Falls back to deterministic extraction when the LLM is unavailable or unsuitable.
- Returns extraction metadata so you can inspect confidence and missing fields.

## Data Setup

The repo already contains cached data and model artifacts, so you can usually start developing without rebuilding everything from scratch.

If you want to refresh public datasets locally, use the backend scripts.

### Automatic Dataset Download

```bash
cd backend
uv run python scripts/download_data.py
```

This writes fetched files into `backend/data/` and appends retrieval metadata to `backend/data/ingestion_manifest.jsonl`.

If you want the script to continue past individual download failures:

```bash
uv run python scripts/download_data.py --allow-errors
```

### Manual Data Download

If a source changes structure or blocks scripted fetches, use the manual guide:

- `DATA_DOWNLOAD_MANUAL.md`

That document includes click-by-click download steps for IESO, AESO, and StatsCan data.

### Load StatsCan Tables Into SQLite

After downloading the StatsCan ZIPs:

```bash
cd backend
uv run python scripts/load_census_to_sqlite.py \
  --db ./data/census_csd.db \
  --census-csv ./data/98-10-0001-01.zip \
  --water-csv ./data/38-10-0250-01.zip
```

## Model Training

### Retrain The Grid-Strain Model

```bash
cd backend
uv run python scripts/train_grid_model.py \
  --data-dir ./data \
  --model-out ./models/grid_strain_model.pkl
```

By design, synthetic training data is opt-in only:

```bash
uv run python scripts/train_grid_model.py \
  --data-dir ./data \
  --model-out ./models/grid_strain_model.pkl \
  --allow-synthetic
```

### Retrain The Site-Fit Model

From the repository root, using the backend virtual environment created by `uv sync`:

```bash
./backend/.venv/bin/python scripts/train_site_fit_model.py
```

This uses the site-fit training code under `backend/ml/site_fit/` and expects the training CSV to exist at `backend/data/site_fit_training_ready.csv`.

## Optional Local BitNet Setup

The backend supports OpenAI-compatible local model servers and includes helper scripts for BitNet-based local inference.

High-level flow:

1. Build or prepare a BitNet runtime outside this repo.
2. Start the local server on `127.0.0.1:8080`.
3. Point `backend/.env` at that server with `LLM_BACKEND=bitnet`.
4. Verify with `GET /health/llm`.

Preflight helper inside this repo:

```bash
cd backend
./scripts/bitnet_preflight.sh
```

Server helper inside this repo:

```bash
BITNET_HOME=../BitNet \
BITNET_MODEL_PATH=../BitNet/models/bitnet_b1_58-large/ggml-model-i2_s.gguf \
./scripts/start_bitnet_server.sh
```

Notes:

- Local OpenAI-compatible servers often support `json_object` structured output but not full `json_schema`.
- The repo includes fallback handling for that limitation.
- Keep the BitNet server bound to localhost.

See `backend/README.md` for the full BitNet runtime walkthrough.

## Optional Playwright Setup

If IESO anti-bot protections block direct downloads, install Playwright's Chromium runtime:

```bash
cd backend
uv run playwright install chromium
```

Then use:

```bash
uv run python scripts/download_ieso_playwright.py --start-year 2020 --end-year 2025 --out-dir ./data
```

## Tests And Validation

### Backend Tests

```bash
cd backend
uv run python -m pytest -q
```

### Frontend Lint

```bash
cd frontend
pnpm lint
```

### Frontend Production Build

```bash
cd frontend
pnpm build
```

### Railtracks Evaluation

```bash
cd backend
uv run python scripts/evaluate_railtracks_workflow.py --skip-judge
```

Output artifacts are written to `docs/results/`.

## Common Development Notes

- Backend default host/port in the actual frontend integration is `http://127.0.0.1:8000`.
- If you change the backend port, update `frontend/.env.local` accordingly.
- The backend requires Python 3.14 according to `backend/pyproject.toml`.
- Core scoring is designed to keep working when an external API is slow or unavailable.
- MapTiler is optional. OpenStreetMap fallback is supported.
- Memo generation and proposal extraction are more capable with a configured LLM, but the platform is still usable without one.

## Additional Documentation

- `backend/README.md`: backend-specific setup, BitNet notes, async memo jobs, and scripts
- `frontend/README.md`: frontend-specific development notes
- `projectoverview.md`: concise product and judging overview
- `DATA_DOWNLOAD_MANUAL.md`: manual dataset retrieval instructions
- `AGENTS.md`: repo-specific engineering and product notes

## License

MIT
- Sociological context: community vulnerability, noise exposure, advisory context
- ML signal: grid strain probability from an XGBoost model
- Deterministic policy recommendation + clause selection
- Grounded memo and negotiation playbook

## Why it matters
Municipal decisions on large data centres can lock in infrastructure pressure for years. ClearSite turns complex technical assumptions into transparent, auditable outputs that non-technical stakeholders can understand.

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
