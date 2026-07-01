import { useState } from 'react'
import { RotateCcw, Send } from 'lucide-react'
import { useCopilotChat } from './useCopilotChat'
import { useProjectContext } from '../../lib/hooks/useProjectContext'

export function CopilotChat({ pageContext }: { pageContext?: string }) {
  const { projectId } = useProjectContext()
  const { messages, loading, error, send, resetMessages } = useCopilotChat(projectId, pageContext)
  const [input, setInput] = useState('')

  const handleSend = async () => {
    const trimmed = input.trim()
    if (!trimmed) return
    setInput('')
    await send(trimmed)
  }

  return (
    <div className="flex h-full min-h-[480px] flex-col">
      <div className="flex items-center justify-between border-b border-bda-border px-4 py-2">
        <span className="text-xs text-bda-muted">
          {projectId ? `Project ${projectId}` : 'Select a project for project-aware answers'}
        </span>
        <button
          type="button"
          aria-label="Reset Copilot conversation"
          title="Reset Copilot conversation"
          className="rounded-md border border-bda-border p-1.5 text-bda-muted hover:bg-bda-panel-hover hover:text-bda-text"
          disabled={loading}
          onClick={resetMessages}
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {error ? (
          <div className="rounded-lg border border-bda-red/40 bg-bda-panel p-3 text-sm text-bda-red">
            {error}
          </div>
        ) : null}
        {messages.filter((msg) => msg.role !== 'system').map((msg, idx) => (
          <div
            key={`${msg.role}-${idx}`}
            className={`rounded-lg px-3 py-2 text-sm ${
              msg.role === 'user'
                ? 'ml-8 bg-bda-panel-hover text-bda-text'
                : 'mr-8 border border-bda-border bg-bda-bg text-bda-muted'
            }`}
          >
            {msg.content}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 border-t border-bda-border p-3">
        <label htmlFor="copilot-input" className="sr-only">
          Ask the Copilot a question
        </label>
        <input
          id="copilot-input"
          aria-label="Ask the Copilot a question"
          placeholder="Ask about this project, route, file, result, or next step..."
          className="flex-1 rounded-md border border-bda-border bg-bda-panel px-3 py-2 text-sm text-bda-text"
          value={input}
          disabled={loading}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void handleSend()}
        />
        <button
          type="button"
          aria-label="Send message"
          className="rounded-md border border-bda-border p-2 hover:bg-bda-panel-hover disabled:opacity-50"
          disabled={loading || !input.trim()}
          onClick={() => void handleSend()}
        >
          <Send className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}
