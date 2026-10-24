import { useDataSources } from '../data/useDataSources'
import { showDemoBadge } from '../data/sources'
import './DemoBadge.css'

/** Visible, announced indicator that at least one dataset is sample (fixture) data. */
export function DemoBadge() {
  const { sources } = useDataSources()
  if (!showDemoBadge(sources)) return null
  return (
    <span role="status" className="demo-badge">
      demo data
    </span>
  )
}
