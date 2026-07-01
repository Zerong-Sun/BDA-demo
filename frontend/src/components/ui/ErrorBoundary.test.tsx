import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ErrorBoundary } from './ErrorBoundary'

describe('ErrorBoundary', () => {
  it('renders fallback when a child throws', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    function Broken(): never {
      throw new Error('boom')
    }

    try {
      render(
        <ErrorBoundary>
          <Broken />
        </ErrorBoundary>,
      )

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    } finally {
      consoleError.mockRestore()
    }
  })
})
