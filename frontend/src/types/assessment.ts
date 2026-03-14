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
  };
  sociological: {
    indigenous_flag: boolean;
    community_vulnerability_index: number;
    sociological_score: string;
    nearest_first_nation_km: number;
    air_quality_baseline: string;
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
  negotiation_playbook: string[];
  report_narrative: string;
}

export interface StreamEvent {
  stage: string;
  pct: number;
  result?: ImpactAssessment;
  error?: unknown;
}
