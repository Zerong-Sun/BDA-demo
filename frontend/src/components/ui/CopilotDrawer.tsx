import { MessageSquare, X } from 'lucide-react'
import { CopilotChat } from '../../features/copilot/CopilotChat'
import { useI18n } from '../../lib/i18n'

interface CopilotDrawerProps {
  open: boolean
  onClose: () => void
}

export function CopilotDrawer({ open, onClose }: CopilotDrawerProps) {
  const { t } = useI18n()

  if (!open) return null

  return (
    <>
      <button
        type="button"
        aria-label="Close copilot"
        className="fixed inset-0 z-40 bg-black/40"
        onClick={onClose}
      />
      <aside className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-bda-border bg-bda-panel shadow-2xl">
        <div className="flex items-start justify-between border-b border-bda-border p-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-bda-cyan">AI Beagle Copilot</p>
            <h2 className="text-lg font-semibold">{t.experiments.copilotTitle}</h2>
            <p className="mt-1 text-xs text-bda-muted">Phase 1 demo rules · DeepSeek hook reserved</p>
          </div>
          <button
            type="button"
            className="rounded-md border border-bda-border p-1.5 hover:bg-bda-panel-hover"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="min-h-0 flex-1">
          <CopilotChat />
        </div>
      </aside>
    </>
  )
}

export function CopilotToggleButton({ onClick, active }: { onClick: () => void; active?: boolean }) {
  return (
    <button
      type="button"
      className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs hover:bg-bda-panel ${
        active ? 'border-bda-cyan/50 text-bda-cyan' : 'border-bda-border text-bda-muted'
      }`}
      onClick={onClick}
      title="Open Copilot"
    >
      <MessageSquare className="h-3.5 w-3.5" />
      Copilot
    </button>
  )
}
