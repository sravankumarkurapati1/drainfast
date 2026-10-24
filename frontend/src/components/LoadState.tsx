import { errorMessage } from './labels'

interface Props {
  label: string
  loading: boolean
  error: unknown
  hasData: boolean
}

/** Loading / error notice for one dataset. Renders nothing once data is shown. */
export function LoadState({ label, loading, error, hasData }: Props) {
  if (error !== undefined && !loading) {
    return (
      <p role="alert" className="notice notice-error">
        {label}: {errorMessage(error)}
      </p>
    )
  }
  if (loading && !hasData) {
    return (
      <p role="status" className="notice notice-loading">
        Loading {label.toLowerCase()}…
      </p>
    )
  }
  return null
}
