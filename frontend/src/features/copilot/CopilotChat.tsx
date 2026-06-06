import { useState } from 'react'
import { Send } from 'lucide-react'
import { matchSkill } from './skills/registry'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

const seedMessages: ChatMessage[] = [
  {
    role: 'user',
    content: 'Based on current scores, which candidates should enter the experimental queue?',
  },
  {
    role: 'assistant',
    content:
      'Prioritize PD1Binder_c4361, PD1Binder_a0172, and PD1Binder_b1923. They balance interface score, pLDDT, and lower aggregation risk.',
  },
]

function demoReply(input: string): string {
  const skill = matchSkill(input)
  if (skill?.name === 'workflow-adjust') {
    return 'Raise solubility threshold to 88, add hydrophobic patch penalty, and cap each scaffold family at 6 ordered variants.'
  }
  if (skill?.name === 'result-interpret') {
    return '9/48 BLI-positive; SEC aggregation is the main QC loss. Preserve c4361 motif and penalize exposed hydrophobic area in round two.'
  }
  if (skill?.name === 'paper-reader') {
    return 'Paper database integration is reserved for Phase 2. I can still summarize indexed methods once DeepSeek is connected.'
  }
  return 'Demo Copilot is active. Connect DeepSeek in Phase 2 for live reasoning over project data and papers.'
}

export function CopilotChat() {
  const [messages, setMessages] = useState<ChatMessage[]>(seedMessages)
  const [input, setInput] = useState('Explain why c4361 should anchor round two')

  const send = () => {
    const trimmed = input.trim()
    if (!trimmed) return
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: trimmed },
      { role: 'assistant', content: demoReply(trimmed) },
    ])
    setInput('')
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
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
        />
        <button
          type="button"
          className="rounded-md border border-bda-border p-2 hover:bg-bda-panel-hover"
          onClick={send}
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
