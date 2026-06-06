import { create } from 'zustand'
import clsx from 'clsx'

interface ToastState {
  message: string | null
  tone: 'info' | 'success' | 'error'
  show: (message: string, tone?: ToastState['tone']) => void
  clear: () => void
}

export const useToastStore = create<ToastState>((set) => ({
  message: null,
  tone: 'info',
  show: (message, tone = 'info') => {
    set({ message, tone })
    window.setTimeout(() => set({ message: null }), 3200)
  },
  clear: () => set({ message: null }),
}))

export function Toast() {
  const { message, tone } = useToastStore()
  if (!message) return null

  return (
    <div
      className={clsx(
        'fixed bottom-6 right-6 z-50 rounded-lg border px-4 py-3 text-sm shadow-lg',
        tone === 'success' && 'border-bda-green/40 bg-bda-panel text-bda-green',
        tone === 'error' && 'border-bda-red/40 bg-bda-panel text-bda-red',
        tone === 'info' && 'border-bda-border bg-bda-panel text-bda-text',
      )}
    >
      {message}
    </div>
  )
}
