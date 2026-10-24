// The single entry point for runtime HTTP from the app (local-dev-macos Req 3.1-3.6).
// Requests go to VITE_API_URL + path, or to a relative '/path' when VITE_API_URL is blank.
// Network errors, timeouts and 5xx fall back to bundled fixtures; 4xx is surfaced as an error.
import type { DataSource } from '../data/sources'
import { fixtureFor } from './fixtures'
import type {
  BacklogItem,
  BacktestResult,
  BriefResponse,
  Cell,
  HealthResponse,
  RainTrendPoint,
} from './types'

export type { DataSource }

export interface ApiResult<T> {
  data: T
  source: DataSource
}

export type ApiErrorKind = 'rejected' | 'unreachable'

/** 'rejected' = the API answered 4xx; 'unreachable' = no usable response and no fixture. */
export class ApiError extends Error {
  kind: ApiErrorKind
  status?: number

  constructor(kind: ApiErrorKind, message: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    if (status !== undefined) this.status = status
  }
}

/** Trimmed base URL with trailing slashes removed; '' when unset or whitespace-only. */
export function resolveBase(raw: string | undefined): string {
  if (raw === undefined) return ''
  return raw.trim().replace(/\/+$/, '')
}

/** Join base and path with exactly one '/'. An empty base yields a relative '/path'. */
export function joinUrl(base: string, path: string): string {
  const cleanPath = path.replace(/^\/+/, '')
  if (base === '') return '/' + cleanPath
  return base.replace(/\/+$/, '') + '/' + cleanPath
}

export type Outcome =
  | { kind: 'network-error' }
  | { kind: 'timeout' }
  | { kind: 'status'; status: number }

export type Decision = 'ok' | 'fallback' | 'rejected'

/** network-error | timeout | 5xx -> fallback; 4xx -> rejected; 2xx -> ok; other non-2xx -> fallback. */
export function decideOutcome(o: Outcome): Decision {
  if (o.kind !== 'status') return 'fallback'
  const { status } = o
  if (status >= 200 && status <= 299) return 'ok'
  if (status >= 400 && status <= 499) return 'rejected'
  return 'fallback'
}

export interface ApiGetOptions {
  /** Abort and fall back after this many ms. Default 10 000 (Req 3.4). */
  timeoutMs?: number
  /** Caller cancellation (e.g. component unmount). Aborting rethrows instead of falling back. */
  signal?: AbortSignal
}

export const DEFAULT_TIMEOUT_MS = 10_000

function fallback<T>(path: string, reason: string): ApiResult<T> {
  const data = fixtureFor(path)
  if (data === undefined) {
    throw new ApiError('unreachable', `API unreachable (${reason}) and no sample data for ${path}`)
  }
  return { data: data as T, source: 'fixture' }
}

export async function apiGet<T>(path: string, opts: ApiGetOptions = {}): Promise<ApiResult<T>> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal } = opts
  const url = joinUrl(resolveBase(import.meta.env.VITE_API_URL), path)

  // Caller already gave up: don't fetch, don't fall back.
  signal?.throwIfAborted()

  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)
  const onCallerAbort = () => controller.abort(signal?.reason)
  signal?.addEventListener('abort', onCallerAbort, { once: true })

  try {
    let outcome: Outcome
    let response: Response | undefined
    try {
      response = await fetch(url, {
        signal: controller.signal,
        headers: { Accept: 'application/json' },
      })
      outcome = { kind: 'status', status: response.status }
    } catch (err) {
      if (signal?.aborted && !timedOut) throw signal.reason ?? err
      outcome = timedOut ? { kind: 'timeout' } : { kind: 'network-error' }
    }

    const decision = decideOutcome(outcome)
    if (decision === 'rejected') {
      const status = outcome.kind === 'status' ? outcome.status : undefined
      throw new ApiError('rejected', `API rejected ${path} with HTTP ${status}`, status)
    }
    if (decision === 'fallback' || response === undefined) {
      return fallback<T>(path, outcome.kind === 'status' ? `HTTP ${outcome.status}` : outcome.kind)
    }

    try {
      // The body read is still covered by the timeout and caller signal.
      const data = (await response.json()) as T
      return { data, source: 'api' }
    } catch (err) {
      if (signal?.aborted && !timedOut) throw signal.reason ?? err
      return fallback<T>(path, timedOut ? 'timeout' : 'invalid JSON')
    }
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', onCallerAbort)
  }
}

type QueryValue = string | number | boolean | undefined

/** Append only the provided params as a query string. fixtureFor ignores the query. */
function withQuery(path: string, params?: Record<string, QueryValue>): string {
  if (!params) return path
  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) qs.append(key, String(value))
  }
  const s = qs.toString()
  return s ? `${path}?${s}` : path
}

type RequestOptions = Pick<ApiGetOptions, 'signal' | 'timeoutMs'>

export interface BriefParams {
  /** 'YYYY-MM-DD'. Required by the shared contract; the backend answers 422 without it. */
  date?: string
  /** Minimum 1. Required by the shared contract. */
  crews?: number
  /** Minimum 1; backend default 30. */
  capacity_per_crew?: number
}

export interface BacklogParams {
  /** Minimum 1. */
  limit?: number
}

export const getHealth = (opts?: RequestOptions) => apiGet<HealthResponse>('/health', opts)

export const getBrief = (params?: BriefParams, opts?: RequestOptions) =>
  apiGet<BriefResponse>(withQuery('/brief', { ...params }), opts)

export const getBacklog = (params?: BacklogParams, opts?: RequestOptions) =>
  apiGet<BacklogItem[]>(withQuery('/backlog', { ...params }), opts)

export const getCells = (opts?: RequestOptions) => apiGet<Cell[]>('/cells', opts)

export const getBacktest = (opts?: RequestOptions) => apiGet<BacktestResult[]>('/backtest', opts)

export const getRainTrend = (opts?: RequestOptions) =>
  apiGet<RainTrendPoint[]>('/rain-trend', opts)
