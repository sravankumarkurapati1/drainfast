import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { DataSourceContext } from './useDataSources'
import type { DataSource } from './sources'

export function DataSourceProvider({ children }: { children: ReactNode }) {
  const [sources, setSources] = useState<Record<string, DataSource>>({})

  const report = useCallback((key: string, source: DataSource) => {
    // Returning the previous object skips the re-render when nothing changed.
    setSources((prev) => (prev[key] === source ? prev : { ...prev, [key]: source }))
  }, [])

  const value = useMemo(() => ({ sources, report }), [sources, report])

  return <DataSourceContext.Provider value={value}>{children}</DataSourceContext.Provider>
}
