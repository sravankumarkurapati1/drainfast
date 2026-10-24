// Pure helpers shared by vite.config.ts (node) and src/ (browser).
// Keep this file free of node-only imports.

/** Backend API paths proxied by the Vite dev server. */
export const API_PATHS = ['/health', '/brief', '/backlog', '/cells', '/backtest', '/rain-trend'] as const

export type ApiPath = (typeof API_PATHS)[number]

/** Matches an API path exactly, or as a prefix followed by '/' or '?'. */
export const API_PATH_PATTERN = '^/(health|brief|backlog|cells|backtest|rain-trend)(?:[/?]|$)'

const API_PATH_REGEX = new RegExp(API_PATH_PATTERN)

/** True when `url` targets one of the backend API paths. */
export function isApiPath(url: string): boolean {
  return API_PATH_REGEX.test(url)
}

/**
 * Normalize a base path to the `/segment/` form Vite expects.
 * undefined, whitespace-only, or slash-only input yields '/'.
 */
export function normalizeBasePath(raw: string | undefined): string {
  if (raw === undefined) return '/'
  const core = raw.trim().replace(/^\/+/, '').replace(/\/+$/, '')
  return core === '' ? '/' : `/${core}/`
}
