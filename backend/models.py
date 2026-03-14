from pydantic import BaseModel, Field
from typing import Literal, Any
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

class ImpactAssessment(BaseModel):
    proposal_id: str
    timestamp: datetime
    location: dict[str, Any]
    data_freshness: dict[str, str]

    proposal: ProposalInput
    environmental: dict[str, Any]
    economic: dict[str, Any]
    sociological: dict[str, Any]

    grid_strain: GridStrainPrediction
    site_fit: SiteFitPrediction
    overall_score: dict[str, Any]
    policy_decision: PolicyDecision
    memo: CouncilMemo

    evidence_pack: dict[str, Any]
    methodology: dict[str, Any]
