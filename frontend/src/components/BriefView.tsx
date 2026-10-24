import type { BriefResponse } from '../api/types'
import { factorLabel, formatContribution, topFactors } from './labels'
import { Stat } from './Stat'
import { isStormForecast, RAIN_LABEL, type RainSource } from './storm'

interface Props {
  brief: BriefResponse
  neighborhoods: Map<string, string>
  source: RainSource
}

export function BriefView({ brief, neighborhoods, source }: Props) {
  const storm = isStormForecast(brief.forecast_rain_in)
  const maxScore = Math.max(...brief.items.map((i) => i.priority_score), 0) || 1
  const capacity = brief.crews * brief.capacity_per_crew

  return (
    <>
      <dl className="stats">
        <Stat label={RAIN_LABEL[source]} icon="rain" tone="sky">
          {brief.forecast_rain_in.toFixed(2)} in
          <small>{source === 'unavailable'
            ? 'Default, not a forecast'
            : storm
              ? 'Storm day (1 in or more)'
              : 'Below storm threshold'}</small>
        </Stat>
        <Stat label="High tide" icon="tide" tone="indigo">
          {brief.high_tide_flag ? 'Yes' : 'No'}
          <small>{brief.high_tide_flag ? 'Coastal backup risk' : 'No tide pressure'}</small>
        </Stat>
        <Stat label="Crew capacity" icon="crew" tone="emerald">
          {capacity} basins
          <small>
            {brief.crews} crews × {brief.capacity_per_crew} each
          </small>
        </Stat>
        <Stat label="Cells ranked" icon="target" tone="coral">
          {brief.items.length}
          <small>{brief.fallback_mode ? 'Fallback mode' : `Brief for ${brief.date}`}</small>
        </Stat>
      </dl>

      {brief.items.length === 0 ? (
        <p className="notice">No cells ranked for this date.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <caption>
              {storm
                ? 'Cells to clear before the storm, highest priority at the top'
                : 'No storm expected: cells ranked for routine cleaning, highest priority at the top'}
            </caption>
            <thead>
              <tr>
                <th scope="col">Rank</th>
                <th scope="col">Location</th>
                <th scope="col">Priority</th>
                <th scope="col">Why</th>
                <th scope="col">Top factors</th>
                <th scope="col">Evidence</th>
              </tr>
            </thead>
            <tbody>
              {brief.items.map((item) => (
                <tr key={item.cell_id}>
                  <td>
                    <span className={`rank ${item.rank <= 3 ? 'rank-top' : ''}`}>{item.rank}</span>
                  </td>
                  <th scope="row">
                    {neighborhoods.get(item.cell_id) ?? 'Unknown area'}
                    <br />
                    <code>{item.cell_id}</code>
                  </th>
                  <td>
                    <div className="score">
                      <span className="score-bar" aria-hidden="true">
                        <span
                          className="score-fill"
                          style={{ width: `${Math.max(4, (item.priority_score / maxScore) * 100)}%` }}
                        />
                      </span>
                      <span className="score-value">{item.priority_score.toFixed(2)}</span>
                    </div>
                  </td>
                  <td className="reason">{item.reason}</td>
                  <td>
                    <ul className="factors">
                      {topFactors(item.factors).map((f) => (
                        <li key={f.factor}>
                          {factorLabel(f.factor)}
                          <span className="num">{formatContribution(f.contribution)}</span>
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td>
                    <details>
                      <summary>
                        {item.evidence_ticket_ids.length} ticket
                        {item.evidence_ticket_ids.length === 1 ? '' : 's'}
                      </summary>
                      <ul className="tickets">
                        {item.evidence_ticket_ids.map((id) => (
                          <li key={id}>
                            <code>{id}</code>
                          </li>
                        ))}
                      </ul>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
