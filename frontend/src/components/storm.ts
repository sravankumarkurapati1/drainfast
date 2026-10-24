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
