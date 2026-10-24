import { STORM_DAY_THRESHOLD_IN } from '../api/types'
import { todayIso } from './labels'

/** 'today', 'tomorrow', or the ISO date itself, relative to the viewer's local date. */
export function relativeDay(isoDate: string, now = new Date()): string {
  const today = todayIso(now)
  const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1)
  if (isoDate === today) return 'today'
  if (isoDate === todayIso(tomorrow)) return 'tomorrow'
  return `on ${isoDate}`
}

/** True when the forecast meets the storm-day threshold (1 inch or more). */
export function isStormForecast(forecastIn: number): boolean {
  return forecastIn >= STORM_DAY_THRESHOLD_IN
}

/** Where the brief's rain number comes from. */
export type RainSource = 'forecast' | 'unavailable' | 'whatif' | 'past'

/** Tomorrow's local date as 'YYYY-MM-DD' (the default brief date). */
export function tomorrowIso(now = new Date()): string {
  return todayIso(new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1))
}

/**
 * Classify the rain behind a brief. A what-if override wins; past dates use recorded rain;
 * future dates in fallback mode use the default planning rain, which is not a forecast.
 */
export function rainSourceFor(briefDate: string, fallbackMode: boolean, hasOverride: boolean, now = new Date()): RainSource {
  if (hasOverride) return 'whatif'
  if (briefDate < todayIso(now)) return 'past'
  return fallbackMode ? 'unavailable' : 'forecast'
}

export const RAIN_LABEL: Record<RainSource, string> = {
  forecast: 'Forecast rain',
  unavailable: 'Planning rain (default)',
  whatif: 'What-if rain',
  past: 'Recorded rain',
}
