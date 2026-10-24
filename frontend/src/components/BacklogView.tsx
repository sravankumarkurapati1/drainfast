import type { BacklogItem } from '../api/types'
import { STATUS_UNCLEAR } from '../api/types'
import { causeLabel } from './labels'
import { Stat } from './Stat'

export function BacklogView({ items }: { items: BacklogItem[] }) {
  if (items.length === 0) return <p className="notice">No open storm-related cases.</p>

  const unclear = items.filter((b) => b.status_label === STATUS_UNCLEAR).length
  const clogged = items.filter((b) => b.cause_label === 'clogged_basin').length
  const avgAge = items.reduce((sum, b) => sum + b.age_days, 0) / items.length

  return (
    <>
      <dl className="stats">
        <Stat label="Open cases" icon="inbox" tone="sky">
          {items.length}
          <small>Storm-related drain reports</small>
        </Stat>
        <Stat label="Likely clogged drain" icon="wrench" tone="amber">
          {clogged}
          <small>Fixable by cleaning</small>
        </Stat>
        <Stat label="Status unclear" icon="alert" tone="coral">
          {unclear}
          <small>Closed with a blank note</small>
        </Stat>
        <Stat label="Average age" icon="clock" tone="indigo">
          {avgAge.toFixed(1)} days
          <small>Since the report was opened</small>
        </Stat>
      </dl>

      <div className="table-wrap">
        <table>
          <caption>Open storm-related 311 cases, highest priority first</caption>
          <thead>
            <tr>
              <th scope="col">Ticket</th>
              <th scope="col">Cell</th>
              <th scope="col" className="num">
                Age (days)
              </th>
              <th scope="col">Likely cause</th>
              <th scope="col">Status</th>
              <th scope="col" className="num">
                Priority
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((b) => (
              <tr key={b.ticket_id}>
                <th scope="row">
                  <code>{b.ticket_id}</code>
                </th>
                <td>
                  <code>{b.cell_id}</code>
                </td>
                <td className="num">{b.age_days.toFixed(1)}</td>
                <td>
                  <span className={`pill pill-${b.cause_label}`}>{causeLabel(b.cause_label)}</span>
                </td>
                <td>
                  <span className={`pill ${b.status_label === STATUS_UNCLEAR ? 'pill-unclear-status' : 'pill-neutral'}`}>
                    {b.status_label}
                  </span>
                </td>
                <td className="num">
                  <strong>{b.priority_score.toFixed(2)}</strong>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
