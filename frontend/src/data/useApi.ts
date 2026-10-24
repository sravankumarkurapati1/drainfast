import { useEffect, useState } from 'react'
import type { ApiResult } from '../api/client'
import { useDataSources } from './useDataSources'

/** Calls the API client; receives an AbortSignal so the request is cancelled on unmount. */
export type Fetcher<T> = (signal: AbortSignal) => Promise<ApiResult<T>>

export interface ApiState<T> {
  data: T | undefined
  error: unknown
  loading: boolean
}

interface Settled<T> {
  fetcher: Fetcher<T>
  data: T | undefined
  error: unknown
}

/**
 * Loads one dataset through the API client and reports its source ('api' | 'fixture')
 * to the demo-badge registry under `key`.
 *
 * `fetcher` must be referentially stable (wrap it in useCallback); a new fetcher
 * triggers a new request and cancels the previous one.
 */
export function useApi<T>(key: string, fetcher: Fetcher<T>): ApiState<T> {
  const { report } = useDataSources()
  const [settled, setSettled] = useState<Settled<T> | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetcher(controller.signal).then(
      (result) => {
        if (controller.signal.aborted) return
        report(key, result.source)
        setSettled({ fetcher, data: result.data, error: undefined })
      },
      (error: unknown) => {
        // Unmount or a newer request cancelled this one: not an error to show.
        if (controller.signal.aborted) return
        setSettled({ fetcher, data: undefined, error })
      },
    )
    return () => controller.abort()
  }, [key, fetcher, report])

  // Loading until the result for the current fetcher arrives; the previous
  // result stays visible meanwhile so the view does not flash empty.
  const loading = settled === null || settled.fetcher !== fetcher
  return { data: settled?.data, error: settled?.error, loading }
}
