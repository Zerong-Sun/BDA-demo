import { CopilotChat } from './CopilotChat'

export function CopilotPanel({ open }: { open: boolean }) {
  if (!open) return null

  return (
    <aside className="flex h-full min-h-[640px] w-full flex-col rounded-lg border border-bda-border bg-bda-panel lg:max-w-sm">
      <div className="border-b border-bda-border p-4">
        <p className="text-xs uppercase tracking-wide text-bda-cyan">BDA Copilot</p>
        <h2 className="text-lg font-semibold">Unified project copilot</h2>
        <p className="mt-1 text-xs text-bda-muted">Knowledge, tools, workflow planning, and LLM provider share one runtime.</p>
      </div>
      <CopilotChat />
    </aside>
  )
}
