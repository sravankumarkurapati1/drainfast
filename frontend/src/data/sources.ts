/** Where a dataset's data came from: the live API or a bundled sample fixture. */
export type DataSource = 'api' | 'fixture'

/** True iff at least one loaded dataset was served from a fixture (Req 3.7, 3.8). */
export function showDemoBadge(sources: Record<string, DataSource>): boolean {
  return Object.values(sources).includes('fixture')
}
