import type { ReactNode } from 'react'
import { ApiError } from '../../lib/api/client'

interface ApiStateProps {
  isLoading?: boolean
  isError?: boolean
  error?: unknown
  loadingMessage?: string
  emptyMessage?: string
  isEmpty?: boolean
  onRetry?: () => void
  children: ReactNode
}

export function ApiState({
  isLoading,
  isError,
  error,
  loadingMessage = 'Loading...',
  emptyMessage,
  isEmpty,
  onRetry,
  children,
}: ApiStateProps) {
  if (isLoading) {
    return <p className="text-sm text-bda-muted">{loadingMessage}</p>
  }

  if (isError) {
    const message = resolveApiErrorMessage(error)
    return (
      <div className="rounded-lg border border-bda-red/40 bg-bda-panel p-4 text-sm text-bda-red">
        <p>{message}</p>
        {onRetry ? (
          <button
            type="button"
            className="mt-2 rounded-md border border-bda-border px-3 py-1.5 text-bda-text hover:bg-bda-panel-hover"
            onClick={onRetry}
          >
            Retry
          </button>
        ) : null}
      </div>
    )
  }

  if (isEmpty && emptyMessage) {
    return <p className="text-sm text-bda-muted">{emptyMessage}</p>
  }

  return <>{children}</>
}

function resolveApiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error && error.message) return error.message
  return 'Backend unavailable. Start the API on port 8100 and retry.'
}
