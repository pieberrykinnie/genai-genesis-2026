# DataSite Impact Analyzer v2
## Full Project Specification
## GenAI Genesis 2026 | Google Sustainability Track | Railtracks-first build

> This spec supersedes the old Groq-centered Section 6.
> The LLM no longer decides policy.
> Policy selection is deterministic.
> Railtracks is used for orchestration, typed extraction, typed memo writing, validation, tracing, and streaming.

---

## 0. Project Summary

**What it is:** A council-facing impact analysis engine for proposed data centres in Canada.
It combines real Canadian public data, deterministic impact calculations, and two small ML models to help municipal planners evaluate whether a proposal is likely to strain local infrastructure or deliver weak public value.

**Core principle:** High-stakes decisions should not be made by an unconstrained LLM.
The LLM is only allowed to:
1. extract proposal fields into a strict schema
2. explain evidence in plain language
3. format already-selected policy clauses into a readable memo

**What the app does:**
- Accept a typed proposal or uploaded proposal PDF
- Pull real location, grid, water, and community context
- Compute environmental, economic, and sociological impacts
- Run two ML models:
  - Grid strain model
  - Site fit / precedent model
- Run a deterministic policy engine that selects clause IDs and a council recommendation
- Use Railtracks agents to generate a grounded memo with zero policy freedom

**Demo pitch:** Councils are tired of vague job promises and black-box AI. DataSite shows the numbers, the risk bands, the precedent score, the exact conditions the developer should accept, and a plain-language memo for council review.

---

## 1. Non-negotiable Design Rules

1. The LLM must never choose policy clauses.
2. The LLM must never invent numbers.
3. All recommendations must come from deterministic rules or ML outputs.
4. Every memo section must be generated from an evidence pack.
5. Every memo must pass a post-generation validator before return.
6. Keep the feature set small and real-data-heavy.
7. Do not use npm. Use pnpm only.

---

## 2. Tech Stack

```text
Frontend:   TypeScript + Next.js 16.1.6 + Tailwind v4 + pnpm 10.32.1
Backend:    Python 3.14 + FastAPI 0.135 + uv 0.10.10
Orchestration: Railtracks
ML:         XGBoost + CatBoost
Geo:        MapTiler API
LLM:        Railtracks provider abstraction
Storage:    SQLite for cached public data + local model artifacts
```

### LLM provider policy
Use Railtracks as the LLM orchestration layer.
Provider can be chosen by env var.
Recommended order:
1. Gemini through Railtracks
2. OpenAI through Railtracks
3. Anthropic through Railtracks
4. Portkey through Railtracks
5. Ollama local fallback

Do not hardcode Groq into the architecture.
Keep provider selection in one factory file.

---

## 3. High-Level Architecture

```text
Input (form or PDF)
    ↓
Railtracks Proposal Extraction Agent (structured output only, optional if PDF)
    ↓
Data join layer (MapTiler + StatsCan + grid + water + climate + Indigenous context)
    ↓
Deterministic calculation engine
    ↓
ML Model A: Grid Strain Probability
ML Model B: Site Fit / Precedent Probability
    ↓
Deterministic policy engine
    ↓
Railtracks Memo Writer Agent (structured output only)
    ↓
Deterministic memo validator
    ↓
JSON response + dashboard + exportable memo
```

### Why Railtracks belongs here
Railtracks is not just a wrapper around one LLM call.
Use it for:
- typed extraction with `output_schema`
- typed memo generation with `output_schema`
- validation loop
- tool/function nodes for deterministic steps
- session tracing and local visualization
- streaming progress via session broadcast callback

---

## 4. User Flow

### 4.1 Input modes

#### A. Typed form
City council enters:
- address
- province
- city
- latitude
- longitude
- facility_size_sqft
- projected_mw_load
- cooling_type
- jobs_promised
- water_intake_lps
- estimated_capital_cost_cad
- annual_property_tax_cad
- facility_type
- pue
- wue
- construction_months
- optional notes

#### B. Proposal PDF upload
Pipeline:
1. extract PDF text with `pypdf` or similar
2. send raw text to Railtracks extraction agent
3. agent returns a `ProposalInput` Pydantic object
4. council user reviews and edits extracted fields before assessment

### 4.2 User-facing result
The dashboard shows:
- composite RAG score
- environmental scorecard
- economic scorecard
- sociological scorecard
- grid strain probability
- site fit probability
- selected clause IDs
- final recommendation
- grounded memo

---

## 5. API Contract

### 5.1 Primary endpoint

```http
POST /api/assess
Content-Type: application/json
```

### 5.2 Optional PDF endpoint

```http
POST /api/extract-proposal
Content-Type: multipart/form-data
```

### 5.3 Streaming endpoint

```http
POST /api/assess/stream
```

Use existing SSE pattern, but the progress messages should be driven by Railtracks session broadcasts.

Example stages:

```json
{"stage": "proposal_extraction", "pct": 10}
{"stage": "geocoding", "pct": 20}
{"stage": "fetching_public_data", "pct": 35}
{"stage": "running_calculations", "pct": 50}
{"stage": "running_grid_model", "pct": 62}
{"stage": "running_site_fit_model", "pct": 72}
{"stage": "selecting_policy", "pct": 82}
{"stage": "writing_memo", "pct": 92}
{"stage": "validating_memo", "pct": 97}
{"stage": "complete", "pct": 100, "result": {...}}
```

---

## 6. Core Data Models

```python
from pydantic import BaseModel
from typing import Literal
from datetime import datetime

RagScore = Literal["green", "amber", "red"]
Recommendation = Literal["approve", "approve_with_conditions", "defer", "reject"]


class ProposalInput(BaseModel):
    address: str | None = None
    province: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    facility_size_sqft: float | None = None
    projected_mw_load: float | None = None
    cooling_type: str | None = None
    facility_type: str | None = None
    pue: float | None = None
    wue: float | None = None

    jobs_promised: int | None = None
    water_intake_lps: float | None = None
    estimated_capital_cost_cad: float | None = None
    annual_property_tax_cad: float | None = None
    construction_months: int | None = None

    notes: str | None = None


class GridStrainPrediction(BaseModel):
    strain_probability: float
    rate_increase_probability: float
    predicted_strain_level: str
    confidence: float
    model_version: str
    top_features: list[dict]


class SiteFitPrediction(BaseModel):
    site_fit_probability: float
    site_fit_band: str
    confidence: float
    model_version: str
    top_features: list[dict]
    nearest_similar_sites: list[dict]


class PolicyDecision(BaseModel):
    recommendation: Recommendation
    triggered_rules: list[str]
    selected_clause_ids: list[str]
    policy_summary: str


class CouncilMemo(BaseModel):
    executive_summary: str
    environmental_section: str
    economic_section: str
    sociological_section: str
    recommendation_section: str
    clause_narratives: list[str]
    disclaimer: str


class ImpactAssessment(BaseModel):
    proposal_id: str
    timestamp: datetime
    location: dict
    data_freshness: dict[str, str]

    proposal: ProposalInput
    environmental: dict
    economic: dict
    sociological: dict

    grid_strain: GridStrainPrediction
    site_fit: SiteFitPrediction
    overall_score: dict
    policy_decision: PolicyDecision
    memo: CouncilMemo

    evidence_pack: dict
    methodology: dict
```

---

## 7. Public Data Sources

Use the current spec sources where they already work, and add the site-fit sources below.

### 7.1 Existing public data from current implementation
Keep these:
- MapTiler for geocoding and map display
- Electricity Maps or fallback provincial carbon table
- IESO and AESO hourly historical demand for grid model training
- Statistics Canada census profile data
- Statistics Canada municipal water use table
- Indigenous Services Canada / Crown-Indigenous Relations data
- Canadian drought monitor or static fallback table

### 7.2 New data for Site Fit model

#### Positive labels
1. **IM3 Open Source Data Center Atlas (US)**
   - Use CSV or GeoPackage
   - Includes existing U.S. data-center locations and area in square feet
2. **OpenStreetMap data centre tags (Canada)**
   - `telecom=data_center`
   - `building=data_center`

#### Negative labels
Create these yourself.
Simplest hackathon method:
- sample random points in urban or business-heavy census subdivisions
- exclude any point within 10 km of a positive site
- keep province distribution roughly balanced

#### Site features to join
Use a small set only:
- province
- climate normals or average temperature
- cooling degree days
- provincial grid carbon intensity
- water stress score
- drought score
- population density
- business density
- distance to nearest existing data centre
- count of existing data centres within 100 km

#### Optional nice-to-have features
- distance to nearest major city
- local tech workforce proxy
- municipal tax proxy

---

## 8. Deterministic Calculation Engine

The deterministic engine remains the backbone.
It computes measurable quantities from formulas and public data.

### 8.1 Environmental
Compute:
- annual electricity demand
- annual carbon emissions
- direct water use
- indirect water use
- total water use
- percent of municipal daily supply
- total power draw
- percent of provincial surplus consumed

Example:

```python
annual_mwh = projected_mw_load * 8760 * pue
annual_co2e_tonnes = annual_mwh * carbon_intensity_tonnes_per_mwh
```

### 8.2 Economic
Compute:
- direct construction jobs
- direct permanent jobs
- tax revenue estimates
- infrastructure burden estimates
- household rate impact proxy
- jobs promised vs expected jobs gap

### 8.3 Sociological
Compute:
- nearest First Nation distance
- Indigenous consultation flag
- community vulnerability index
- population density exposure
- noise-zone population proxy
- local hiring feasibility proxy

### 8.4 RAG scoring
Each pillar gets a RAG score.
The overall score is deterministic.
Do not ask the LLM to infer RAG colors.

---

## 9. ML Model A: Grid Strain Predictor

Keep the existing model, but make it a clean standalone module.

### 9.1 Task
Predict the probability that the proposed new load will push the provincial grid into a strain event.

### 9.2 Model
Use `XGBClassifier`.

### 9.3 Training data
Use the current plan:
- IESO hourly demand data
- AESO hourly demand / price data

### 9.4 Output
Return:
- `strain_probability`
- `rate_increase_probability`
- `predicted_strain_level`
- `confidence`
- `top_features`

### 9.5 Notes
Do not let this model choose final policy.
It is one signal into the policy engine.

---

## 10. ML Model B: Site Fit / Precedent Model

This is the new ML model.
It makes the app feel much more like a real AI system without faking policy reasoning.

### 10.1 What it predicts
**Question:** Does this proposed location look like places where data centres are actually built?

This is not a moral judgment.
This is a precedent / market-likelihood signal.

### 10.2 Model type
Primary choice:
```python
CatBoostClassifier
```

Why:
- strong on mixed tabular data
- handles missing numeric values
- handles categorical features well
- good fit for `province`, `city`, and incomplete public data

Fallback if needed:
```python
HistGradientBoostingClassifier
```

### 10.3 Labels
- Positive label `1`: known existing data centre site
- Negative label `0`: matched non-data-centre point

### 10.4 Training table
Each row is a site candidate.

Features:
```text
province
annual_mean_temp_c
cooling_degree_days
grid_carbon_intensity
water_stress_score
drought_score
population_density
business_density
distance_to_nearest_dc_km
dc_count_within_100km
```

Target:
```text
label ∈ {0,1}
```

### 10.5 Inference output
Return:
- `site_fit_probability`
- `site_fit_band`
- `confidence`
- `top_features`
- `nearest_similar_sites`

Band rule:
```python
if p < 0.35:
    band = "low"
elif p < 0.65:
    band = "moderate"
else:
    band = "high"
```

### 10.6 Why this model is useful
It gives councils one extra grounded question:
- Is this proposal being dropped into a location that looks structurally plausible for a data-centre market?

Low site-fit does **not** mean automatic rejection.
It means more due diligence and stronger conditions.

---

## 11. Policy Engine

This replaces the old free-form LLM negotiation logic.

### 11.1 Clause catalog
Maintain a fixed catalog of clause IDs.
Example IDs:

```python
CLAUSE_CATALOG = {
    "GRID_COST_SHARE": "Developer funds or reimburses required grid upgrades.",
    "PEAK_CURTAILMENT_PLAN": "Developer provides a curtailment or demand-response plan for peak events.",
    "WATER_USE_CAP": "Daily water withdrawal cap with audited reporting.",
    "WATER_REPLENISHMENT": "Water replenishment commitment tied to annual usage.",
    "NOISE_ABATEMENT": "Verified acoustic mitigation and setback requirements.",
    "LOCAL_HIRING_PLAN": "Local hiring and training targets with annual reporting.",
    "INDIGENOUS_CONSULTATION": "Formal Indigenous consultation and benefit-sharing plan.",
    "ANNUAL_TRANSPARENCY_REPORT": "Annual public disclosure of power, water, jobs, and taxes.",
    "SUBSIDY_CLAWBACK": "Tax incentives clawed back if audited conditions are missed.",
    "DEVELOPER_FUNDED_DUE_DILIGENCE": "Developer funds independent third-party technical review."
}
```

### 11.2 Rule engine
The policy engine is plain Python.
It consumes deterministic metrics + ML outputs.

Example:

```python
def select_policy(evidence) -> PolicyDecision:
    clauses = []
    rules = []

    if evidence["grid_strain"]["strain_probability"] >= 0.55:
        clauses += ["GRID_COST_SHARE", "PEAK_CURTAILMENT_PLAN", "ANNUAL_TRANSPARENCY_REPORT"]
        rules.append("high_grid_strain")

    if evidence["environmental"]["water_score"] == "red" or evidence["environmental"]["pct_of_municipal_daily_supply"] >= 10:
        clauses += ["WATER_USE_CAP", "WATER_REPLENISHMENT", "SUBSIDY_CLAWBACK"]
        rules.append("high_water_burden")

    if evidence["sociological"]["indigenous_flag"]:
        clauses += ["INDIGENOUS_CONSULTATION", "ANNUAL_TRANSPARENCY_REPORT"]
        rules.append("indigenous_consultation_required")

    if evidence["site_fit"]["site_fit_probability"] < 0.35:
        clauses += ["DEVELOPER_FUNDED_DUE_DILIGENCE"]
        rules.append("low_site_fit")

    if evidence["sociological"]["residential_population_in_noise_zone"] > 1000:
        clauses += ["NOISE_ABATEMENT"]
        rules.append("noise_exposure")

    if evidence["economic"]["jobs_gap"] > 0:
        clauses += ["LOCAL_HIRING_PLAN"]
        rules.append("jobs_promise_gap")

    clauses = sorted(set(clauses))

    # Recommendation
    red_count = sum([
        evidence["environmental"]["carbon_score"] == "red",
        evidence["environmental"]["water_score"] == "red",
        evidence["environmental"]["grid_score"] == "red",
        evidence["sociological"]["sociological_score"] == "red",
        evidence["grid_strain"]["strain_probability"] >= 0.75,
        evidence["site_fit"]["site_fit_probability"] < 0.20,
    ])

    if red_count >= 4:
        recommendation = "reject"
    elif red_count >= 2:
        recommendation = "defer"
    elif len(clauses) > 0:
        recommendation = "approve_with_conditions"
    else:
        recommendation = "approve"

    return PolicyDecision(
        recommendation=recommendation,
        triggered_rules=rules,
        selected_clause_ids=clauses,
        policy_summary=f"{recommendation} based on {len(rules)} triggered rule(s)."
    )
```

### 11.3 Important rule
The LLM can rephrase a clause.
The LLM cannot invent a new clause ID.

---

## 12. Railtracks LLM Layer

This is the major architecture change.

### 12.1 Agent 1: Proposal Extraction Agent
Only used when PDF or raw proposal text is supplied.

```python
import railtracks as rt

ProposalExtractionAgent = rt.agent_node(
    name="ProposalExtractionAgent",
    llm=make_railtracks_llm(),
    output_schema=ProposalInput,
    system_message=(
        "Extract proposal fields into the schema. "
        "Use null for missing values. "
        "Do not infer missing numeric values. "
        "Do not perform policy analysis."
    )
)
```

### 12.2 Agent 2: Memo Writer Agent
Receives only:
- proposal summary
- evidence pack
- policy decision
- clause catalog subset

Returns only a structured memo object.

```python
class MemoInput(BaseModel):
    proposal: ProposalInput
    evidence_pack: dict
    policy_decision: PolicyDecision
    clause_text: dict[str, str]


MemoWriterAgent = rt.agent_node(
    name="MemoWriterAgent",
    llm=make_railtracks_llm(),
    output_schema=CouncilMemo,
    system_message=(
        "You are a municipal planning memo writer. "
        "Use only the evidence pack and selected clause IDs. "
        "Do not invent numbers. "
        "Do not invent policy clauses. "
        "Explain trade-offs in plain language for council members."
    )
)
```

### 12.3 Validation loop
After memo generation, run a deterministic validator.
If validation fails, rerun the memo writer one time with explicit correction notes.

Validator checks:
- no clause outside `selected_clause_ids`
- no number mentioned that is absent from evidence pack
- recommendation text matches deterministic recommendation
- no unsupported factual claims

### 12.4 Railtracks session flow

```python
@rt.session(name="assess_proposal")
async def assess_flow(user_payload: dict):
    await rt.broadcast("proposal_ingest")

    proposal = await ingest_or_extract(user_payload)

    await rt.broadcast("fetching_public_data")
    public_context = fetch_public_context(proposal)

    await rt.broadcast("running_calculations")
    evidence = run_calculations(proposal, public_context)

    await rt.broadcast("running_grid_model")
    evidence["grid_strain"] = predict_grid_strain(proposal, public_context)

    await rt.broadcast("running_site_fit_model")
    evidence["site_fit"] = predict_site_fit(proposal, public_context)

    await rt.broadcast("selecting_policy")
    policy = select_policy(evidence)

    await rt.broadcast("writing_memo")
    memo = await rt.call(
        MemoWriterAgent,
        MemoInput(
            proposal=proposal,
            evidence_pack=evidence,
            policy_decision=policy,
            clause_text={k: CLAUSE_CATALOG[k] for k in policy.selected_clause_ids},
        )
    )

    await rt.broadcast("validating_memo")
    ok, errors = validate_memo(memo, evidence, policy)
    if not ok:
        memo = await rt.call(
            MemoWriterAgent,
            MemoInput(
                proposal=proposal,
                evidence_pack={**evidence, "validation_errors": errors},
                policy_decision=policy,
                clause_text={k: CLAUSE_CATALOG[k] for k in policy.selected_clause_ids},
            )
        )

    return build_response(proposal, evidence, policy, memo)
```

### 12.5 What the LLM is NOT allowed to do
- choose recommendation
- choose clauses
- estimate numbers not in evidence
- perform legal analysis beyond restating clause text

---

## 13. Memo Validator

Create a plain Python validator.
This is not an LLM.

Checks:
1. memo fields are present and non-empty
2. recommendation language matches deterministic recommendation
3. clause count equals or is less than selected clauses
4. no clause name outside selected clause IDs
5. every numeric token is linked to evidence pack values within tolerance

If validator fails twice, return the deterministic outputs plus a minimal fallback memo template.

---

## 14. Repository Structure

```text
/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx
│   │   │   ├── results/page.tsx
│   │   │   └── api/
│   │   ├── components/
│   │   │   ├── ProposalForm.tsx
│   │   │   ├── ProposalUpload.tsx
│   │   │   ├── ImpactDashboard.tsx
│   │   │   ├── ScoreCard.tsx
│   │   │   ├── MapView.tsx
│   │   │   └── MemoViewer.tsx
│   │   └── types/
│   │       └── assessment.ts
│   ├── package.json
│   └── pnpm-lock.yaml
│
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── orchestrator/
│   │   ├── railtracks_flow.py
│   │   ├── llm_factory.py
│   │   ├── agents.py
│   │   └── validators.py
│   ├── calculator/
│   │   ├── environmental.py
│   │   ├── economic.py
│   │   ├── sociological.py
│   │   └── scoring.py
│   ├── policy/
│   │   ├── clause_catalog.py
│   │   └── engine.py
│   ├── data_sources/
│   │   ├── electricity_maps.py
│   │   ├── statcan.py
│   │   ├── indigenous.py
│   │   ├── drought.py
│   │   ├── climate.py
│   │   ├── water_risk.py
│   │   └── site_fit_data.py
│   ├── ml/
│   │   ├── grid_strain/
│   │   │   ├── train.py
│   │   │   └── predict.py
│   │   ├── site_fit/
│   │   │   ├── train.py
│   │   │   ├── predict.py
│   │   │   └── features.py
│   │   └── common/
│   │       └── utils.py
│   ├── ingestion/
│   │   ├── pdf_extract.py
│   │   └── proposal_normalize.py
│   └── pyproject.toml
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── census_csd.db
│   ├── reserves_centroids.csv
│   ├── im3_dc_atlas.csv
│   ├── canada_osm_dc.csv
│   └── site_fit_training.parquet
│
├── models/
│   ├── grid_strain_model.pkl
│   └── site_fit_model.cbm
│
└── scripts/
    ├── download_data.py
    ├── build_site_fit_dataset.py
    ├── train_grid_model.py
    ├── train_site_fit_model.py
    └── load_census_to_sqlite.py
```

---

## 15. Environment Variables

```bash
# Core
MAPTILER_API_KEY=...
ELECTRICITY_MAPS_API_KEY=...

# Railtracks provider selection
LLM_PROVIDER=gemini

# Optional provider keys. Use only the one your team chooses.
GEMINI_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
PORTKEY_API_KEY=...
PORTKEY_VIRTUAL_KEY=...
OLLAMA_BASE_URL=http://localhost:11434

# App
STATCAN_CACHE_DIR=./data/statcan_cache
GRID_MODEL_PATH=./models/grid_strain_model.pkl
SITE_FIT_MODEL_PATH=./models/site_fit_model.cbm
RAILTRACKS_SAVE_STATE=true
```

---

## 16. Pre-Hackathon Checklist

### Data
- [ ] Download IESO hourly demand data 2020 to 2024
- [ ] Download AESO hourly data 2020 to 2024
- [ ] Download StatsCan census profile and load into SQLite
- [ ] Download StatsCan municipal water use table
- [ ] Download Indigenous reserve polygons or centroids
- [ ] Build `canada_osm_dc.csv`
- [ ] Download IM3 Open Source Data Center Atlas
- [ ] Build random negative site sample CSV
- [ ] Build site-fit training parquet

### Models
- [ ] Train `grid_strain_model.pkl`
- [ ] Train `site_fit_model.cbm`
- [ ] Save model metrics for README

### LLM / Railtracks
- [ ] Choose provider and test Railtracks factory
- [ ] Implement ProposalExtractionAgent
- [ ] Implement MemoWriterAgent
- [ ] Implement memo validator
- [ ] Enable Railtracks session save state
- [ ] Wire Railtracks broadcasts to SSE

### Demo
Prepare two precomputed cases:
1. Bad case with high water or grid burden
2. Better case with clean grid and better site-fit

---

## 17. What to Say to Judges

### Where the AI is
"We have four AI layers. First, a Railtracks extraction agent turns a proposal PDF into a typed schema. Second, an XGBoost model predicts grid strain risk from real historical grid data. Third, a CatBoost model scores whether the location looks like historically plausible data-centre siting. Fourth, a Railtracks memo writer turns those computed results into a readable council memo. The LLM never decides policy."

### Why this is safer than generic agent prompting
"The recommendation and clause selection are deterministic. The LLM only explains and formats. That makes the system auditable and much safer for municipal planning."

### Why Railtracks matters
"Railtracks gives us typed agent outputs, validation loops, run tracing, and a provider-agnostic LLM layer. We can show the execution graph, not just a black-box answer."

---

## 18. Migration Notes from the Old Spec

1. Delete the old free-form `Groq` report generation pattern.
2. Remove any code that extracts clause bullets by parsing numbered prose.
3. Add `site_fit_model` as the second ML model.
4. Add a deterministic policy engine.
5. Use Railtracks for extraction, memo writing, validation, and tracing.
6. Keep deterministic formulas and the grid-strain model.
7. Keep the frontend concept, but rename `ReportViewer` to `MemoViewer` if helpful.

---

## 19. Minimum Viable Build Order

1. Typed form input only
2. Deterministic calculators
3. Grid strain model
4. Policy engine
5. Railtracks memo writer
6. Site-fit model
7. Optional PDF extraction
8. Optional validation rerun

Build in that order.
Do not start with multi-agent complexity.
Start with one clean end-to-end pipeline.

---

*End of spec.*
