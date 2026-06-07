import { Component, type ErrorInfo, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

/**
 * Top-level error boundary. Prevents a render-time exception in any subtree from
 * blanking the entire SPA, showing a recoverable fallback instead. Wrap route
 * content (and other risky subtrees such as the Mol* viewer) with this.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surfaced to the console for now; wire to an error-reporting service later.
    console.error('Unhandled UI error:', error, info.componentStack)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children
    }

    if (this.props.fallback) {
      return this.props.fallback
    }

    return (
      <div
        role="alert"
        className="mx-auto my-12 max-w-lg rounded-lg border border-bda-red/40 bg-bda-panel p-6 text-sm"
      >
        <h2 className="mb-2 text-base font-semibold text-bda-red">Something went wrong</h2>
        <p className="mb-4 text-bda-muted">
          An unexpected error occurred while rendering this view. You can retry, or reload the page
          if the problem persists.
        </p>
        {this.state.error?.message ? (
          <pre className="mb-4 overflow-x-auto rounded-md bg-bda-bg p-3 text-xs text-bda-muted">
            {this.state.error.message}
          </pre>
        ) : null}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={this.handleReset}
            className="rounded-md border border-bda-border px-3 py-1.5 text-bda-text hover:bg-bda-panel-hover"
          >
            Try again
          </button>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="rounded-md border border-bda-border px-3 py-1.5 text-bda-text hover:bg-bda-panel-hover"
          >
            Reload page
          </button>
        </div>
      </div>
    )
  }
}
