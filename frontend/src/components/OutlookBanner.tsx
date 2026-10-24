import type { OutlookResponse } from '../api/client'
import { Icon } from './Icon'

/** Live NWS look-ahead: "Storm expected Thursday..." or "No storm in the forecast...". */
export function OutlookBanner({ outlook }: { outlook: OutlookResponse }) {
  const storm = outlook.brief_active
  const tag = outlook.fallback ? 'Check forecast' : storm ? 'Action needed' : outlook.next_storm ? 'Watch' : 'No storm'
  const days = outlook.days.length
  const detail = outlook.fallback
    ? 'The live NWS forecast could not be reached.'
    : storm
      ? `Live NWS forecast. Storm day = ${outlook.threshold_in} in or more; the brief turns on ${outlook.lookahead_days} days ahead.`
      : `Live NWS forecast for the next ${days} days. The pre-storm list appears when a day reaches ${outlook.threshold_in} in or more. The backlog is still available.`
  return (
    <section
      className={`storm-banner ${outlook.fallback ? 'storm-unknown' : storm ? 'storm-yes' : 'storm-no'}`}
      role="status"
      aria-live="polite"
    >
      <span className="storm-icon" aria-hidden="true">
        <Icon name={outlook.fallback ? 'alert' : storm ? 'rain' : 'sun'} size={26} />
      </span>
      <div>
        <p className="storm-title">{outlook.message}</p>
        <p className="storm-text">{detail}</p>
      </div>
      <span className="storm-tag">{tag}</span>
    </section>
  )
}
