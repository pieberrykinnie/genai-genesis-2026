/**
 * Types aligned with backend API contract for DataSite Impact Analyzer.
 * POST /api/assess — body: DataCentreProposal, response: ImpactAssessment.
 */

export type CanadianProvince =
  | "ON"
  | "AB"
  | "BC"
  | "QC"
  | "MB"
  | "SK"
  | "NS"
  | "NB"
  | "NL"
  | "PE"

export type CoolingType =
  | "air"
  | "evaporative"
  | "liquid_immersion"
  | "hybrid"

export type FacilityType = "hyperscale" | "enterprise" | "colocation"

export type RagScore = "green" | "amber" | "red"

export interface DataCentreProposal {
  address: string
  province: CanadianProvince
  it_load_mw: number // 1–500
  pue: number // 1.1–2.0
  wue: number // 0.5–3.0 L/kWh
  cooling_type: CoolingType
  facility_type: FacilityType
  capex_cad: number // CAD millions
  construction_months: number // 12–48
  has_onsite_generation?: boolean
  renewable_ppa?: boolean
}

export interface PillarResult {
  score: RagScore
  summary?: string
  details?: Record<string, unknown>
}

export interface GridStrainResult {
  score: RagScore
  probability?: number
  summary?: string
}

export interface ImpactAssessmentMetadata {
  proposal_id?: string
  location?: string
  timestamp?: string
  data_freshness?: string
}

export interface ImpactAssessment {
  metadata?: ImpactAssessmentMetadata
  environmental: PillarResult
  economic: PillarResult
  sociological: PillarResult
  grid_strain: GridStrainResult
  overall_score: RagScore
  negotiation_playbook: string[]
  report_narrative: string
  raw_inputs_used?: Record<string, unknown>
  calculation_methodology?: string
}
