export type CanadianProvince = "ON" | "AB" | "BC" | "QC" | "MB" | "SK" | "NS" | "NB" | "NL" | "PE";

export interface DataCentreProposal {
  address: string;
  province: CanadianProvince;
  it_load_mw: number;
  pue: number;
  wue: number;
  cooling_type: "air" | "evaporative" | "liquid_immersion" | "hybrid";
  facility_type: "hyperscale" | "enterprise" | "colocation";
  capex_cad: number;
  construction_months: number;
  has_onsite_generation: boolean;
  renewable_ppa: boolean;
}

export interface ImpactAssessment {
  proposal_id: string;
  data_freshness: Record<string, string>;
  location: {
    municipality: string;
    province: string;
    lat: number;
    lng: number;
  };
  environmental: {
    annual_carbon_tonnes: number;
    carbon_score: string;
    total_water_litres_per_day: number;
    water_score: string;
    grid_score: string;
    pct_of_municipal_daily_supply: number;
  };
  economic: {
    direct_permanent_jobs: number;
    total_permanent_jobs_with_multiplier: number;
    estimated_total_tax_revenue_10yr_cad: number;
    net_fiscal_impact_10yr_cad: number;
    fiscal_score: string;
    jobs_score: string;
  };
  sociological: {
    indigenous_flag: boolean;
    community_vulnerability_index: number;
    sociological_score: string;
    nearest_first_nation_km: number;
    air_quality_baseline: string;
    residential_population_in_noise_zone: number;
    estimated_noise_radius_m?: number | null;
  };
  grid_strain: {
    strain_probability: number;
    rate_increase_probability: number;
    predicted_strain_level: string;
    confidence: number;
    model_version: string;
  };
  overall_score: {
    composite_rag: string;
    summary_sentence: string;
  };
  policy_decision?: {
    recommendation: "approve" | "approve_with_conditions" | "defer" | "reject";
    triggered_rules: string[];
    selected_clause_ids: string[];
    policy_summary: string;
  };
  memo?: {
    executive_summary: string;
    environmental_section: string;
    economic_section: string;
    sociological_section: string;
    recommendation_section: string;
    clause_narratives: string[];
    disclaimer: string;
  };
  evidence_pack?: {
    environmental?: Record<string, unknown>;
    economic?: Record<string, unknown>;
    sociological?: Record<string, unknown>;
    grid_strain?: Record<string, unknown>;
  };
  negotiation_playbook: string[];
  report_narrative: string;
  methodology?: Record<string, unknown>;
}

export interface StreamEvent {
  stage: string;
  pct: number;
  result?: ImpactAssessment;
  error?: unknown;
}

export interface ExtractProposalResponse extends Partial<DataCentreProposal> {
  _extraction?: {
    mode: string;
    confidence: "high" | "moderate" | "low" | string;
    missing_fields: string[];
    warnings: string[];
  };
}

export interface MemoJobSubmitResponse {
  job_id: string;
  status: "queued" | "running" | "succeeded" | "failed" | string;
}

export interface MemoJobStatusResponse {
  job_id: string;
  status: "queued" | "running" | "succeeded" | "failed" | string;
  has_result: boolean;
  error?: string | null;
}

export interface MemoJobResultResponse {
  job_id: string;
  status: "succeeded" | "failed" | string;
  result: {
    proposal_id?: string;
    memo?: ImpactAssessment["memo"];
    report_narrative?: string;
    methodology?: Record<string, unknown>;
    fallback_used?: boolean;
    assessment?: ImpactAssessment;
  };
}
