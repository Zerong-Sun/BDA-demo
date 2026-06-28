import { useState, type PointerEvent as ReactPointerEvent } from 'react'
import { GripVertical, MessageSquare, X } from 'lucide-react'
import { CopilotChat } from '../../features/copilot/CopilotChat'
import { CopilotSettings } from '../../features/copilot/CopilotSettings'
import { ClusterDrafts } from '../../features/copilot/ClusterDrafts'
import { useProjectContext } from '../../lib/hooks/useProjectContext'
import { useI18n } from '../../lib/i18n'
import { useAppStore } from '../../lib/store/appStore'

interface CopilotDrawerProps {
  open: boolean
  onClose: () => void
  pageContext?: string
}

export function CopilotDrawer({ open, onClose, pageContext }: CopilotDrawerProps) {
  const { t } = useI18n()
  const copilotWidth = useAppStore((s) => s.copilotWidth)
  const setCopilotWidth = useAppStore((s) => s.setCopilotWidth)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [jobsOpen, setJobsOpen] = useState(false)
  const { projectId } = useProjectContext()

  if (!open) return null

  const startResize = (event: ReactPointerEvent<HTMLButtonElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId)
    const startX = event.clientX
    const startWidth = copilotWidth

    const onMove = (moveEvent: PointerEvent) => {
      const nextWidth = Math.min(560, Math.max(300, startWidth - (moveEvent.clientX - startX)))
      setCopilotWidth(nextWidth)
    }
    const onUp = () => {
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
    }

    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)
  }

  return (
    <aside
      className="fixed inset-y-0 right-0 z-50 flex max-w-full shrink-0 flex-col border-l border-bda-border bg-bda-panel shadow-2xl lg:relative lg:inset-auto lg:z-auto lg:min-h-[calc(100vh-4rem)] lg:shadow-none"
      style={{ width: `min(${copilotWidth}px, 100vw)` }}
    >
      <button
        type="button"
        aria-label="Resize Copilot"
        className="absolute inset-y-0 -left-2 flex w-4 cursor-col-resize items-center justify-center text-bda-muted hover:text-bda-cyan"
        onPointerDown={startResize}
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <div className="flex items-start justify-between border-b border-bda-border p-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-bda-cyan">BDA Copilot</p>
          <h2 className="text-lg font-semibold">{t.experiments.copilotTitle}</h2>
          <p className="mt-1 text-xs text-bda-muted">One Copilot for project, knowledge, workflow, tools, and LLM context.</p>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            className="rounded-md border border-bda-border px-2 py-1.5 text-xs text-bda-muted hover:bg-bda-panel-hover hover:text-bda-text"
            onClick={() => setSettingsOpen((value) => !value)}
          >
            Model settings
          </button>
          <button
            type="button"
            className="rounded-md border border-bda-border px-2 py-1.5 text-xs text-bda-muted hover:bg-bda-panel-hover hover:text-bda-text"
            onClick={() => setJobsOpen((value) => !value)}
          >
            Cluster jobs
          </button>
          <button
            type="button"
            className="rounded-md border border-bda-border p-1.5 hover:bg-bda-panel-hover"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
      {settingsOpen ? <CopilotSettings /> : null}
      {jobsOpen ? <ClusterDrafts projectId={projectId} /> : null}
      <div className="min-h-0 flex-1">
        <CopilotChat pageContext={pageContext} />
      </div>
    </aside>
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
