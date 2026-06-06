import { useState } from 'react'
import { Send } from 'lucide-react'
import { useCopilotChat } from './useCopilotChat'
import { useProjectContext } from '../../lib/hooks/useProjectContext'

export function CopilotChat() {
  const { projectId } = useProjectContext()
  const { messages, loading, send } = useCopilotChat(projectId)
  const [input, setInput] = useState('Explain why c4361 should anchor round two')

  const handleSend = async () => {
    const trimmed = input.trim()
    if (!trimmed) return
    setInput('')
    await send(trimmed)
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((msg, idx) => (
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
        <input
          className="flex-1 rounded-md border border-bda-border bg-bda-panel px-3 py-2 text-sm"
          value={input}
          disabled={loading}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void handleSend()}
        />
        <button
          type="button"
          className="rounded-md border border-bda-border p-2 hover:bg-bda-panel-hover disabled:opacity-50"
          disabled={loading}
          onClick={() => void handleSend()}
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
