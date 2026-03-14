from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from constants import CanadianProvince, RagScore


CoolingType = Literal["air", "evaporative", "liquid_immersion", "hybrid"]
FacilityType = Literal["hyperscale", "enterprise", "colocation"]


class DataCentreProposal(BaseModel):
    address: str
    province: CanadianProvince
    it_load_mw: float = Field(ge=1, le=5000)
    pue: float = Field(ge=1.1, le=2.5)
    wue: float = Field(ge=0.0, le=5.0)
    cooling_type: CoolingType
    facility_type: FacilityType
    capex_cad: float = Field(gt=0)
    construction_months: int = Field(ge=12, le=60)
    has_onsite_generation: bool = False
    renewable_ppa: bool = False


class LocationData(BaseModel):
    lat: float
    lng: float
    province: str
    municipality: str
    census_subdivision_id: str
    census_division_id: str


class EnvironmentalImpact(BaseModel):
    annual_carbon_tonnes: float
    carbon_intensity_g_per_kwh: float
    carbon_score: RagScore
    direct_water_litres_per_day: float
    indirect_water_litres_per_day: float
    total_water_litres_per_day: float
    pct_of_municipal_daily_supply: float
    water_score: RagScore
    total_power_draw_mw: float
    provincial_capacity_mw: float
    pct_of_provincial_surplus: float
    grid_score: RagScore


class EconomicImpact(BaseModel):
    direct_construction_jobs: int
    peak_construction_jobs: int
    direct_permanent_jobs: int
    total_permanent_jobs_with_multiplier: int
    estimated_property_tax_10yr_cad: float
    estimated_total_tax_revenue_10yr_cad: float
    estimated_household_electricity_increase_annual_cad: float
    net_fiscal_impact_10yr_cad: float
    jobs_score: RagScore
    fiscal_score: RagScore


class SociologicalImpact(BaseModel):
    nearest_first_nation_km: float
    nearest_first_nation_name: str | None = None
    treaty_territory: str | None = None
    active_water_advisories_nearby: int
    indigenous_flag: bool
    community_vulnerability_index: float
    median_household_income_cad: float
    unemployment_rate_pct: float
    pct_indigenous_population: float
    pct_low_income: float
    estimated_noise_radius_m: float
    residential_population_in_noise_zone: int
    air_quality_baseline: str
    local_tech_workforce_pct: float
    estimated_local_hiring_pct: float
    sociological_score: RagScore


class GridStrainPrediction(BaseModel):
    strain_probability: float
    rate_increase_probability: float
    predicted_strain_level: Literal["low", "moderate", "high", "critical"]
    confidence: float
    model_version: str
    top_features: list[dict[str, Any]]


class OverallScore(BaseModel):
    composite_rag: RagScore
    environmental_weight: float = 0.40
    economic_weight: float = 0.30
    sociological_weight: float = 0.30
    summary_sentence: str


class ImpactAssessment(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    proposal_id: str
    location: LocationData
    timestamp: datetime
    data_freshness: dict[str, str]
    environmental: EnvironmentalImpact
    economic: EconomicImpact
    sociological: SociologicalImpact
    grid_strain: GridStrainPrediction
    overall_score: OverallScore
    negotiation_playbook: list[str]
    report_narrative: str
    raw_inputs_used: dict[str, Any]
    calculation_methodology: str
