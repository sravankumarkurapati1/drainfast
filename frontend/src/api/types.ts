// TypeScript mirrors of the Pydantic models in contracts/schemas.py (snake_case, frozen contract).
// Dates are ISO strings: `date` -> 'YYYY-MM-DD', `AwareDatetime` -> ISO 8601 with offset.

export type CauseLabel = 'clogged_basin' | 'grading_capacity' | 'coastal_tide' | 'unclear'
export type LabelSource = 'rule' | 'llm'
export type ReportStatus = 'open' | 'closed'
export type BasinOwner = 'BWSC' | 'City' | 'Private' | 'Mixed' | 'Unknown'

export const STORM_DAY_THRESHOLD_IN = 1.0
export const STATUS_UNCLEAR = 'Status unclear'

export interface Report {
  ticket_id: string
  opened_at: string
  closed_at: string | null
  status: ReportStatus
  lat: number
  lon: number
  cell_id: string
  text: string
  closing_note: string | null
  note_blank: boolean
  cause_label: CauseLabel
  label_source: LabelSource
  storm_day: string | null
  neighborhood: string
  ej_flag: boolean
  duplicate_of: string | null
}

export interface Cell {
  cell_id: string
  lat: number
  lon: number
  neighborhood: string
  basin_count: number
  basin_owner: BasinOwner
  ej_flag: boolean
  flood_area_flag: boolean
  tree_density: number | null
}

export interface Storm {
  storm_day: string
  rain_total_in: number
  max_hourly_in: number
  high_tide_flag: boolean
}

export interface FactorContribution {
  factor: string
  value: number
  contribution: number
}

export interface BriefItem {
  rank: number
  cell_id: string
  lat: number
  lon: number
  priority_score: number
  factors: FactorContribution[]
  reason: string
  evidence_ticket_ids: string[]
}

export interface BriefResponse {
  date: string
  forecast_rain_in: number
  high_tide_flag: boolean
  crews: number
  capacity_per_crew: number
  items: BriefItem[]
  fallback_mode: boolean
}

export interface BacklogItem {
  ticket_id: string
  cell_id: string
  opened_at: string
  age_days: number
  cause_label: CauseLabel
  note_blank: boolean
  status_label: string
  priority_score: number
  factors: FactorContribution[]
  evidence_ticket_ids: string[]
}

export interface BacktestResult {
  storm_day: string
  n_fixable_reports: number
  n_cells: number
  hit_rate_top100: number
  hit_rate_top200: number
  random_top100: number
  random_top200: number
  most_complaints_top100: number
  most_complaints_top200: number
}

export interface RainTrendPoint {
  year: number
  heavy_rain_days: number
}

export interface HealthResponse {
  status: 'ok'
}
