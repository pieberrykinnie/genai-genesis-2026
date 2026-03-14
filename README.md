# DataSite Impact Analyzer

AI decision support for Canadian city councils reviewing new data centre proposals.

Built with railtracks.

## Why This Matters

Municipal councils are being asked to approve large data centre projects with incomplete evidence. DataSite gives councils a defensible, transparent assessment before they negotiate or vote.

The system combines:
- Real Canadian public data
- Deterministic impact formulas
- A trained XGBoost grid-strain model
- A Railtracks memo workflow with grounding checks

## What The App Delivers

For each proposal, DataSite returns:
- Environmental impact: carbon, water draw, grid pressure
- Economic impact: jobs, tax, net fiscal effect
- Sociological impact: community vulnerability, Indigenous context, noise exposure
- ML prediction: grid strain probability + top model features
- Policy output: recommendation and selected negotiation clauses
- Decision memo: grounded council-ready narrative
- Data freshness: per-source status (`live`, `cached`, `static_reference`, `unavailable:*`)

## Demo-Ready User Flow

1. Proposal Intake
2. Location Context (interactive map + site marker + estimated noise radius)
3. Impact Results (plain-language summaries)
4. Decision Brief (playbook + evidence freshness)

## Architecture

- Frontend: Next.js + TypeScript + Tailwind + Leaflet (OSM tiles)
- Backend: FastAPI + deterministic calculators + ML inference
- Orchestration: Railtracks session workflow
- Model: `xgboost_v1_ieso_aeso_2024`
- Storage: local SQLite/cache for public data lookups

Assessment order:
1. Geocode
2. Fetch public data
3. Run deterministic calculations
4. Run ML inference
5. Select deterministic policy
6. Run Railtracks memo + verifier + one repair pass

## API

- `GET /health`
- `POST /api/assess`
- `POST /api/assess/stream` (SSE)

SSE includes a visible Railtracks stage:
- `proposal_ingest`
- `fetching_public_data`
- `running_calculations`
- `running_grid_model`
- `running_site_fit_model`
- `selecting_policy`
- `railtracks_workflow`
- `writing_memo`
- `complete`

## Quickstart

From repo root:

```bash
cd backend
uv sync
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8010
```

In a second terminal:

```bash
cd frontend
pnpm install
pnpm dev
```

Frontend: `http://localhost:3000`
Backend: `http://127.0.0.1:8010`

## Required Environment Variables

Backend (`backend/.env`):

```bash
MAPTILER_API_KEY=
NOMINATIM_USER_AGENT=genai-genesis-2026-local-dev/1.0
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_API_BASE=https://api.groq.com/openai/v1
STRICT_DATA_MODE=true
```

Frontend (`frontend/.env.local`):

```bash
NEXT_PUBLIC_MAPTILER_API_KEY=
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8010
```

## Data + Model Commands

```bash
cd backend
uv run python scripts/download_data.py
uv run python scripts/load_census_to_sqlite.py --db ./data/census_csd.db --census-csv ./data/98-10-0001-01.zip --water-csv ./data/38-10-0250-01.zip
uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl
```

Evaluation artifacts:

```bash
uv run python scripts/evaluate_railtracks_workflow.py --skip-judge
```

Outputs:
- `docs/results/railtracks_eval_result.json`
- `docs/results/railtracks_eval_summary.md`

## Validation Commands

```bash
cd backend
uv run python -m pytest -q
uv run python scripts/evaluate_railtracks_workflow.py --skip-judge
```

## Railtracks Usage (Submission Notes)

Railtracks is used for:
- session-based orchestration (`council_decision_workflow`)
- memo generation agent
- memo grounding verifier agent
- repair pass when verifier/deterministic checks fail
- evaluation artifact generation

Current workflow evaluation scenarios pass in local run:
- AB high-load
- QC lower-risk
- malformed-address edge case

## Core Data Sources

- IESO hourly demand reports
- AESO market/system historical data
- Statistics Canada census + water use tables
- Electricity Maps (when available) with deterministic fallback
- ECCC AQHI and drought context fallbacks
- Indigenous context cache/fallback tables

## License

MIT
