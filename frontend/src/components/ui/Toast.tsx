import clsx from 'clsx'
import { useToastStore } from './toastStore'

export function Toast() {
  const { message, tone } = useToastStore()

  // The live region is always mounted so assistive tech registers it; errors
  // are assertive (interrupt), other tones are polite.
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      aria-live={tone === 'error' ? 'assertive' : 'polite'}
      aria-atomic="true"
      className="fixed bottom-6 right-6 z-50"
    >
      {message ? (
        <div
          className={clsx(
            'rounded-lg border px-4 py-3 text-sm shadow-lg',
            tone === 'success' && 'border-bda-green/40 bg-bda-panel text-bda-green',
            tone === 'error' && 'border-bda-red/40 bg-bda-panel text-bda-red',
            tone === 'info' && 'border-bda-border bg-bda-panel text-bda-text',
          )}
        >
          {message}
        </div>
      ) : null}
    </div>
  )
}
