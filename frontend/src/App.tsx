import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { getBacklog, getBacktest, getBrief, getCells, getHealth, getRainTrend } from './api/client'
import { BacklogView } from './components/BacklogView'
import { BacktestTable, RainTrendChart } from './components/BacktestView'
import { BriefView } from './components/BriefView'
import { DemoBadge } from './components/DemoBadge'
import { Icon, type IconName } from './components/Icon'
import { LoadState } from './components/LoadState'
import { LogoMark, Wordmark } from './components/Logo'
import { MapView } from './components/MapView'
import { StormBanner } from './components/StormBanner'
import { rainSourceFor, tomorrowIso } from './components/storm'
import { DataSourceProvider } from './data/DataSourceContext'
import { showDemoBadge } from './data/sources'
import { useApi } from './data/useApi'
import { useDataSources } from './data/useDataSources'
import { useNeighborhoods } from './data/useNeighborhoods'
import './App.css'

const TABS: ReadonlyArray<{ id: TabId; label: string; icon: IconName }> = [
  { id: 'brief', label: 'Morning brief', icon: 'list' },
  { id: 'map', label: 'Map', icon: 'map' },
  { id: 'backlog', label: 'Backlog', icon: 'inbox' },
  { id: 'backtest', label: 'Backtest & rain trend', icon: 'chart' },
]
type TabId = 'brief' | 'map' | 'backlog' | 'backtest'

const DEFAULT_CREWS = 2
const DEFAULT_CAPACITY = 30

/** Parse a number input; keep the last valid value (minimum 1) while the user is typing. */
function positiveInt(raw: string, fallback: number): number {
  const n = Number.parseInt(raw, 10)
  return Number.isFinite(n) && n >= 1 ? n : fallback
}

/** Live/demo connection indicator in the header. Text carries the meaning, not just color. */
function ConnectionStatus() {
  const { sources } = useDataSources()
  if (Object.keys(sources).length === 0) return null
  const demo = showDemoBadge(sources)
  return (
    <span className={`conn ${demo ? '' : 'conn-live'}`}>
      <span className="conn-dot" aria-hidden="true" />
      {demo ? 'Offline: sample data' : 'Live API'}
    </span>
  )
}

function PanelHead({ title, subtitle, children }: { title: string; subtitle: string; children?: ReactNode }) {
  return (
    <div className="panel-head">
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {children}
    </div>
  )
}

function Dashboard() {
  const [tab, setTab] = useState<TabId>('brief')
  const [date, setDate] = useState(() => tomorrowIso())
  const [crews, setCrews] = useState(DEFAULT_CREWS)
  const [capacity, setCapacity] = useState(DEFAULT_CAPACITY)
  // '' = use the live forecast; a number = what-if rain override (forecast_rain_in).
  const [rainOverride, setRainOverride] = useState('')
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({})

  // Bumped to reload every dataset: when the tab regains focus, the network comes back,
  // or once a minute. A backend restart (e.g. fallback mode turned off) then shows up
  // without a manual page reload. Previous data stays on screen while reloading.
  const [refresh, setRefresh] = useState(0)
  useEffect(() => {
    const bump = () => {
      if (document.visibilityState === 'visible') setRefresh((n) => n + 1)
    }
    window.addEventListener('focus', bump)
    window.addEventListener('online', bump)
    document.addEventListener('visibilitychange', bump)
    const timer = window.setInterval(bump, 60_000)
    return () => {
      window.removeEventListener('focus', bump)
      window.removeEventListener('online', bump)
      document.removeEventListener('visibilitychange', bump)
      window.clearInterval(timer)
    }
  }, [])

  const fetchBrief = useCallback(
    (signal: AbortSignal) =>
      getBrief(
        {
          date,
          crews,
          capacity_per_crew: capacity,
          forecast_rain_in: rainOverride === '' ? undefined : Number(rainOverride),
        },
        { signal },
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refresh forces a reload
    [date, crews, capacity, rainOverride, refresh],
  )
  // eslint-disable-next-line react-hooks/exhaustive-deps -- refresh forces a reload
  const fetchHealth = useCallback((signal: AbortSignal) => getHealth({ signal }), [refresh])
  // eslint-disable-next-line react-hooks/exhaustive-deps -- refresh forces a reload
  const fetchCells = useCallback((signal: AbortSignal) => getCells({ signal }), [refresh])
  // eslint-disable-next-line react-hooks/exhaustive-deps -- refresh forces a reload
  const fetchBacklog = useCallback((signal: AbortSignal) => getBacklog(undefined, { signal }), [refresh])
  // eslint-disable-next-line react-hooks/exhaustive-deps -- refresh forces a reload
  const fetchBacktest = useCallback((signal: AbortSignal) => getBacktest({ signal }), [refresh])
  // eslint-disable-next-line react-hooks/exhaustive-deps -- refresh forces a reload
  const fetchRain = useCallback((signal: AbortSignal) => getRainTrend({ signal }), [refresh])

  // Health has no view; it only reports whether the live API answered (feeds the demo badge).
  useApi('health', fetchHealth)
  const brief = useApi('brief', fetchBrief)
  const cells = useApi('cells', fetchCells)
  const backlog = useApi('backlog', fetchBacklog)
  const backtest = useApi('backtest', fetchBacktest)
  const rain = useApi('rain-trend', fetchRain)

  const cellIds = useMemo(
    () => [...(brief.data?.items ?? []).map((i) => i.cell_id), ...(backlog.data ?? []).map((b) => b.cell_id)],
    [brief.data, backlog.data],
  )
  const neighborhoods = useNeighborhoods(cellIds, cells.data)
  const rainSource = rainSourceFor(
    brief.data?.date ?? date,
    brief.data?.fallback_mode ?? false,
    rainOverride !== '',
  )

  // Arrow/Home/End keys move between tabs (WAI-ARIA tabs pattern).
  const onTabKey = (e: KeyboardEvent<HTMLButtonElement>) => {
    const i = TABS.findIndex((t) => t.id === tab)
    let next: number
    if (e.key === 'ArrowRight') next = (i + 1) % TABS.length
    else if (e.key === 'ArrowLeft') next = (i - 1 + TABS.length) % TABS.length
    else if (e.key === 'Home') next = 0
    else if (e.key === 'End') next = TABS.length - 1
    else return
    e.preventDefault()
    const id = TABS[next].id
    setTab(id)
    tabRefs.current[id]?.focus()
  }

  const controls = (
    <form className="controls" onSubmit={(e) => e.preventDefault()} aria-label="Brief settings">
      <label>
        Date
        <input type="date" value={date} required onChange={(e) => e.target.value && setDate(e.target.value)} />
      </label>
      <label>
        Crews
        <input
          type="number"
          min={1}
          max={50}
          value={crews}
          onChange={(e) => setCrews(positiveInt(e.target.value, crews))}
        />
      </label>
      <label>
        Basins per crew
        <input
          type="number"
          min={1}
          max={200}
          value={capacity}
          onChange={(e) => setCapacity(positiveInt(e.target.value, capacity))}
        />
      </label>
      <label>
        Rain what-if (in)
        <input
          type="number"
          min={0}
          max={30}
          step={0.1}
          placeholder="Forecast"
          value={rainOverride}
          aria-describedby="rain-hint"
          onChange={(e) => {
            const v = e.target.value
            if (v === '' || (Number(v) >= 0 && Number(v) <= 30)) setRainOverride(v)
          }}
        />
        <span id="rain-hint" className="sr-only">
          Leave blank to use the live forecast
        </span>
      </label>
    </form>
  )

  return (
    <>
      <header className="app-header">
        <div className="rain" aria-hidden="true" />
        <div className="container">
          <div className="header-row">
            <div className="brand">
              <LogoMark size={46} />
              <div>
                <Wordmark />
                <span className="brand-sub">Boston catch-basin triage</span>
              </div>
            </div>
            <div className="header-meta">
              <ConnectionStatus />
              <DemoBadge />
            </div>
          </div>
          <div className="hero">
            <span className="hero-kicker">
              <Icon name="rain" size={14} /> Storm-ready morning brief
            </span>
            <h1>
              Clear the <span className="grad">right drains</span> before the storm.
            </h1>
            <p>
              DrainFast ranks Boston&apos;s catch basins by past storm reports, clog risk, flood
              extent and environmental justice, so crews reach the blocks that flood first.
            </p>
          </div>
        </div>
        <svg className="wave" viewBox="0 0 1440 60" preserveAspectRatio="none" aria-hidden="true">
          <path
            d="M0 32c120 18 240 26 360 18S600 10 720 12s240 26 360 28 240-14 360-22v42H0z"
            fill="var(--bg)"
          />
        </svg>
      </header>

      <main className="container">
        <div className="card shell">
          <div role="tablist" aria-label="DrainFast views" className="tabs">
            {TABS.map((t) => (
              <button
                key={t.id}
                ref={(el) => {
                  tabRefs.current[t.id] = el
                }}
                type="button"
                role="tab"
                id={`tab-${t.id}`}
                aria-selected={tab === t.id}
                aria-controls={`panel-${t.id}`}
                tabIndex={tab === t.id ? 0 : -1}
                onClick={() => setTab(t.id)}
                onKeyDown={onTabKey}
              >
                <span className="tab-icon" aria-hidden="true">
                  <Icon name={t.icon} size={16} />
                </span>
                {t.label}
              </button>
            ))}
          </div>

          <section
            role="tabpanel"
            id={`panel-${tab}`}
            aria-labelledby={`tab-${tab}`}
            tabIndex={0}
            className="panel"
          >
            {tab === 'brief' && (
              <>
                <PanelHead title="Morning brief" subtitle="Ranked cells for crews to clear before the next storm">
                  {controls}
                </PanelHead>
                <LoadState label="Morning brief" {...brief} hasData={brief.data !== undefined} />
                {brief.data && <StormBanner brief={brief.data} source={rainSource} />}
                {brief.data && <BriefView brief={brief.data} neighborhoods={neighborhoods} source={rainSource} />}
              </>
            )}

            {tab === 'map' && (
              <>
                <PanelHead title="Priority map" subtitle="Where today's ranked cells are across Boston">
                  {controls}
                </PanelHead>
                <LoadState label="Morning brief" {...brief} hasData={brief.data !== undefined} />
                {brief.data && <StormBanner brief={brief.data} source={rainSource} />}
                {brief.data && (
                  <MapView items={brief.data.items} cells={cells.data ?? []} neighborhoods={neighborhoods} />
                )}
              </>
            )}

            {tab === 'backlog' && (
              <>
                <PanelHead
                  title="Open backlog"
                  subtitle="Storm-related 311 drain cases, sorted by priority, with a plain-language likely cause"
                />
                <LoadState label="Backlog" {...backlog} hasData={backlog.data !== undefined} />
                {backlog.data && <BacklogView items={backlog.data} />}
              </>
            )}

            {tab === 'backtest' && (
              <>
                <PanelHead
                  title="Backtest"
                  subtitle="How well the ranking would have caught cleaning-fixable reports in past storms"
                />
                <LoadState label="Backtest" {...backtest} hasData={backtest.data !== undefined} />
                {backtest.data && <BacktestTable results={backtest.data} />}
                <h3 className="section-title">Heavy-rain trend</h3>
                <LoadState label="Rain trend" {...rain} hasData={rain.data !== undefined} />
                {rain.data && <RainTrendChart points={rain.data} />}
              </>
            )}
          </section>
        </div>
        <footer className="app-footer">
          <LogoMark size={18} />
          <span>DrainFast · Built at Hackachusetts with Kiro · Data: Boston 311, BWSC, NOAA, FEMA</span>
        </footer>
      </main>
    </>
  )
}

export default function App() {
  return (
    <DataSourceProvider>
      <Dashboard />
    </DataSourceProvider>
  )
}
