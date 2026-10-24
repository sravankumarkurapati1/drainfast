// Plain-language labels for contract enums and factor names (product rule 5).
import { ApiError } from '../api/client'
import type { CauseLabel, FactorContribution } from '../api/types'

const CAUSE_LABELS: Record<CauseLabel, string> = {
  clogged_basin: 'Likely clogged drain',
  grading_capacity: 'Street grading or pipe capacity',
  coastal_tide: 'Tide-driven backup',
  unclear: 'Cause unclear',
}

const FACTOR_LABELS: Record<string, string> = {
  past_storm_reports: 'Past storm reports',
  clog_risk: 'Clog risk',
  flood_area: 'Inside flood extent',
  ej_block_group: 'Environmental justice area',
  tree_density: 'Tree cover',
  forecast_rain: 'Forecast rain',
  high_tide: 'High tide',
}

export function causeLabel(c: CauseLabel): string {
  return CAUSE_LABELS[c] ?? 'Cause unclear'
}

export function factorLabel(f: string): string {
  const known = FACTOR_LABELS[f]
  if (known) return known
  const words = f.replace(/_/g, ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/** The `n` factors that raised the score most, largest first. */
export function topFactors(factors: FactorContribution[], n = 3): FactorContribution[] {
  return [...factors].sort((a, b) => b.contribution - a.contribution).slice(0, n)
}

export function formatContribution(c: number): string {
  return `${c >= 0 ? '+' : '−'}${Math.abs(c).toFixed(2)}`
}

export function formatPercent(x: number): string {
  return `${(x * 100).toFixed(1)}%`
}

/** Today's local date as 'YYYY-MM-DD'. */
export function todayIso(now = new Date()): string {
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** Inline error text for a failed load, so a view is never blank (Req 3.5, 3.6). */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.kind === 'rejected') {
      return `Request rejected (HTTP ${error.status ?? 'unknown'})`
    }
    return 'API unreachable and no sample data'
  }
  return 'Something went wrong while loading this data'
}
