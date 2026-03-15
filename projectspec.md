# ClearSite - Final Project Spec

## 1. Purpose

ClearSite provides an auditable assessment of proposed data centres for Canadian municipalities.

The system must produce:
- Quantified environmental, economic, and sociological impact
- ML-based grid strain risk
- Deterministic policy recommendation and clause selection
- A grounded, readable council memo

## 2. Operating Principles

1. Deterministic scoring and policy logic are the source of truth.
2. LLM output is explanatory only and must be grounded to evidence.
3. Critical-path failures must be explicit (no fabricated substitute values).
4. Advisory data may degrade gracefully with explicit freshness markers.
5. API paths and top-level response schema remain stable.

## 3. Public Interfaces

### 3.1 Endpoints

- `GET /health`
- `POST /api/assess`
- `POST /api/assess/stream` (SSE)

### 3.2 Request Model (assess)

`DataCentreProposal` fields used in MVP:
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

### 3.3 Response Model (assess)

Top-level sections:
- `proposal_id`, `timestamp`, `location`, `data_freshness`
- `proposal`
- `environmental`
- `economic`
- `sociological`
- `grid_strain`
- `site_fit`
- `overall_score`
- `policy_decision`
- `memo`
- `report_narrative`
- `evidence_pack`
- `methodology`

Additive fields used for current release:
- `sociological.estimated_noise_radius_m`
- `methodology.railtacks_used`
- `methodology.railtacks_workflow`
- `methodology.railtacks_verification_passed`

### 3.4 SSE Stage Contract

Expected order:
1. `proposal_ingest`
2. `fetching_public_data`
3. `running_calculations`
4. `running_grid_model`
5. `running_site_fit_model`
6. `selecting_policy`
7. `railtracks_workflow`
8. `writing_memo`
9. `complete`

## 4. Data Sources

### 4.1 Core

- IESO hourly demand reports (historical training context)
- AESO market/system historical data
- Statistics Canada census profile + water use tables
- Geocoding: MapTiler primary, Nominatim fallback
- Carbon intensity: live/cached feed with deterministic fallback table
- AQHI, drought, Indigenous context: advisory enrichments with explicit availability

### 4.2 Freshness Semantics

`data_freshness` values must use explicit status prefixes:
- `live:<timestamp or source>`
- `cached:<timestamp>`
- `static_reference:<dataset_id>`
- `unavailable:<reason>`

Legacy ambiguous labels like `fallback_defaults` are not acceptable in final output.

## 5. Assessment Pipeline

Pipeline order:
1. Geocode location
2. Pull public context data
3. Run deterministic calculators
4. Run grid strain model inference
5. Run site-fit model inference
6. Select deterministic policy
7. Run Railtracks memo workflow
8. Return full assessment payload

## 6. Deterministic Calculation Scope

### 6.1 Environmental

- Annual carbon estimate
- Total water use per day
- Percent of municipal water supply
- Grid pressure indicators

### 6.2 Economic

- Permanent jobs estimate
- 10-year tax revenue estimate
- 10-year net fiscal impact

### 6.3 Sociological

- Community vulnerability proxy
- Population in noise influence zone
- Indigenous proximity/context (if available)
- AQHI baseline

## 7. ML Scope

### 7.1 Grid Model (required)

- Model artifact: `backend/models/grid_strain_model.pkl`
- Model version expected in output: `xgboost_v1_ieso_aeso_2024`
- Output fields:
  - `strain_probability`
  - `rate_increase_probability`
  - `predicted_strain_level`
  - `confidence`
  - `top_features`

Training policy:
- Default training must fail if real IESO/AESO files are missing
- Synthetic training only with explicit `--allow-synthetic`

### 7.2 Site-Fit Model (current)

- Current runtime may use heuristic-backed signal
- Must remain explicit in `model_version`
- Must not overwrite deterministic/policy authority

## 8. Railtracks Integration

Railtracks must be substantive, not checkbox-only.

### 8.1 Workflow

Session name:
- `council_decision_workflow`

Steps:
1. Context seed (`proposal`, `evidence_pack`, `policy_decision`)
2. Memo generation agent
3. Memo grounding verifier agent
4. Single repair pass on failure

### 8.2 Guardrails

Verifier checks are constrained to:
- invented numeric claims
- recommendation mismatch vs deterministic policy
- clause mismatch vs selected clauses

### 8.3 Runtime Behavior

- If memo workflow fails, deterministic scoring still returns
- Narrative may degrade to deterministic fallback memo
- Policy output must remain deterministic

## 9. Frontend Product Scope

Target audience:
- city council and public stakeholders

Required flow:
1. Proposal Intake
2. Location Context
3. Impact Results
4. Decision Brief

Location context map must show:
- site marker
- estimated noise radius overlay (when available)
- fallback marker-only mode when radius unavailable

## 10. Error Handling Policy

Critical failures (must return explicit error):
- geocoding unavailable in strict mode
- missing/corrupt required model artifact
- missing mandatory core inputs for scoring

Advisory failures (assessment may continue):
- AQHI unavailable
- drought unavailable
- Indigenous advisory source unavailable

## 11. Test and Validation Gates

### 11.1 Backend

- `uv run python -m pytest -q` passes
- `/api/assess` returns full schema
- `/api/assess/stream` reaches `complete` on happy path

### 11.2 Data + ML

- Ingestion scripts fail loudly on bad source payloads
- Training script enforces real-data default policy
- Model artifact metadata is present and readable

### 11.3 Railtracks

- `uv run python scripts/evaluate_railtracks_workflow.py --skip-judge`
- Artifacts generated:
  - `docs/results/railtracks_eval_result.json`
  - `docs/results/railtracks_eval_summary.md`

Current acceptance target:
- fixed scenario suite passes verification

## 12. Runtime Configuration

Minimum backend env vars:
- `MAPTILER_API_KEY`
- `NOMINATIM_USER_AGENT`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `GROQ_API_BASE`
- `STRICT_DATA_MODE`

Frontend env vars:
- `NEXT_PUBLIC_BACKEND_URL`
- `NEXT_PUBLIC_MAPTILER_API_KEY` (optional if OSM-only map tiles used)

## 13. Submission Checklist

1. Demo flow works end-to-end from frontend.
2. Backend tests pass locally.
3. Railtracks evaluation artifacts are present.
4. README includes keyword: `railtracks`.
5. `pyproject.toml` includes Railtracks dependency.
6. No hardcoded secrets in committed files.

## 14. Out of Scope for Final Hackathon Cut

- Full station-level pollution proximity stack
- Building-footprint population micro-modeling
- Full production data warehouse and ETL orchestration
- Automated legal drafting beyond selected clause narratives
