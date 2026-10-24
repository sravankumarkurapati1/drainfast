import { createContext, useContext } from 'react'
import type { DataSource } from './sources'

export interface DataSourceRegistry {
  /** datasetKey -> source of the most recent load. Empty until a dataset loads. */
  sources: Record<string, DataSource>
  /** Stable across renders. Records where `key` was loaded from. */
  report: (key: string, source: DataSource) => void
}

// Kept out of the .tsx provider file so react-refresh only sees component exports.
export const DataSourceContext = createContext<DataSourceRegistry | null>(null)

export function useDataSources(): DataSourceRegistry {
  const ctx = useContext(DataSourceContext)
  if (ctx === null) {
    throw new Error('useDataSources must be used inside <DataSourceProvider>')
  }
  return ctx
}
