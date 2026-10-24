// Bundled demo fixtures, used by the API client when the backend is unreachable.
// Shapes mirror contracts/schemas.py (see ../types.ts).
import backlog from './backlog.json'
import backtest from './backtest.json'
import brief from './brief.json'
import cells from './cells.json'
import health from './health.json'
import rainTrend from './rain-trend.json'

/** Kept in sync with API_PATHS in frontend/vite.helpers.ts. */
const FIXTURES: Record<string, unknown> = {
  '/health': health,
  '/brief': brief,
  '/backlog': backlog,
  '/cells': cells,
  '/backtest': backtest,
  '/rain-trend': rainTrend,
}

/**
 * Return the fixture for an API path, or undefined when none exists.
 * The query string is ignored; a path matches an endpoint exactly or as a '/'-prefixed sub-path.
 */
export function fixtureFor(path: string): unknown | undefined {
  const pathname = path.split('?', 1)[0]
  for (const [apiPath, data] of Object.entries(FIXTURES)) {
    if (pathname === apiPath || pathname.startsWith(apiPath + '/')) return data
  }
  return undefined
}
