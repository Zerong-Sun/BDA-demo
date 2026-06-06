import { useState } from 'react'
import { matchSkill } from './skills/registry'
import { sendCopilotMessage } from '../../lib/api/copilot'

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

export function useCopilotChat(projectId?: string) {
  const [messages, setMessages] = useState<ChatMessage[]>(seedMessages)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const send = async (input: string) => {
    const trimmed = input.trim()
    if (!trimmed || loading) return

    const skill = matchSkill(trimmed)?.name
    const nextMessages: ChatMessage[] = [...messages, { role: 'user', content: trimmed }]
    setMessages(nextMessages)
    setLoading(true)
    setError(null)

    try {
      const response = await sendCopilotMessage({
        messages: nextMessages,
        project_id: projectId,
        skill,
      })
      setMessages((prev) => [...prev, { role: 'assistant', content: response.message }])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Copilot request failed'
      setError(message)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Copilot is unavailable. Start the backend API and retry.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  return { messages, loading, error, send }
}
