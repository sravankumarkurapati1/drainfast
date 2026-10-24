import type { BriefResponse } from '../api/types'
import { STORM_DAY_THRESHOLD_IN } from '../api/types'
import { Icon } from './Icon'
import { isStormForecast, relativeDay } from './storm'

/**
 * Says in words whether a storm is expected, so a supervisor doesn't have to interpret
 * the rain number. Storm = forecast >= STORM_DAY_THRESHOLD_IN (shared contract constant).
 */
export function StormBanner({ brief }: { brief: BriefResponse }) {
  const rain = brief.forecast_rain_in.toFixed(2)
  const when = relativeDay(brief.date)
  const threshold = STORM_DAY_THRESHOLD_IN.toFixed(1)
  const n = brief.items.length

  if (isStormForecast(brief.forecast_rain_in)) {
    return (
      <section className="storm-banner storm-yes" role="status" aria-live="polite">
        <span className="storm-icon" aria-hidden="true">
          <Icon name="rain" size={26} />
        </span>
        <div>
          <p className="storm-title">
            Storm likely {when}: {rain} in forecast
          </p>
          <p className="storm-text">
            At or above the {threshold} in storm threshold
            {brief.high_tide_flag ? ', with a high tide (coastal backup risk)' : ''}. Send crews to
            these {n} cells first, in rank order.
          </p>
        </div>
        <span className="storm-tag">Action needed</span>
      </section>
    )
  }

  return (
    <section className="storm-banner storm-no" role="status" aria-live="polite">
      <span className="storm-icon" aria-hidden="true">
        <Icon name="sun" size={26} />
      </span>
      <div>
        <p className="storm-title">
          No storm expected {when}: {rain} in forecast
        </p>
        <p className="storm-text">
          Below the {threshold} in storm threshold. No storm prep needed; the ranking below can guide
          routine cleaning.
        </p>
      </div>
      <span className="storm-tag">Routine day</span>
    </section>
  )
}
