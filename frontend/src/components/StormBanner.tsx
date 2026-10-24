import type { BriefResponse } from '../api/types'
import { STORM_DAY_THRESHOLD_IN } from '../api/types'
import { Icon } from './Icon'
import { isStormForecast, relativeDay, type RainSource } from './storm'

interface Props {
  brief: BriefResponse
  source: RainSource
}

/**
 * Says in words whether a storm is expected, so a supervisor doesn't have to interpret
 * the rain number. Storm = rain >= STORM_DAY_THRESHOLD_IN (shared contract constant).
 * The wording follows where the rain number came from, so a default or what-if value
 * is never presented as a real forecast.
 */
export function StormBanner({ brief, source }: Props) {
  const rain = brief.forecast_rain_in.toFixed(2)
  const when = relativeDay(brief.date)
  const threshold = STORM_DAY_THRESHOLD_IN.toFixed(1)
  const n = brief.items.length
  const storm = isStormForecast(brief.forecast_rain_in)
  const tide = brief.high_tide_flag ? ', with a high tide (coastal backup risk)' : ''

  if (source === 'unavailable') {
    return (
      <section className="storm-banner storm-unknown" role="status" aria-live="polite">
        <span className="storm-icon" aria-hidden="true">
          <Icon name="alert" size={26} />
        </span>
        <div>
          <p className="storm-title">Live forecast unavailable for {when}</p>
          <p className="storm-text">
            The API is in fallback mode, so this brief assumes the default planning rain of {rain} in. It
            is not a real forecast. Check the weather before sending crews, or enter a rain what-if.
          </p>
        </div>
        <span className="storm-tag">Check forecast</span>
      </section>
    )
  }

  let title: string
  let tag: string
  if (source === 'past') {
    title = storm ? `Past storm ${when}: ${rain} in recorded` : `No storm ${when}: ${rain} in recorded`
    tag = 'History'
  } else if (source === 'whatif') {
    title = `What-if ${when}: ${rain} in of rain`
    tag = 'What-if'
  } else {
    title = storm ? `Storm likely ${when}: ${rain} in forecast` : `No storm expected ${when}: ${rain} in forecast`
    tag = storm ? 'Action needed' : 'Routine day'
  }

  const text = storm
    ? source === 'past'
      ? `At or above the ${threshold} in storm threshold${tide}. These ${n} cells are what DrainFast would have sent crews to first.`
      : `At or above the ${threshold} in storm threshold${tide}. Send crews to these ${n} cells first, in rank order.`
    : `Below the ${threshold} in storm threshold. No storm prep needed; the ranking below can guide routine cleaning.`

  return (
    <section className={`storm-banner ${storm ? 'storm-yes' : 'storm-no'}`} role="status" aria-live="polite">
      <span className="storm-icon" aria-hidden="true">
        <Icon name={storm ? 'rain' : 'sun'} size={26} />
      </span>
      <div>
        <p className="storm-title">{title}</p>
        <p className="storm-text">{text}</p>
      </div>
      <span className="storm-tag">{tag}</span>
    </section>
  )
}
