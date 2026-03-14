# genai-genesis-2026

DataSite Impact Analyzer for GenAI Genesis 2026 (Google Sustainability track).
Built with railtracks.

## Quickstart

1. Install frontend dependencies:

```bash
cd frontend
pnpm install
```

2. Install backend dependencies:

```bash
cd ../backend
uv sync
```

3. Run backend:

```bash
uv run fastapi dev main.py
```

4. Run frontend:

```bash
cd ../frontend
pnpm dev
```

## Backend scripts

```bash
cd backend
uv run python scripts/download_data.py
uv run python scripts/load_census_to_sqlite.py --db ./data/census_csd.db --census-csv ./data/98-10-0001-01.csv --water-csv ./data/38-10-0250-01.csv
uv run python scripts/train_grid_model.py --data-dir ./data --model-out ./models/grid_strain_model.pkl
uv run python scripts/evaluate_railtracks_workflow.py --skip-judge
```

## Railtracks

- Workflow usage: proposal extraction, memo generation, memo grounding verification, and repair pass.
- Evaluation artifact generation:
  - `uv run python scripts/evaluate_railtracks_workflow.py` (requires Groq key for judge evaluator)
  - Outputs saved to `docs/results/`
- Viz on Windows:
  - `cmd /c "set PYTHONIOENCODING=utf-8 && uv run railtracks viz"`

## Branching

- `main`: stable submission branch
- `dev`: integration branch
- `feat/*`, `fix/*`, `docs/*`: working branches
