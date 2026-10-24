import 'leaflet/dist/leaflet.css'
import type { CircleMarker as LCircleMarker, LatLngBoundsExpression } from 'leaflet'
import { useEffect, useMemo, useRef, useState } from 'react'
import { CircleMarker, MapContainer, Popup, Rectangle, TileLayer, Tooltip, useMap } from 'react-leaflet'
import type { BriefItem, Cell } from '../api/types'
import { factorLabel, formatContribution, topFactors } from './labels'

// Shared 100 m grid from contracts/cells.py (cell footprint drawn at street zoom).
const DLAT = 100 / 111320
const DLON = 100 / (111320 * Math.cos((42.32 * Math.PI) / 180))
const BOSTON: [number, number] = [42.32, -71.07]

// Keyless tile servers (no API key or sign-up needed). CARTO now serves "API key required"
// placeholder tiles, so it is not used.
const ESRI_ATTR = 'Tiles &copy; <a href="https://www.esri.com/">Esri</a>'
const OSM_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

const BASEMAPS = {
  dark: {
    label: 'Night',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    attribution: `${ESRI_ATTR} &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors`,
    maxNativeZoom: 16,
  },
  light: {
    label: 'Street',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: OSM_ATTR,
    maxNativeZoom: 19,
  },
  satellite: {
    label: 'Satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: `${ESRI_ATTR} &mdash; Esri, Maxar, Earthstar Geographics`,
    maxNativeZoom: 18,
  },
} as const
type Basemap = keyof typeof BASEMAPS

/** Amber (lower) -> coral -> crimson (highest), matching the brief's priority bars. */
function priorityColor(t: number): string {
  return `hsl(${42 - t * 42}, 95%, ${58 - t * 12}%)`
}

function cellBounds(lat: number, lon: number): LatLngBoundsExpression {
  return [
    [lat - DLAT / 2, lon - DLON / 2],
    [lat + DLAT / 2, lon + DLON / 2],
  ]
}

/** Keeps Leaflet's size in sync with its box (fixes grey/partial tiles after layout changes). */
function AutoResize() {
  const map = useMap()
  useEffect(() => {
    const fit = () => map.invalidateSize()
    const t = window.setTimeout(fit, 0)
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', fit)
      return () => {
        window.removeEventListener('resize', fit)
        window.clearTimeout(t)
      }
    }
    const ro = new ResizeObserver(fit)
    ro.observe(map.getContainer())
    return () => {
      ro.disconnect()
      window.clearTimeout(t)
    }
  }, [map])
  return null
}

/** Frames all ranked cells, or flies to the selected one. */
function Viewport({ bounds, focus, resetKey }: { bounds: LatLngBoundsExpression | null; focus: [number, number] | null; resetKey: number }) {
  const map = useMap()
  useEffect(() => {
    if (focus) map.flyTo(focus, 16, { duration: 0.8 })
  }, [map, focus])
  useEffect(() => {
    if (bounds) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 })
  }, [map, bounds, resetKey])
  return null
}

interface Props {
  items: BriefItem[]
  cells: Cell[]
  neighborhoods: Map<string, string>
}

export function MapView({ items, cells, neighborhoods }: Props) {
  const [basemap, setBasemap] = useState<Basemap>('dark')
  const [selected, setSelected] = useState<string | null>(null)
  const [resetKey, setResetKey] = useState(0)
  const markers = useRef<Record<string, LCircleMarker | null>>({})

  const ranked = useMemo(() => [...items].sort((a, b) => a.rank - b.rank), [items])
  const rankedIds = useMemo(() => new Set(items.map((i) => i.cell_id)), [items])
  const context = useMemo(() => cells.filter((c) => !rankedIds.has(c.cell_id)), [cells, rankedIds])

  const scores = items.map((i) => i.priority_score)
  const max = Math.max(...scores, 0)
  const min = Math.min(...scores, max)
  const span = max - min || 1
  const norm = (s: number) => (s - min) / span

  const bounds = useMemo<LatLngBoundsExpression | null>(
    () => (items.length ? items.map((i) => [i.lat, i.lon] as [number, number]) : null),
    [items],
  )
  const selectedItem = ranked.find((i) => i.cell_id === selected) ?? null
  const focus = useMemo<[number, number] | null>(
    () => (selectedItem ? [selectedItem.lat, selectedItem.lon] : null),
    [selectedItem],
  )

  // Open the popup once the fly-to has started.
  useEffect(() => {
    if (!selected) return
    const t = window.setTimeout(() => markers.current[selected]?.openPopup(), 850)
    return () => window.clearTimeout(t)
  }, [selected])

  const byArea = useMemo(() => {
    const counts = new Map<string, number>()
    for (const i of items) {
      const n = neighborhoods.get(i.cell_id) ?? 'Unknown'
      counts.set(n, (counts.get(n) ?? 0) + 1)
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [items, neighborhoods])
  const areaMax = Math.max(...byArea.map(([, n]) => n), 1)

  return (
    <div className="map-layout">
      <div className={`map map-${basemap}`} role="region" aria-label="Priority map of ranked cells in Boston">
        <MapContainer center={BOSTON} zoom={12} maxZoom={19} scrollWheelZoom={false} className="map-inner">
          <TileLayer
            key={basemap}
            attribution={BASEMAPS[basemap].attribution}
            url={BASEMAPS[basemap].url}
            maxNativeZoom={BASEMAPS[basemap].maxNativeZoom}
            maxZoom={19}
          />
          <AutoResize />
          <Viewport bounds={bounds} focus={focus} resetKey={resetKey} />

          {context.map((c) => (
            <CircleMarker
              key={c.cell_id}
              center={[c.lat, c.lon]}
              radius={4}
              pathOptions={{
                color: c.flood_area_flag ? '#38bdf8' : '#94a3b8',
                weight: c.flood_area_flag ? 2 : 1,
                fillColor: '#64748b',
                fillOpacity: 0.55,
              }}
            >
              <Tooltip>
                {c.neighborhood} · monitored, not ranked today
                {c.flood_area_flag ? ' · in flood extent' : ''}
              </Tooltip>
            </CircleMarker>
          ))}

          {ranked.map((item) => {
            const t = norm(item.priority_score)
            const color = priorityColor(t)
            const isSel = item.cell_id === selected
            return (
              <Rectangle
                key={`fp-${item.cell_id}`}
                bounds={cellBounds(item.lat, item.lon)}
                interactive={false}
                pathOptions={{ color, weight: 1, fillColor: color, fillOpacity: isSel ? 0.45 : 0.25 }}
              />
            )
          })}

          {ranked
            .filter((i) => i.rank <= 3)
            .map((item) => (
              <CircleMarker
                key={`halo-${item.cell_id}`}
                center={[item.lat, item.lon]}
                radius={30}
                interactive={false}
                pathOptions={{ className: 'halo', stroke: false, fillColor: '#fb7185', fillOpacity: 0.25 }}
              />
            ))}

          {[...ranked].reverse().map((item) => {
            const t = norm(item.priority_score)
            const isSel = item.cell_id === selected
            return (
              <CircleMarker
                key={item.cell_id}
                ref={(m) => {
                  markers.current[item.cell_id] = m
                }}
                center={[item.lat, item.lon]}
                radius={11 + t * 11}
                eventHandlers={{ click: () => setSelected(item.cell_id) }}
                pathOptions={{
                  color: isSel ? '#22d3ee' : '#ffffff',
                  weight: isSel ? 4 : 2,
                  fillColor: priorityColor(t),
                  fillOpacity: 0.95,
                }}
              >
                <Tooltip permanent direction="center" className="rank-label" opacity={1}>
                  {item.rank}
                </Tooltip>
                <Popup className="cell-popup" minWidth={260} maxWidth={320}>
                  <div className="pop-head">
                    <span className={`rank ${item.rank <= 3 ? 'rank-top' : ''}`}>{item.rank}</span>
                    <div>
                      <strong>{neighborhoods.get(item.cell_id) ?? 'Unknown area'}</strong>
                      <code>{item.cell_id}</code>
                    </div>
                  </div>
                  <div className="score">
                    <span className="score-bar" aria-hidden="true">
                      <span className="score-fill" style={{ width: `${Math.max(6, (item.priority_score / (max || 1)) * 100)}%` }} />
                    </span>
                    <span className="score-value">{item.priority_score.toFixed(2)}</span>
                  </div>
                  <p className="pop-reason">{item.reason}</p>
                  <ul className="factors">
                    {topFactors(item.factors).map((f) => (
                      <li key={f.factor}>
                        {factorLabel(f.factor)}
                        <span className="num">{formatContribution(f.contribution)}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="pop-evidence">
                    Evidence: {item.evidence_ticket_ids.length} past report
                    {item.evidence_ticket_ids.length === 1 ? '' : 's'}
                  </p>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>

        <div className="map-toolbar">
          <div className="seg" role="group" aria-label="Basemap">
            {(Object.keys(BASEMAPS) as Basemap[]).map((k) => (
              <button key={k} type="button" aria-pressed={basemap === k} onClick={() => setBasemap(k)}>
                {BASEMAPS[k].label}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="map-btn"
            onClick={() => {
              setSelected(null)
              setResetKey((n) => n + 1)
            }}
          >
            Reset view
          </button>
        </div>

        <div className="map-legend" aria-hidden="true">
          <div className="legend-scale" />
          <div className="legend-labels">
            <span>Lower priority</span>
            <span>Clear first</span>
          </div>
          <div className="legend-keys">
            <span>
              <i className="key key-ranked" /> Ranked cell (number = rank)
            </span>
            <span>
              <i className="key key-context" /> Monitored cell
            </span>
            <span>
              <i className="key key-flood" /> In flood extent
            </span>
          </div>
        </div>
      </div>

      <aside className="map-side" aria-label="Ranked cells">
        <div className="toplist">
          <h3>Clear in this order</h3>
          <ol>
            {ranked.map((item) => (
              <li key={item.cell_id}>
                <button
                  type="button"
                  className={`toplist-btn ${item.cell_id === selected ? 'is-selected' : ''}`}
                  aria-pressed={item.cell_id === selected}
                  onClick={() => setSelected(item.cell_id)}
                >
                  <span className={`rank ${item.rank <= 3 ? 'rank-top' : ''}`}>{item.rank}</span>
                  <span className="where">
                    {neighborhoods.get(item.cell_id) ?? item.cell_id}
                    <small>{topFactors(item.factors, 1).map((f) => factorLabel(f.factor))[0]}</small>
                  </span>
                  <span className="dot" style={{ background: priorityColor(norm(item.priority_score)) }} aria-hidden="true" />
                  <span className="score-value">{item.priority_score.toFixed(2)}</span>
                </button>
              </li>
            ))}
          </ol>
        </div>
        <div className="legend">
          <h3>Ranked cells by neighborhood</h3>
          <ul className="area-bars">
            {byArea.map(([name, n]) => (
              <li key={name}>
                <span>{name}</span>
                <span className="bar-track" aria-hidden="true">
                  <span className="bar-fill" style={{ width: `${(n / areaMax) * 100}%` }} />
                </span>
                <span className="num">{n}</span>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  )
}
