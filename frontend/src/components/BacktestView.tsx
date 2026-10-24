import type { BacktestResult, RainTrendPoint } from '../api/types'
import { formatPercent } from './labels'
import { Stat } from './Stat'

function mean(xs: number[]): number {
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0
}

function Compare({ drainfast, random, complaints }: { drainfast: number; random: number; complaints: number }) {
  const rows = [
    { label: 'DrainFast', value: drainfast, cls: 'is-drainfast' },
    { label: 'Most complaints', value: complaints, cls: '' },
    { label: 'Random', value: random, cls: '' },
  ]
  return (
    <div className="compare">
      {rows.map((r) => (
        <div key={r.label} className={`compare-row ${r.cls}`}>
          <span>{r.label}</span>
          <span className="bar-track" aria-hidden="true">
            <span className="bar-fill" style={{ width: `${Math.max(2, r.value * 100)}%` }} />
          </span>
          <span className="num">{formatPercent(r.value)}</span>
        </div>
      ))}
    </div>
  )
}

export function BacktestTable({ results }: { results: BacktestResult[] }) {
  if (results.length === 0) return <p className="notice">No backtest results recorded.</p>

  const df = mean(results.map((r) => r.hit_rate_top100))
  const rnd = mean(results.map((r) => r.random_top100))
  const mc = mean(results.map((r) => r.most_complaints_top100))
  const lift = rnd > 0 ? df / rnd : 0

  return (
    <>
      <dl className="stats">
        <Stat label="DrainFast hit rate" icon="target" tone="sky">
          {formatPercent(df)}
          <small>Average, top 100 cells</small>
        </Stat>
        <Stat label="vs. random" icon="chart" tone="emerald">
          {lift ? `${lift.toFixed(1)}×` : 'n/a'}
          <small>Random picks catch {formatPercent(rnd)}</small>
        </Stat>
        <Stat label="vs. most complaints" icon="inbox" tone="indigo">
          {formatPercent(mc)}
          <small>Ranking by complaint count only</small>
        </Stat>
        <Stat label="Storms tested" icon="rain" tone="amber">
          {results.length}
          <small>Past storm days held out</small>
        </Stat>
      </dl>

      <div className="table-wrap">
        <table>
          <caption>Share of cleaning-fixable reports that fell in the top-ranked cells, by past storm</caption>
          <thead>
            <tr>
              <th scope="col">Storm day</th>
              <th scope="col" className="num">
                Fixable reports
              </th>
              <th scope="col" className="num">
                Cells
              </th>
              <th scope="col">Top 100 cells</th>
              <th scope="col">Top 200 cells</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.storm_day}>
                <th scope="row">{r.storm_day}</th>
                <td className="num">{r.n_fixable_reports}</td>
                <td className="num">{r.n_cells}</td>
                <td>
                  <Compare drainfast={r.hit_rate_top100} random={r.random_top100} complaints={r.most_complaints_top100} />
                </td>
                <td>
                  <Compare drainfast={r.hit_rate_top200} random={r.random_top200} complaints={r.most_complaints_top200} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

const BAR_W = 18
const GAP = 6
const CHART_H = 150
const LABEL_H = 18
const LEFT = 22

/** Inline SVG bar chart of heavy-rain days per year, with the numbers in a table below. */
export function RainTrendChart({ points }: { points: RainTrendPoint[] }) {
  if (points.length === 0) return <p className="notice">No rain trend data.</p>
  const max = Math.max(...points.map((p) => p.heavy_rain_days), 1)
  const width = LEFT + points.length * (BAR_W + GAP)
  const first = points[0]
  const last = points[points.length - 1]
  const ticks = [0, Math.round(max / 2), max]

  return (
    <figure className="chart">
      <svg
        viewBox={`0 0 ${width} ${CHART_H + LABEL_H}`}
        role="img"
        aria-label={`Heavy-rain days per year at Boston Logan, ${first.year} to ${last.year}. Highest: ${max} days.`}
      >
        <defs>
          <linearGradient id="rain-bar" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#22d3ee" />
            <stop offset="1" stopColor="#6366f1" />
          </linearGradient>
        </defs>
        {ticks.map((t) => {
          const y = CHART_H - (t / max) * CHART_H
          return (
            <g key={t}>
              <line x1={LEFT} x2={width} y1={y} y2={y} className="gridline" />
              <text x={LEFT - 4} y={y + 3} textAnchor="end" className="axis">
                {t}
              </text>
            </g>
          )
        })}
        {points.map((p, i) => {
          const h = (p.heavy_rain_days / max) * CHART_H
          const x = LEFT + i * (BAR_W + GAP) + GAP / 2
          return (
            <g key={p.year}>
              <rect x={x} y={CHART_H - h} width={BAR_W} height={h} rx={4} fill="url(#rain-bar)">
                <title>{`${p.year}: ${p.heavy_rain_days} days`}</title>
              </rect>
              {(i % 5 === 0 || i === points.length - 1) && (
                <text x={x + BAR_W / 2} y={CHART_H + 13} textAnchor="middle" className="axis">
                  {p.year}
                </text>
              )}
            </g>
          )
        })}
      </svg>
      <figcaption>Heavy-rain days (1 inch or more) per year at Boston Logan</figcaption>
      <details>
        <summary>Show numbers</summary>
        <table>
          <thead>
            <tr>
              <th scope="col">Year</th>
              <th scope="col" className="num">
                Heavy-rain days
              </th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.year}>
                <th scope="row">{p.year}</th>
                <td className="num">{p.heavy_rain_days}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  )
}
