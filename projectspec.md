# DataSite Impact Analyzer — Full Project Specification
## GenAI Genesis 2026 | Google Sustainability Track

> **Reading guide for Claude Code:** This spec is written for the AI/data/ML developer.
> It tells you *what* to build, *which exact data sources* to use, *how* to do the ML,
> and *what* the API contracts look like. Frontend and product details are intentional
> kept minimal — focus is on backend, data pipelines, and the ML model.

---

## 0. Project Summary

**What it is:** A dynamic negotiation and impact-modeling engine for municipal governments. By combining real-time Canadian open data with predictive ML, it stress-tests proposed data centers against local infrastructure limits, generating a strict, mathematically sound Community Benefit Agreement (CBA) term sheet to protect local taxpayers.

**The pitch frame (important for demo):** The era of vague job promises and secret NDAs is over. City councils face intense public backlash over strained grids, water depletion, and spiked utility bills. DataSite shifts the power dynamic. It arms municipalities to stress-test data center proposals and generates a legally actionable Community Benefit Agreement (CBA) playbook—dictating the exact water replenishment targets, local hiring minimums, and grid infrastructure costs the developer must legally commit to before a single shovel hits the dirt.

**The three AI techniques (tell judges all three):**
1. Deterministic calculation engine — real formulas from published benchmarks applied
   to real Canadian datasets
2. XGBoost ML model — trained on real IESO/AESO historical grid data to predict
   grid strain probability from a proposed load addition
3. Groq LLM — grounded report + negotiation playbook generation, citing only
   numbers produced by layers 1 and 2


---

## 1. Tech Stack

```
Frontend:   TypeScript + Next.js 16.1.6 + Tailwind v4 + pnpm 10.32.1
Backend:    Python 3.14 + FastAPI 0.135 + uv 0.10.10
ML:         scikit-learn + XGBoost (trained offline, loaded at runtime)
Geo:        MapTiler API (geocoding + map tiles + land cover)
LLM:        Groq API (llama-3.3-70b-versatile or mixtral-8x7b)
Data:       See Section 3 for all sources
```

**Do NOT use npm. Use pnpm exclusively.**

---

## 2. User Flow & API Contract

### 2.1 User Input (Step 1)

City council enters on the frontend:

```typescript
interface DataCentreProposal {
  // Location
  address: string;           // Free text, geocoded to lat/lng via MapTiler
  province: CanadianProvince; // "ON" | "AB" | "BC" | "QC" | "MB" | "SK" | "NS" | "NB" | "NL" | "PE"

  // Technical parameters
  it_load_mw: number;        // Proposed IT load in megawatts (range: 1–500)
  pue: number;               // Power Usage Effectiveness (1.1–2.0, default 1.5)
  wue: number;               // Water Usage Effectiveness L/kWh (0.5–3.0, default 1.9)
  cooling_type: CoolingType; // "air" | "evaporative" | "liquid_immersion" | "hybrid"
  facility_type: FacilityType; // "hyperscale" | "enterprise" | "colocation"

  // Economic parameters
  capex_cad: number;         // Total capital expenditure in CAD millions
  construction_months: number; // Build timeline (12–48)

  // Optional advanced
  has_onsite_generation: boolean; // "bring your own power" model
  renewable_ppa: boolean;  // Has signed renewable power purchase agreement
}
```

### 2.2 Backend API Endpoint

**Single endpoint. Everything flows through here.**

```
POST /api/assess
Content-Type: application/json
Body: DataCentreProposal

Response: ImpactAssessment (see 2.3)
```

Expected response time: 8–15 seconds (real API calls + ML inference + LLM).
Implement SSE streaming so frontend shows progress as each pillar completes.

```
POST /api/assess/stream
```

Stream events:
```
data: {"stage": "geocoding", "pct": 5}
data: {"stage": "fetching_grid_data", "pct": 20}
data: {"stage": "fetching_census_data", "pct": 35}
data: {"stage": "running_calculations", "pct": 55}
data: {"stage": "running_ml_model", "pct": 70}
data: {"stage": "generating_report", "pct": 85}
data: {"stage": "complete", "pct": 100, "result": {...}}
```

### 2.3 API Response Schema

**Define this schema first. Everything else builds to it.**

```python
class ImpactAssessment(BaseModel):
    # Metadata
    proposal_id: str
    location: LocationData
    timestamp: datetime
    data_freshness: dict[str, str]  # source_name -> last_updated

    # Three pillars
    environmental: EnvironmentalImpact
    economic: EconomicImpact
    sociological: SociologicalImpact

    # ML output
    grid_strain: GridStrainPrediction

    # Overall
    overall_score: OverallScore       # Composite RAG score
    negotiation_playbook: list[str]   # Groq-generated action items
    report_narrative: str             # Groq-generated full narrative

    # For transparency / judging
    raw_inputs_used: dict             # All actual numbers pulled from APIs
    calculation_methodology: str      # Citation string

class LocationData(BaseModel):
    lat: float
    lng: float
    province: str
    municipality: str
    census_subdivision_id: str        # StatsCan CSD UID
    census_division_id: str

class EnvironmentalImpact(BaseModel):
    # Carbon
    annual_carbon_tonnes: float
    carbon_intensity_g_per_kwh: float  # From Electricity Maps, real-time
    carbon_score: RagScore            # "green" | "amber" | "red"

    # Water
    direct_water_litres_per_day: float
    indirect_water_litres_per_day: float
    total_water_litres_per_day: float
    pct_of_municipal_daily_supply: float
    water_score: RagScore

    # Grid
    total_power_draw_mw: float        # IT load × PUE
    provincial_capacity_mw: float
    pct_of_provincial_surplus: float
    grid_score: RagScore

class EconomicImpact(BaseModel):
    # Jobs (honest)
    direct_construction_jobs: int
    peak_construction_jobs: int       # including indirect/induced
    direct_permanent_jobs: int        # HONEST: usually 20-150
    total_permanent_jobs_with_multiplier: int

    # Tax (10-year)
    estimated_property_tax_10yr_cad: float
    estimated_total_tax_revenue_10yr_cad: float

    # Hidden cost
    estimated_household_electricity_increase_annual_cad: float
    net_fiscal_impact_10yr_cad: float  # revenue - infrastructure costs

    # Scores
    jobs_score: RagScore
    fiscal_score: RagScore

class SociologicalImpact(BaseModel):
    # Indigenous
    nearest_first_nation_km: float
    treaty_territory: str | None      # e.g. "Treaty 6 Territory"
    active_water_advisories_nearby: int
    indigenous_flag: bool             # True = requires deep consultation

    # Community vulnerability
    community_vulnerability_index: float  # 0-100, higher = more vulnerable
    median_household_income_cad: float
    unemployment_rate_pct: float
    pct_indigenous_population: float
    pct_low_income: float

    # Noise/air
    estimated_noise_radius_m: float
    residential_population_in_noise_zone: int
    air_quality_baseline: str         # AQHI rating for area

    # Skills
    local_tech_workforce_pct: float   # % of local workforce in tech occupations
    estimated_local_hiring_pct: float # % of permanent jobs fillable locally

    sociological_score: RagScore

class GridStrainPrediction(BaseModel):
    # ML model output
    strain_probability: float         # 0.0–1.0
    rate_increase_probability: float  # Probability of consumer rate increase
    predicted_strain_level: str       # "low" | "moderate" | "high" | "critical"
    confidence: float                 # Model confidence
    model_version: str                # e.g. "xgboost_v1_ieso_aeso_2024"

    # Feature importances for transparency
    top_features: list[dict]          # [{"feature": "...", "importance": 0.xx}]

class OverallScore(BaseModel):
    composite_rag: RagScore
    environmental_weight: float       # Default 0.40
    economic_weight: float            # Default 0.30
    sociological_weight: float        # Default 0.30
    summary_sentence: str             # 1-sentence plain language summary
```

---

## 3. Data Sources — Complete Reference

### 3.1 Electricity Maps API
**Purpose:** Real-time provincial grid carbon intensity (gCO2eq/kWh)
**URL:** `https://api-access.electricitymaps.com/free-tier/carbon-intensity/latest`
**Auth:** Free tier API key (sign up at electricitymaps.com/free-tier-api)
**Canadian zones:**
```python
PROVINCE_TO_ZONE = {
    "ON": "CA-ON",    # Ontario — IESO grid
    "AB": "CA-AB",    # Alberta — AESO grid
    "BC": "CA-BC",    # BC Hydro
    "QC": "CA-QC",    # Hydro-Québec
    "MB": "CA-MB",    # Manitoba Hydro
    "SK": "CA-SK",    # SaskPower
    "NB": "CA-NB",    # NB Power
    "NS": "CA-NS",    # Nova Scotia Power
    "NL": "CA-NL",    # NL Hydro
    "PE": "CA-PE",    # Maritime Electric
}
```
**Call:**
```python
headers = {"auth-token": ELECTRICITY_MAPS_API_KEY}
r = httpx.get(
    "https://api-access.electricitymaps.com/free-tier/carbon-intensity/latest",
    params={"zone": PROVINCE_TO_ZONE[province]},
    headers=headers
)
carbon_intensity_g_per_kwh = r.json()["carbonIntensity"]
```
**Fallback (if API down):** Use these static 2024 annual averages (gCO2eq/kWh):
```python
FALLBACK_CARBON_INTENSITY = {
    "QC": 1.8,    # Hydro-Québec: ~98% hydro
    "MB": 3.5,    # Manitoba Hydro: ~97% hydro
    "BC": 11.0,   # BC Hydro: mostly hydro
    "ON": 29.0,   # Nuclear + hydro mix
    "NL": 30.0,   # Mostly hydro
    "SK": 490.0,  # Coal/gas dominant
    "AB": 530.0,  # Natural gas dominant
    "NB": 200.0,  # Mixed
    "NS": 650.0,  # Coal dominant
    "PE": 8.0,    # Wind + imports
}
```
**Note:** Free tier = 1 zone only. For multi-province, either rotate API keys or use fallback table for non-primary zone.

---

### 3.2 IESO & AESO Historical Grid Data (ML Training)
**Purpose:** Training XGBoost grid strain model
**This is your most important pre-hackathon task — download before the event.**

#### IESO (Ontario)
**URL:** `https://ieso.ca/en/Power-Data/Data-Directory`
**Download these files:**
- Hourly Ontario Demand: `http://reports.ieso.ca/public/Demand/PUB_Demand_YYYY.csv`
  - Download 2020, 2021, 2022, 2023, 2024 (5 years)
  - Format: `Date,Hour,Ontario Demand (MW),Market Demand (MW)`
- Installed Capacity by Fuel Type (yearly summary PDFs — extract key numbers manually)
- Grid-connected total capacity: 37,205 MW (2024), 38,644 MW (2020)

**Direct CSV bulk download script (run pre-hackathon):**
```python
import httpx, os
for year in range(2020, 2025):
    url = f"http://reports.ieso.ca/public/Demand/PUB_Demand_{year}.csv"
    r = httpx.get(url)
    with open(f"data/ieso_demand_{year}.csv", "wb") as f:
        f.write(r.content)
    print(f"Downloaded IESO {year}")
```

#### AESO (Alberta)
**URL:** `https://www.aeso.ca/market/market-and-system-reporting/data-requests/`
**Download these files (pre-hackathon):**
- Hourly AIL + SMP data 2016-2020: Direct download from AESO data requests page
- Historical System Marginal Price: Available as CSV from AESO ETS
- Python library option: `pip install pyaeso` — wraps AESO ETS API
  ```python
  from pyaeso import ets
  # Gets current supply/demand
  supply_demand = ets.parse_csd_report(ets.fetch_csd_report())
  ```
- For historical bulk: `http://ets.aeso.ca/ets_web/ip/Market/Reports/HistoricalSystemMarginalPriceReportServlet`
  Download 2020-2024 by year.

**Alberta total capacity reference:** ~22,000 MW installed (2024)

#### Provincial Capacity Static Table (backup for provinces without open APIs)
```python
# Provincial grid capacity in MW (2024 values from annual reports)
PROVINCIAL_CAPACITY_MW = {
    "ON": 37205,   # IESO 2024 Year-End
    "AB": 22000,   # AESO approximate
    "BC": 16000,   # BC Hydro approximate
    "QC": 40000,   # Hydro-Québec total
    "MB": 6000,    # Manitoba Hydro approximate
    "SK": 5000,    # SaskPower approximate
    "NB": 4000,    # NB Power approximate
    "NS": 2700,    # NS Power approximate
    "NL": 2300,    # NL Hydro approximate
    "PE": 500,     # Maritime Electric approximate
}

# Provincial current surplus capacity (% of total that is uncommitted)
# Source: Provincial utility annual outlooks (conservative estimates)
PROVINCIAL_SURPLUS_PCT = {
    "ON": 0.08,   # IESO: tight, ~8% effective surplus
    "AB": 0.15,   # AESO: more flexible
    "BC": 0.12,   # BC Hydro: seasonal variation
    "QC": 0.05,   # Hydro-QC: very constrained, new data centres waitlisted
    "MB": 0.20,   # Manitoba: surplus hydro
    "SK": 0.10,
    "NB": 0.15,
    "NS": 0.08,
    "NL": 0.25,
    "PE": 0.30,
}
```

---

### 3.3 Statistics Canada API (Census Data)
**Purpose:** Community demographics for sociological pillar
**Base URL:** `https://www150.statcan.gc.ca/t1/wds/rest/`
**Auth:** None required (public API)
**Docs:** `https://www.statcan.gc.ca/en/developers/wds`

**Key approach:** Use the 2021 Census Profile SDMX API to get CSD-level demographics.
The CSD code is derived from the MapTiler reverse geocode result.

```python
# Step 1: Get CSD code from coordinates via MapTiler reverse geocode
# Step 2: Query StatsCan for that CSD

STATCAN_BASE = "https://www150.statcan.gc.ca/t1/wds/rest"

async def get_csd_demographics(csd_uid: str) -> dict:
    """
    CSD UID format: 7-digit code e.g. "3520005" for Toronto
    Get from MapTiler reverse geocode response field: properties.region_code
    """

    # Key table: 98-10-0001-01 = 2021 Census Profile
    # Key vectors we need:
    vectors = {
        "v_CA21_1":     "total_population",
        "v_CA21_560":   "median_total_income",
        "v_CA21_5862":  "unemployment_rate",
        "v_CA21_4201":  "pct_indigenous_identity",
        "v_CA21_1040":  "pct_low_income_lim_at",
        "v_CA21_6531":  "pct_postsecondary_certificate",
    }

    # SDMX endpoint for 2021 Census Profile
    url = f"https://www12.statcan.gc.ca/wds-sdw/cr2021geo-eng.cfm"
    # Params: GEO_ID = CSD UID, LEVEL = CSD

    # Simpler fallback: Direct table download
    # https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/downloadTbl/csvDownload/98-10-0001-01.zip
    # (pre-download this ~200MB file before hackathon, load into SQLite)

    pass

# PRE-HACKATHON TASK: Download census profile CSV and load into SQLite
# File: 98-10-0001-01_databaseLoadingData.csv (~200MB)
# Query: SELECT * FROM census WHERE GEO_UID = ? AND CHARACTERISTIC_ID IN (1, 560, 5862, 4201, 1040, 6531)
```

**Recommended pre-hackathon prep:**
```bash
# Download and load census data into SQLite for fast lookups
wget "https://www150.statcan.gc.ca/n1/tbl/csv/98-10-0001-01-eng.zip"
unzip 98-10-0001-01-eng.zip
python scripts/load_census_to_sqlite.py  # Write this pre-hackathon
```

**Key variables to extract per CSD:**

| Variable | StatsCan Code | Description |
|----------|---------------|-------------|
| Total population | v_CA21_1 | For noise zone calc |
| Median total income | v_CA21_560 | Economic vulnerability |
| Unemployment rate | v_CA21_5862 | Employment context |
| Pct Indigenous identity | v_CA21_4201 | Equity flag |
| Pct low income (LIM-AT) | v_CA21_1040 | Economic vulnerability |
| Pct with post-secondary | v_CA21_6531 | Tech workforce proxy |

---

### 3.4 Indigenous Services Canada — First Nations Data
**Purpose:** Water advisories + proximity flags for sociological pillar

**Water advisories (live):**
```
Long-term: https://www.sac-isc.gc.ca/eng/1506514143353/1533317130660
Short-term: https://www.sac-isc.gc.ca/eng/1562856509704/1562856530304
```
These are HTML pages — scrape or use the open data CSV:
```
CSV: https://www.canada.ca/content/dam/eccc/documents/csv/cesindicators/number-lt-dwa-first-nations/number-lt-dwa-first-nations-en.csv
```

**First Nations reserve boundaries (pre-download as shapefile/GeoJSON):**
```
Source: Crown-Indigenous Relations and Northern Affairs Canada
Open Government Portal: https://open.canada.ca/data/en/dataset/b6567c5c-8339-4021-9357-e57e6fd14d6f
Direct download: Aboriginal Lands — GeoJSON format
File: aboriginal_lands.geojson (~15MB)
```

**Pre-hackathon prep:**
```python
import geopandas as gpd
reserves = gpd.read_file("data/aboriginal_lands.geojson")
reserves_simplified = reserves[["NAME", "geometry", "TREATY"]].to_file("data/reserves_simplified.geojson")
```

**At runtime (simplified approach without full GIS):**
```python
from math import radians, sin, cos, sqrt, atan2

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2-lat1)
    dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

def nearest_reserve(lat: float, lng: float, reserves_df) -> dict:
    reserves_df["distance_km"] = reserves_df.apply(
        lambda r: haversine_km(lat, lng, r["centroid_lat"], r["centroid_lng"]), axis=1
    )
    nearest = reserves_df.nsmallest(1, "distance_km").iloc[0]
    return {
        "name": nearest["NAME"],
        "distance_km": nearest["distance_km"],
        "treaty": nearest.get("TREATY", "Unknown"),
        "has_water_advisory": nearest["NAME"] in ACTIVE_WATER_ADVISORY_COMMUNITIES
    }

# Pre-compute centroids from GeoJSON before hackathon
# ACTIVE_WATER_ADVISORY_COMMUNITIES: Set of community names from ISC live page
```

---

### 3.5 StatsCan Municipal Water Use Data
**Purpose:** Calculate % of local water supply consumed by data centre
**Table:** 38-10-0250-01 — Water use, by source and sector
**URL:** `https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/downloadTbl/csvDownload/38-10-0250-01.zip`

This gives municipal water system totals by geography. Use as denominator in:
```
pct_local_supply = (direct_L_day + indirect_L_day) / municipal_daily_supply_L × 100
```

**Pre-hackathon:** Download and create a lookup dict of CSD → daily_supply_litres.

If StatsCan table unavailable, use this benchmark formula:
```python
# Estimate municipal daily water supply from population
# Canadian average: ~220 litres/person/day (municipal supply)
def estimate_municipal_supply_L_day(population: int) -> float:
    return population * 220.0
```

---

### 3.6 ECCC Canadian Drought Monitor
**Purpose:** Watershed stress level for environmental pillar
**URL:** `https://agriculture.canada.ca/en/agricultural-production/weather/canadian-drought-monitor`
**Data:** Updated monthly, available as GeoJSON/shapefile

**API approach:**
```
https://api.weather.gc.ca/collections/ahccd-monthly/items?limit=1&f=json
```
ECCC has a public OGC API compliant endpoint.

**Pre-hackathon:** Download the current drought monitor GeoJSON and create a
province → drought_level lookup. For a hackathon, province-level is sufficient.

**Fallback static table** (based on 2024 conditions):
```python
DROUGHT_LEVEL_2024 = {
    "AB": "D2",  # Severe drought (oil sands region)
    "SK": "D1",  # Moderate drought
    "MB": "D0",  # Abnormally dry
    "BC": "D1",  # Moderate (varies by region)
    "ON": "D0",  # Abnormally dry (some regions)
    "QC": "None",
    "NB": "None",
    "NS": "D0",
    "NL": "None",
    "PE": "None",
}
DROUGHT_SCORE = {"None": 0, "D0": 1, "D1": 2, "D2": 3, "D3": 4, "D4": 5}
```

---

## 4. Calculation Engine (Deterministic Layer)

All calculations are pure functions. No ML. Each returns a float + the formula used
as a string for transparency.

### 4.1 Environmental Calculations

```python
# --- CARBON ---
def calc_annual_carbon(
    it_load_mw: float,
    pue: float,
    carbon_intensity_g_per_kwh: float  # from Electricity Maps
) -> tuple[float, str]:
    """
    Returns: (tonnes_co2_per_year, methodology_citation)
    Formula: IT_load_kW × 8760_hrs × PUE × CI_g/kWh ÷ 1,000,000
    Source: IEA data centre methodology, Electricity Maps lifecycle factors
    """
    it_load_kw = it_load_mw * 1000
    total_energy_kwh_yr = it_load_kw * 8760 * pue
    carbon_kg_yr = total_energy_kwh_yr * (carbon_intensity_g_per_kwh / 1000)
    carbon_tonnes_yr = carbon_kg_yr / 1000
    citation = (
        f"Formula: {it_load_kw:.0f}kW × 8,760h × PUE({pue}) × "
        f"{carbon_intensity_g_per_kwh:.1f}gCO2/kWh ÷ 1,000,000. "
        f"CI source: Electricity Maps lifecycle factors for zone {zone}."
    )
    return carbon_tonnes_yr, citation


# --- WATER ---
def calc_water_consumption(
    it_load_mw: float,
    pue: float,
    wue: float,                      # L/kWh, user input
    cooling_type: str,
    province: str,
    grid_water_intensity: float = None  # L/kWh for electricity generation
) -> dict:
    """
    Two-component model (direct + indirect).
    Source: Lei & Masanet (2022), The Green Grid WUE standard,
            Ceres "Drained by Data" report, EESI data center water analysis.
    Average WUE industry benchmark: 1.9 L/kWh (The Green Grid)
    """
    it_load_kw = it_load_mw * 1000

    # Direct (on-site cooling water)
    # WUE varies by cooling type
    wue_adjustments = {
        "air": 0.0,           # Air-cooled: near-zero water
        "evaporative": 1.9,   # Industry average
        "liquid_immersion": 0.4,  # ~70% reduction vs evaporative
        "hybrid": 1.2,
    }
    effective_wue = wue_adjustments.get(cooling_type, wue)
    direct_L_day = it_load_kw * 24 * pue * effective_wue

    # Indirect (water used in electricity generation)
    # Provincial water intensity of grid (L/kWh)
    # Source: Siddik et al. 2021, regional factors
    GRID_WATER_INTENSITY = {
        "ON": 1.8,   # Nuclear + hydro mix
        "AB": 0.9,   # Gas dominant (lower than hydro paradoxically at consumption)
        "BC": 3.2,   # Hydro (reservoir evaporation)
        "QC": 4.1,   # Hydro (large reservoirs)
        "MB": 3.8,   # Hydro
        "SK": 0.8,   # Gas/coal
        "NB": 1.2,
        "NS": 0.7,
        "NL": 4.0,   # Hydro
        "PE": 0.3,
    }
    gwi = grid_water_intensity or GRID_WATER_INTENSITY.get(province, 1.5)
    total_energy_kwh_day = it_load_kw * 24 * pue
    indirect_L_day = total_energy_kwh_day * gwi

    return {
        "direct_L_day": direct_L_day,
        "indirect_L_day": indirect_L_day,
        "total_L_day": direct_L_day + indirect_L_day,
        "methodology": (
            f"Direct: {it_load_kw:.0f}kW × 24h × PUE({pue}) × WUE({effective_wue:.1f}L/kWh). "
            f"Indirect: energy × grid water intensity ({gwi:.1f}L/kWh for {province}). "
            "Sources: The Green Grid WUE standard; Siddik et al. 2021 regional factors; "
            "Lei & Masanet 2022 cooling system analysis."
        )
    }


# --- GRID STRAIN ---
def calc_grid_strain_deterministic(
    it_load_mw: float,
    pue: float,
    province: str
) -> dict:
    """Deterministic component only. ML model adds probabilistic layer."""
    total_power_draw = it_load_mw * pue
    capacity = PROVINCIAL_CAPACITY_MW[province]
    surplus_mw = capacity * PROVINCIAL_SURPLUS_PCT[province]
    pct_of_surplus = (total_power_draw / surplus_mw) * 100 if surplus_mw > 0 else 999

    return {
        "total_power_draw_mw": total_power_draw,
        "provincial_capacity_mw": capacity,
        "surplus_mw": surplus_mw,
        "pct_of_surplus_consumed": pct_of_surplus,
        "raw_strain_flag": pct_of_surplus > 15  # >15% of surplus = high concern
    }
```

### 4.2 Economic Calculations

```python
def calc_economic_impact(
    it_load_mw: float,
    facility_type: str,
    capex_cad_millions: float,
    construction_months: int,
    province: str
) -> dict:
    """
    Sources:
    - Construction jobs: StatsCan construction employment multiplier ~12 jobs/$1M CAD
    - Permanent jobs: WRI data center employment analysis; US Chamber of Commerce 2017
      (hyperscale: ~0.5 FTE/MW, enterprise: ~2 FTE/MW, colo: ~3 FTE/MW)
    - Economic multiplier: Regional I-O multiplier 1.5-2.0 (StatsCan RIMS II proxy)
    - Tax: CBRE analysis: $1B data centre → ~$200M tax revenue over 10 years (2% of capex/yr)
    - Household electricity cost: Based on RBC Climate Action Institute analysis
    """

    # Jobs (honest version)
    JOBS_PER_MW = {"hyperscale": 0.5, "enterprise": 2.0, "colocation": 3.0}
    REGIONAL_MULTIPLIER = {"ON": 1.8, "AB": 1.6, "BC": 1.9, "QC": 1.7, "MB": 1.5, "SK": 1.4}

    direct_construction = capex_cad_millions * 12  # ~12 jobs per $1M
    multiplier = REGIONAL_MULTIPLIER.get(province, 1.6)
    peak_construction = direct_construction * multiplier

    direct_permanent = int(it_load_mw * JOBS_PER_MW.get(facility_type, 1.0))
    # Permanent jobs almost never use the full multiplier — be honest
    total_permanent = int(direct_permanent * 1.3)  # Conservative 1.3× (WRI research)

    # Tax revenue (10-year)
    capex_cad = capex_cad_millions * 1_000_000
    annual_property_tax = capex_cad * 0.015  # ~1.5% assessed value, varies by province
    total_tax_10yr = capex_cad * 0.20  # CBRE benchmark: ~20% of capex over 10 years

    # Infrastructure costs municipality must bear
    infrastructure_cost = capex_cad * 0.03  # ~3% of capex in grid/road/water upgrades

    # Household electricity rate impact
    # RBC analysis: large data centres add 1-5% to provincial electricity demand
    total_load = it_load_mw * JOBS_PER_MW.get(facility_type, 1.0)  # reusing variable
    # Simpler: estimate based on % of surplus consumed
    surplus_consumed_pct = (it_load_mw / PROVINCIAL_CAPACITY_MW.get(province, 20000)) * 100
    # Provincial avg household consumption ~9,500 kWh/year, rate ~$0.13/kWh = $1,235/yr
    rate_increase_pct = min(surplus_consumed_pct * 0.3, 8.0)  # capped at 8%
    household_cost_increase = 1235 * (rate_increase_pct / 100)

    return {
        "direct_construction_jobs": int(direct_construction),
        "peak_construction_jobs": int(peak_construction),
        "direct_permanent_jobs": direct_permanent,
        "total_permanent_with_multiplier": total_permanent,
        "tax_revenue_10yr_cad": total_tax_10yr,
        "property_tax_annual_cad": annual_property_tax,
        "infrastructure_costs_cad": infrastructure_cost,
        "net_fiscal_10yr_cad": total_tax_10yr - infrastructure_cost,
        "household_electricity_increase_annual_cad": household_cost_increase,
        "rate_increase_pct": rate_increase_pct,
        "methodology": (
            f"Construction jobs: {capex_cad_millions:.0f}M × 12 jobs/$1M × "
            f"{multiplier}× regional multiplier (StatsCan RIMS II). "
            f"Permanent jobs: {it_load_mw}MW × {JOBS_PER_MW.get(facility_type, 1.0)} FTE/MW "
            "(WRI data centre employment analysis; US Chamber 2017). "
            "Tax revenue: CBRE 10-year fiscal impact benchmark (20% of capex). "
            "Household electricity impact: RBC Climate Action Institute methodology."
        )
    }
```

### 4.3 Sociological Calculations

```python
def calc_sociological_impact(
    lat: float,
    lng: float,
    province: str,
    csd_demographics: dict,     # From StatsCan
    it_load_mw: float,
    reserves_df,                # Pre-loaded from GeoJSON
    active_water_advisories: set  # Community names with active advisories
) -> dict:

    # Indigenous proximity
    nearest = nearest_reserve(lat, lng, reserves_df)
    indigenous_flag = (
        nearest["distance_km"] < 50 or
        csd_demographics["pct_indigenous_population"] > 15 or
        nearest.get("has_water_advisory", False)
    )

    # Community Vulnerability Index (CVI)
    # Higher = more vulnerable = data centre benefits less likely to reach residents
    income_score = max(0, 100 - (csd_demographics["median_household_income"] / 1200))
    unemployment_score = csd_demographics["unemployment_rate"] * 5
    indigenous_score = csd_demographics["pct_indigenous_population"] * 2
    low_income_score = csd_demographics["pct_low_income"] * 2
    education_gap_score = max(0, 60 - csd_demographics["pct_postsecondary"]) * 1.5

    cvi = min(100, (
        income_score * 0.25 +
        unemployment_score * 0.20 +
        indigenous_score * 0.20 +
        low_income_score * 0.20 +
        education_gap_score * 0.15
    ))

    # Noise impact (80-90 dBA at source, ~50 dB at 500m)
    # Rough formula: noise radius where > 45dB (residential concern threshold)
    # Larger facility = more cooling fans = larger radius
    noise_radius_m = 200 + (it_load_mw * 5)  # Basic scaling, 5m per MW above base

    # Local hiring probability
    tech_workforce_pct = csd_demographics.get("pct_postsecondary", 20)
    local_hiring_pct = min(tech_workforce_pct * 0.4, 40)  # Max 40% local for tech roles

    return {
        "nearest_first_nation_km": nearest["distance_km"],
        "nearest_first_nation_name": nearest["name"],
        "treaty_territory": nearest.get("treaty"),
        "active_water_advisories_in_region": 1 if nearest.get("has_water_advisory") else 0,
        "indigenous_flag": indigenous_flag,
        "community_vulnerability_index": round(cvi, 1),
        "median_household_income": csd_demographics["median_household_income"],
        "unemployment_rate_pct": csd_demographics["unemployment_rate"],
        "pct_indigenous": csd_demographics["pct_indigenous_population"],
        "pct_low_income": csd_demographics["pct_low_income"],
        "estimated_noise_radius_m": noise_radius_m,
        "local_tech_workforce_pct": tech_workforce_pct,
        "estimated_local_hiring_pct": local_hiring_pct,
        "methodology": (
            "Indigenous proximity: haversine distance to nearest reserve centroid "
            "(Crown-Indigenous Relations GeoJSON). "
            "CVI: Weighted composite of StatsCan 2021 Census variables "
            "(income, unemployment, Indigenous identity, low income, education). "
            "Noise radius: empirical scaling from IT load. "
            "Local hiring: StatsCan LFS occupation data proxy."
        )
    }
```

---

## 5. ML Model — XGBoost Grid Strain Predictor

### 5.1 What It Predicts

**Target variable:** `grid_strain_event` (binary: 1 = strain event occurred)

**Definition of a strain event** (derived from raw data):
- Ontario (IESO): Hour where demand > 95% of available capacity, OR
  where operating reserve fell below 1,000 MW
- Alberta (AESO): Hour where pool price > $200/MWh (indicates tight supply)

This is the real ML contribution: given a proposed new load addition to a province,
what is the probability of pushing the grid into a strain event?

### 5.2 Training Data Pipeline

**Pre-hackathon task: Build this pipeline and train the model before the event.**

```python
# scripts/train_grid_model.py

import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import roc_auc_score, classification_report
import joblib

def build_training_dataset():
    """
    Combine IESO + AESO historical data into a unified training set.
    Each row = one hour in a province.
    Target = whether that hour was a strain event.
    """

    frames = []

    # --- Load IESO data (Ontario 2020-2024) ---
    for year in range(2020, 2025):
        df = pd.read_csv(f"data/ieso_demand_{year}.csv")
        df.columns = ["date", "hour", "ontario_demand_mw", "market_demand_mw"]
        df["province"] = "ON"
        df["year"] = year
        df["capacity_mw"] = 37205  # IESO 2024; adjust per year
        df["demand_mw"] = df["ontario_demand_mw"]
        df["utilization"] = df["demand_mw"] / df["capacity_mw"]
        # Label: strain event = utilization > 0.90
        df["strain_event"] = (df["utilization"] > 0.90).astype(int)
        frames.append(df)

    # --- Load AESO data (Alberta 2020-2024) ---
    # AESO format varies — adapt column names to your download
    for year in range(2020, 2025):
        try:
            df = pd.read_csv(f"data/aeso_demand_{year}.csv")
            # Typical AESO columns: Date, Hour Ending, Alberta Internal Load (MW), Pool Price ($/MWh)
            df = df.rename(columns={
                "Alberta Internal Load (MW)": "demand_mw",
                "Pool Price ($/MWh)": "pool_price"
            })
            df["province"] = "AB"
            df["year"] = year
            df["capacity_mw"] = 22000
            df["utilization"] = df["demand_mw"] / df["capacity_mw"]
            # AESO strain signal: price > $200/MWh
            df["strain_event"] = (df.get("pool_price", 0) > 200).astype(int)
            frames.append(df[["date", "hour", "demand_mw", "province", "year",
                               "capacity_mw", "utilization", "strain_event"]])
        except FileNotFoundError:
            print(f"AESO {year} not found, skipping")

    combined = pd.concat(frames, ignore_index=True)

    # --- Feature Engineering ---
    combined["date"] = pd.to_datetime(combined["date"])
    combined["month"] = combined["date"].dt.month
    combined["day_of_week"] = combined["date"].dt.dayofweek
    combined["is_weekend"] = (combined["day_of_week"] >= 5).astype(int)
    combined["is_summer"] = combined["month"].isin([6, 7, 8]).astype(int)
    combined["is_winter"] = combined["month"].isin([12, 1, 2]).astype(int)

    # Hour bins
    combined["hour_bin"] = pd.cut(
        combined["hour"],
        bins=[0, 6, 9, 17, 21, 24],
        labels=["night", "morning", "business", "evening", "late"],
        right=False
    )

    # Encode province
    le = LabelEncoder()
    combined["province_encoded"] = le.fit_transform(combined["province"])

    return combined, le


def engineer_prediction_features(
    province: str,
    proposed_load_mw: float,
    pue: float,
    le: LabelEncoder,
    capacity_mw: int,
    current_utilization: float = None  # If available from live grid data
) -> np.ndarray:
    """
    Build feature vector for a new proposal at inference time.
    Must match the training feature set exactly.
    """
    total_new_load = proposed_load_mw * pue

    # If we have live data (from IESO/AESO real-time), use it
    # Otherwise use seasonal averages
    base_utilization = current_utilization or 0.75  # 75% as default estimate

    projected_utilization = base_utilization + (total_new_load / capacity_mw)

    import datetime
    now = datetime.datetime.now()

    features = {
        "demand_mw": (base_utilization * capacity_mw) + total_new_load,
        "capacity_mw": capacity_mw,
        "utilization": projected_utilization,
        "month": now.month,
        "day_of_week": now.weekday(),
        "is_weekend": int(now.weekday() >= 5),
        "is_summer": int(now.month in [6, 7, 8]),
        "is_winter": int(now.month in [12, 1, 2]),
        # Use peak (worst case) hour bin for planning purposes
        "hour_bin_encoded": 2,  # "business" = highest demand period
        "province_encoded": le.transform([province])[0],
    }

    return np.array(list(features.values())).reshape(1, -1)


def train_model():
    print("Building training dataset...")
    data, le = build_training_dataset()

    # Features
    FEATURE_COLS = [
        "demand_mw", "capacity_mw", "utilization",
        "month", "day_of_week", "is_weekend",
        "is_summer", "is_winter",
        "province_encoded"
    ]

    X = data[FEATURE_COLS].dropna()
    y = data.loc[X.index, "strain_event"]

    print(f"Training on {len(X)} hourly observations across ON + AB")
    print(f"Strain event rate: {y.mean():.1%}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # XGBoost — well-suited for tabular data, fast, interpretable via feature importance
    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum(),  # Handle imbalance
        random_state=42,
        eval_metric="auc",
        early_stopping_rounds=20,
        verbosity=1
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=50
    )

    # Evaluate
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\nTest AUC: {auc:.4f}")
    print(classification_report(y_test, model.predict(X_test)))

    # Cross-validation
    cv_scores = cross_val_score(
        XGBClassifier(n_estimators=100, max_depth=4, random_state=42),
        X, y, cv=5, scoring="roc_auc"
    )
    print(f"CV AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Feature importance for transparency in report
    importance = dict(zip(FEATURE_COLS, model.feature_importances_))
    print("\nTop features:")
    for feat, imp in sorted(importance.items(), key=lambda x: -x[1])[:5]:
        print(f"  {feat}: {imp:.4f}")

    # Save model + label encoder + feature list
    joblib.dump({
        "model": model,
        "label_encoder": le,
        "feature_cols": FEATURE_COLS,
        "train_auc": auc,
        "cv_auc": cv_scores.mean(),
        "version": "xgboost_v1_ieso_aeso_2024"
    }, "models/grid_strain_model.pkl")

    print("\nModel saved to models/grid_strain_model.pkl")
    return model, le


if __name__ == "__main__":
    train_model()
```

### 5.3 Inference at Runtime

```python
# In FastAPI backend

import joblib
import numpy as np

# Load once at startup
MODEL_ARTIFACT = joblib.load("models/grid_strain_model.pkl")
GRID_MODEL = MODEL_ARTIFACT["model"]
LABEL_ENCODER = MODEL_ARTIFACT["label_encoder"]
FEATURE_COLS = MODEL_ARTIFACT["feature_cols"]

async def predict_grid_strain(
    province: str,
    it_load_mw: float,
    pue: float,
    capacity_mw: int,
    current_utilization: float = None
) -> GridStrainPrediction:

    # Build feature vector
    features = engineer_prediction_features(
        province, it_load_mw, pue,
        LABEL_ENCODER, capacity_mw, current_utilization
    )

    # Predict
    strain_probability = float(GRID_MODEL.predict_proba(features)[0, 1])

    # Rate increase probability — correlated but distinct
    rate_increase_probability = min(1.0, strain_probability * 0.85)

    # Threshold to level
    if strain_probability < 0.25:
        level = "low"
    elif strain_probability < 0.50:
        level = "moderate"
    elif strain_probability < 0.75:
        level = "high"
    else:
        level = "critical"

    # Feature importances for transparency
    importance_dict = dict(zip(
        FEATURE_COLS,
        GRID_MODEL.feature_importances_
    ))
    top_features = sorted(
        [{"feature": k, "importance": round(float(v), 4)} for k, v in importance_dict.items()],
        key=lambda x: -x["importance"]
    )[:5]

    return GridStrainPrediction(
        strain_probability=round(strain_probability, 4),
        rate_increase_probability=round(rate_increase_probability, 4),
        predicted_strain_level=level,
        confidence=round(MODEL_ARTIFACT["cv_auc"], 3),
        model_version=MODEL_ARTIFACT["version"],
        top_features=top_features
    )
```

---

## 6. LLM Layer (Groq)

**Rule: The LLM receives only structured numbers from the calculation engine.
It must not invent figures. Every claim in the report must cite a calculated value.**

```python
GROQ_MODEL = "llama-3.3-70b-versatile"  # Fast, high quality
# Fallback: "mixtral-8x7b-32768"

SYSTEM_PROMPT = """You are a strict municipal planning advisor helping city councils evaluate
data centre proposals. You generate a clear, mathematically-grounded report and a legally
actionable Community Benefit Agreement (CBA) playbook.

STRICT RULES:
1. Every specific number you mention MUST come from the data provided to you.
   Do not estimate, round, or invent figures.
2. Use plain language. Write as if explaining to an elected official worried about voters.
3. Be brutally honest about the trade-offs—especially regarding utility rates and jobs.
4. Format each section with a clear heading.
5. In the ECONOMIC REALITY CHECK, you MUST explicitly state the contrast between the massive
   capital expenditure (Capex) and the low number of permanent direct jobs. Emphasize that
   economic benefit must be captured via tax revenue and CBAs, not direct employment.
6. The NEGOTIATION PLAYBOOK must be specific and actionable.
7. CRITICAL: Include STRICT subsidy clawback clauses tied to audited annual performance metrics 
   for any metric that scores RED or poses a high risk to the community.
"""

def build_report_prompt(assessment: ImpactAssessment) -> str:
    e = assessment.environmental
    ec = assessment.economic
    s = assessment.sociological
    g = assessment.grid_strain
    capex = assessment.raw_inputs_used.get('capex_cad_millions')

    return f"""
Generate a city council impact report for the following data centre proposal:

LOCATION: {assessment.location.municipality}, {assessment.location.province}
PROPOSAL: {assessment.raw_inputs_used.get('it_load_mw')}MW IT load, 
          {assessment.raw_inputs_used.get('facility_type')} facility,
          ${capex}M CAD capex

--- ENVIRONMENTAL DATA ---
Annual carbon emissions: {e.annual_carbon_tonnes:,.0f} tonnes CO2e/year
Grid carbon intensity: {e.carbon_intensity_g_per_kwh:.1f} gCO2/kWh
Daily water consumption: {e.total_water_litres_per_day:,.0f} litres/day
As % of municipal daily supply: {e.pct_of_municipal_daily_supply:.1f}%
Grid power draw: {e.total_power_draw_mw:.1f} MW
% of provincial surplus consumed: {e.pct_of_provincial_surplus:.1f}%
Grid strain probability (ML model): {g.strain_probability:.0%}
Environmental scores: Carbon={e.carbon_score}, Water={e.water_score}, Grid={e.grid_score}

--- ECONOMIC DATA ---
Construction jobs (direct): {ec.direct_construction_jobs:,}
Permanent operations jobs (honest): {ec.direct_permanent_jobs} direct jobs vs. massive ${capex}M CAD Capex
10-year estimated tax revenue: ${ec.estimated_total_tax_revenue_10yr_cad/1e6:.1f}M CAD
Net fiscal impact (after infrastructure costs): ${ec.net_fiscal_impact_10yr_cad/1e6:.1f}M CAD
Estimated household utility rate increase (Ratepayer cost-shift): ${ec.estimated_household_electricity_increase_annual_cad:.0f}/year

--- SOCIOLOGICAL DATA ---
Nearest First Nation: {s.nearest_first_nation_km:.1f} km ({s.nearest_first_nation_name})
Community Vulnerability Index: {s.community_vulnerability_index:.0f}/100
NIMBY Risk Index (Population in noise zone): {s.residential_population_in_noise_zone:,} residents
Overall sociological score: {s.sociological_score}

--- OVERALL ---
Composite RAG score: {assessment.overall_score.composite_rag}

Generate:
1. EXECUTIVE SUMMARY (3 sentences, must include the composite RAG score and ratepayer risk)
2. ENVIRONMENTAL IMPACT (2-3 paragraphs, cite every number above)
3. ECONOMIC REALITY CHECK (2 paragraphs — explicitly contrast the ${capex}M investment against the low {ec.direct_permanent_jobs} permanent jobs, noting the risk of ratepayer utility increases)
4. COMMUNITY & NIMBY CONSIDERATIONS (2 paragraphs, highlighting the {s.residential_population_in_noise_zone:,} residents in the noise zone)
5. GRID SUSTAINABILITY (1 paragraph, cite ML model probability)
6. CBA NEGOTIATION PLAYBOOK & CLAWBACKS (5-7 specific, legally actionable conditions)

For the playbook, base recommendations on the risks:
- If household utility increases > $0: Demand a grid infrastructure cost-coverage agreement.
- If water score = red: Specify a financial clawback clause tying property tax breaks to strict water replenishment auditing.
- If NIMBY risk population is high: Demand verifiable noise abatement structures.
"""


async def generate_report(assessment: ImpactAssessment) -> tuple[str, list[str]]:
    from groq import AsyncGroq

    client = AsyncGroq(api_key=GROQ_API_KEY)

    response = await client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_report_prompt(assessment)}
        ],
        temperature=0.3,  # Low temperature for factual report
        max_tokens=2000
    )

    full_report = response.choices[0].message.content

    # Extract negotiation playbook as structured list
    # Parse the numbered list from the report
    playbook_lines = []
    in_playbook = False
    for line in full_report.split("\n"):
        if "NEGOTIATION PLAYBOOK" in line.upper():
            in_playbook = True
            continue
        if in_playbook and line.strip() and line.strip()[0].isdigit():
            playbook_lines.append(line.strip())
        elif in_playbook and line.startswith("#"):
            break  # Next section

    return full_report, playbook_lines
```

---

## 7. Pre-Hackathon Checklist

**Complete ALL of these before the hackathon starts.**

### Data Downloads
- [ ] IESO demand CSVs 2020–2024 from `reports.ieso.ca/public/Demand/`
- [ ] AESO demand CSVs 2020–2024 from AESO data requests page
- [ ] StatsCan Census 98-10-0001-01 CSV (~200MB) unzipped and loaded to SQLite
- [ ] StatsCan water use table 38-10-0250-01
- [ ] Crown-Indigenous Relations aboriginal lands GeoJSON
- [ ] Pre-compute reserve centroids from GeoJSON → save as `data/reserves_centroids.csv`

### API Keys — Sign Up Before Hackathon
- [ ] Electricity Maps free tier: `electricitymaps.com/free-tier-api`
- [ ] MapTiler free tier: `maptiler.com` (geocoding + tiles)
- [ ] Groq API: `console.groq.com` (free tier, fast inference)

### ML Training
- [ ] Run `python scripts/train_grid_model.py`
- [ ] Verify model AUC > 0.70 (should be ~0.80+ on IESO data)
- [ ] Save to `models/grid_strain_model.pkl`
- [ ] Document training data size and AUC in README

### Demo Scenario — Pre-Calculate
Use **Wonder Valley, Grande Prairie, Alberta** as the primary demo case:
```python
WONDER_VALLEY_DEMO = {
    "address": "Municipal District of Greenview, Grande Prairie, Alberta",
    "province": "AB",
    "it_load_mw": 2000,          # 5.6GW project, ~2GW phase 1
    "pue": 1.5,
    "wue": 1.9,
    "cooling_type": "evaporative",
    "facility_type": "hyperscale",
    "capex_cad_millions": 5000,  # $5B CAD phase 1
    "construction_months": 36,
    "has_onsite_generation": True,
    "renewable_ppa": False
}
```
**Expected outputs to validate:** Red water score (drought region), Indigenous flag=True
(Treaty 8), high grid strain probability.

Second demo case — **Good example:** Québec City, QC (green grid, water surplus, low drought):
```python
QUEBEC_CITY_DEMO = {
    "address": "Levis, Quebec",
    "province": "QC",
    "it_load_mw": 100,
    "pue": 1.3,
    "wue": 0.8,
    "cooling_type": "liquid_immersion",
    "facility_type": "enterprise",
    "capex_cad_millions": 800,
    "construction_months": 24,
    "has_onsite_generation": False,
    "renewable_ppa": True
}
```
**Expected:** Green carbon score (Hydro-Québec near-zero CI), better sociological score.

---

## 8. Repository Structure

```
/
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js app router
│   │   │   ├── page.tsx            # Landing + proposal form
│   │   │   ├── results/page.tsx    # Results dashboard
│   │   │   └── api/               # Next.js API routes (proxy to FastAPI)
│   │   ├── components/
│   │   │   ├── ProposalForm.tsx    # Input form with MapTiler picker
│   │   │   ├── ImpactDashboard.tsx # 3-pillar results view
│   │   │   ├── ScoreCard.tsx       # RAG traffic light component
│   │   │   ├── MapView.tsx         # MapTiler map with overlays
│   │   │   └── ReportViewer.tsx    # Full LLM report display
│   │   └── types/
│   │       └── assessment.ts       # TypeScript types matching Python models
│   ├── package.json
│   └── pnpm-lock.yaml
│
├── backend/
│   ├── main.py                     # FastAPI app, routes
│   ├── models.py                   # Pydantic models (single source of truth)
│   ├── calculator/
│   │   ├── environmental.py        # Carbon, water, grid calculations
│   │   ├── economic.py             # Jobs, tax, household cost calculations
│   │   └── sociological.py        # CVI, Indigenous proximity, noise
│   ├── data_sources/
│   │   ├── electricity_maps.py    # Electricity Maps API client
│   │   ├── statcan.py             # StatsCan API + SQLite fallback
│   │   ├── indigenous.py          # Reserve proximity, water advisories
│   │   ├── drought.py             # Drought monitor data
│   │   └── provincial_grid.py     # Static provincial capacity tables
│   ├── ml/
│   │   ├── predict.py             # Inference wrapper
│   │   └── features.py            # Feature engineering for inference
│   ├── llm/
│   │   └── report_generator.py    # Groq integration
│   └── pyproject.toml
│
├── data/                           # Pre-downloaded datasets (gitignored except samples)
│   ├── ieso_demand_2020.csv
│   ├── ieso_demand_2021.csv
│   ├── ieso_demand_2022.csv
│   ├── ieso_demand_2023.csv
│   ├── ieso_demand_2024.csv
│   ├── census_csd.db               # SQLite census database
│   ├── reserves_centroids.csv      # Pre-computed First Nations centroids
│   └── water_advisories.json       # Scraped from ISC
│
├── models/
│   └── grid_strain_model.pkl       # Trained XGBoost model
│
└── scripts/
    ├── train_grid_model.py         # ML training pipeline
    ├── download_data.py            # Pre-hackathon data download script
    └── load_census_to_sqlite.py    # Census CSV → SQLite loader
```

---

## 9. Key Formulas Quick Reference

| Metric | Formula | Source |
|--------|---------|--------|
| Annual carbon (t) | `IT_kW × 8760 × PUE × CI_g/kWh ÷ 1,000,000` | IEA + Electricity Maps |
| Direct water (L/day) | `IT_kW × 24 × PUE × WUE` | The Green Grid WUE standard |
| Indirect water (L/day) | `IT_kW × 24 × PUE × grid_water_intensity` | Siddik et al. 2021 |
| % of municipal supply | `total_L_day / municipal_daily_L × 100` | StatsCan 38-10-0250-01 |
| Grid strain % | `(IT_MW × PUE) / provincial_surplus_MW × 100` | Provincial utility reports |
| Construction jobs | `capex_M × 12 × regional_multiplier` | StatsCan RIMS II |
| Permanent jobs | `IT_MW × jobs_per_MW_coefficient` | WRI, US Chamber 2017 |
| 10yr tax revenue | `capex_CAD × 0.20` | CBRE fiscal benchmark |
| Household rate impact | `base_kwh_cost × demand_increase% × 0.30` | RBC Climate Action Institute |

---

## 10. Scoring Logic

```python
def rag_score(value: float, thresholds: tuple[float, float]) -> str:
    """Returns 'green', 'amber', or 'red'"""
    low, high = thresholds
    if value <= low: return "green"
    if value <= high: return "amber"
    return "red"

# Threshold definitions
CARBON_THRESHOLDS = (50_000, 200_000)      # tonnes/yr: green < 50k, red > 200k
WATER_PCT_THRESHOLDS = (2.0, 10.0)         # % of municipal supply
GRID_STRAIN_THRESHOLDS = (0.25, 0.55)      # ML probability
JOBS_THRESHOLDS = (50, 20)                 # Direct permanent jobs (inverted: more = better)
FISCAL_THRESHOLDS = (10_000_000, 0)        # Net fiscal 10yr (inverted)
CVI_THRESHOLDS = (30, 60)                  # Community vulnerability (lower = better)

def calc_composite_rag(
    environmental: EnvironmentalImpact,
    economic: EconomicImpact,
    sociological: SociologicalImpact,
    grid_strain: GridStrainPrediction
) -> OverallScore:
    # Numeric scores: green=1, amber=2, red=3
    score_map = {"green": 1, "amber": 2, "red": 3}

    env_score = (
        score_map[environmental.carbon_score] * 0.33 +
        score_map[environmental.water_score] * 0.33 +
        score_map[environmental.grid_score] * 0.34
    )
    eco_score = (
        score_map[economic.jobs_score] * 0.40 +
        score_map[economic.fiscal_score] * 0.60
    )
    soc_score = score_map[sociological.sociological_score]

    composite = (
        env_score * 0.40 +
        eco_score * 0.30 +
        soc_score * 0.30
    )

    if composite < 1.7: return "green"
    if composite < 2.3: return "amber"
    return "red"
```

---

## 11. Environment Variables

```bash
# .env (never commit)
ELECTRICITY_MAPS_API_KEY=your_key_here
MAPTILER_API_KEY=your_key_here
GROQ_API_KEY=your_key_here

# Optional
STATCAN_CACHE_DIR=./data/statcan_cache
MODEL_PATH=./models/grid_strain_model.pkl
```

---

## 12. What to Say to Judges

When asked "where does the AI come in?":

> "Three layers. First, a deterministic calculation engine applying published
> industry benchmarks — the carbon formula is from IEA methodology, the water
> model follows The Green Grid WUE standard. Second, an XGBoost model trained
> on five years of real hourly grid demand data from IESO and AESO — it predicts
> the probability that adding this proposed load will push the provincial grid
> into a strain event. Third, Groq's LLM generates the council report and
> negotiation playbook, but it can only cite numbers the first two layers
> calculated — it can't invent figures."

When asked "why not just use formulas?":

> "The ML model captures non-linear interactions that formulas miss — for example,
> a 100MW addition in Alberta in August during a drought-year heat wave has a
> fundamentally different strain profile than the same addition in January.
> The XGBoost model learned these patterns from 40,000+ historical hourly
> observations. Our AUC on the test set was [X]."

When asked about the data:

> "Everything is Canadian government open data — IESO published demand reports,
> StatsCan 2021 Census, Crown-Indigenous Relations treaty boundaries, Health Canada
> water advisories, and real-time grid carbon from Electricity Maps. We can show
> you the exact source citation for every number in the report."

---

*End of spec. Questions → start with Section 7 (pre-hackathon checklist).*
*If a data source is down during the hack, every source has a documented fallback.*
