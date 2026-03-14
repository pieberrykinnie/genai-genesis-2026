from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

RagScore = Literal["green", "amber", "red"]
Recommendation = Literal["approve", "approve_with_conditions", "defer", "reject"]

class ProposalInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    address: str | None = None
    province: str | None = None
    city: str | None = None
    latitude: float | None = Field(default=None, validation_alias=AliasChoices("latitude", "lat"))
    longitude: float | None = Field(default=None, validation_alias=AliasChoices("longitude", "lng"))

    facility_size_sqft: float | None = None
    it_load_mw: float | None = Field(default=None, validation_alias=AliasChoices("it_load_mw", "projected_mw_load"))
    cooling_type: str | None = None
    facility_type: str | None = None
    pue: float | None = None
    wue: float | None = None

    jobs_promised: int | None = None
    water_intake_lps: float | None = None
    capex_cad: float | None = Field(default=None, validation_alias=AliasChoices("capex_cad", "estimated_capital_cost_cad"))
    annual_property_tax_cad: float | None = None
    construction_months: int | None = None
    has_onsite_generation: bool | None = None
    renewable_ppa: bool | None = None

    notes: str | None = None


class Location(BaseModel):
    municipality: str
    province: str
    lat: float
    lng: float


class EnvironmentalImpact(BaseModel):
    annual_carbon_tonnes: float
    carbon_score: RagScore
    total_water_litres_per_day: float
    water_score: RagScore
    grid_score: RagScore
    pct_of_municipal_daily_supply: float


class EconomicImpact(BaseModel):
    direct_permanent_jobs: int
    total_permanent_jobs_with_multiplier: int
    estimated_total_tax_revenue_10yr_cad: float
    net_fiscal_impact_10yr_cad: float
    fiscal_score: RagScore
    jobs_score: RagScore


class SociologicalImpact(BaseModel):
    indigenous_flag: bool
    community_vulnerability_index: float
    sociological_score: RagScore
    nearest_first_nation_km: float
    air_quality_baseline: str
    residential_population_in_noise_zone: int

class GridStrainPrediction(BaseModel):
    strain_probability: float
    rate_increase_probability: float
    predicted_strain_level: str
    confidence: float
    model_version: str
    top_features: list[dict[str, Any]]

class SiteFitPrediction(BaseModel):
    site_fit_probability: float
    site_fit_band: str
    confidence: float
    model_version: str
    top_features: list[dict[str, Any]]
    nearest_similar_sites: list[dict[str, Any]]

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


class OverallScore(BaseModel):
    composite_rag: RagScore
    summary_sentence: str


class ImpactAssessment(BaseModel):
    proposal_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    location: Location
    data_freshness: dict[str, str]

    proposal: ProposalInput
    environmental: EnvironmentalImpact
    economic: EconomicImpact
    sociological: SociologicalImpact

    grid_strain: GridStrainPrediction
    site_fit: SiteFitPrediction | None = None
    overall_score: OverallScore
    policy_decision: PolicyDecision | None = None
    memo: CouncilMemo | None = None

    negotiation_playbook: list[str] = Field(default_factory=list)
    report_narrative: str = ""
    evidence_pack: dict[str, Any] = Field(default_factory=dict)
    methodology: dict[str, Any] = Field(default_factory=dict)
