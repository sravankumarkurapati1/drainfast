import { useEffect, useMemo, useState } from 'react'
import { getCellHistory } from '../api/client'
import type { Cell } from '../api/types'

const CONCURRENCY = 6

/**
 * cell_id -> neighborhood for the given cells.
 *
 * Uses the /cells list when it is available (bundled fixtures). The live API has no /cells
 * list, so any id still missing is looked up through /cells/{id}/history, whose reports
 * carry the neighborhood. Lookups that fail are skipped (the UI shows "Unknown area").
 */
export function useNeighborhoods(cellIds: string[], cells: Cell[] | undefined): Map<string, string> {
  const base = useMemo(() => new Map((cells ?? []).map((c) => [c.cell_id, c.neighborhood])), [cells])
  const [looked, setLooked] = useState<Map<string, string>>(() => new Map())

  // Stable key so the effect only reruns when the set of ids changes.
  const missingKey = useMemo(
    () => [...new Set(cellIds)].filter((id) => !base.has(id)).sort().join(','),
    [cellIds, base],
  )

  useEffect(() => {
    const ids = missingKey ? missingKey.split(',') : []
    if (ids.length === 0) return
    const controller = new AbortController()
    let next = 0
    const found = new Map<string, string>()

    const worker = async () => {
      while (next < ids.length && !controller.signal.aborted) {
        const id = ids[next++]
        try {
          const { data } = await getCellHistory(id, { signal: controller.signal, timeoutMs: 8000 })
          const name = data.find((r) => r.neighborhood)?.neighborhood
          if (name) found.set(id, name)
        } catch {
          // API down, unknown cell or aborted: leave this cell unnamed.
        }
      }
    }

    Promise.all(Array.from({ length: Math.min(CONCURRENCY, ids.length) }, worker)).then(() => {
      if (controller.signal.aborted || found.size === 0) return
      setLooked((prev) => {
        const merged = new Map(prev)
        found.forEach((v, k) => merged.set(k, v))
        return merged
      })
    })
    return () => controller.abort()
  }, [missingKey])

  return useMemo(() => {
    const out = new Map(looked)
    base.forEach((v, k) => out.set(k, v))
    return out
  }, [base, looked])
}
