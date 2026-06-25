import { useState } from 'react'
import { matchSkill } from './skills/registry'
import { sendCopilotMessage, streamCopilotMessage } from '../../lib/api/copilot'

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

const seedMessages: ChatMessage[] = [
  {
    role: 'assistant',
    content: 'Describe the current project goal, evidence question, workflow decision, or experimental result you want to review.',
  },
]

const MAX_COPILOT_HISTORY = 20

export function useCopilotChat(projectId?: string, pageContext?: string) {
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

    const scopedMessages: ChatMessage[] = pageContext
      ? [
          {
            role: 'system',
            content: `Page context available to Copilot: ${pageContext}`,
          },
          ...nextMessages.slice(-MAX_COPILOT_HISTORY),
        ]
      : nextMessages.slice(-MAX_COPILOT_HISTORY)

    const payload = {
      messages: scopedMessages,
      project_id: projectId,
      skill,
    }

    try {
      let streamed = ''
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }])
      await streamCopilotMessage(payload, (chunk) => {
        streamed += chunk
        setMessages((prev) => {
          const copy = [...prev]
          copy[copy.length - 1] = { role: 'assistant', content: streamed }
          return copy
        })
      })
      if (!streamed) {
        const response = await sendCopilotMessage(payload)
        setMessages((prev) => {
          const copy = [...prev]
          copy[copy.length - 1] = { role: 'assistant', content: response.message }
          return copy
        })
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Copilot request failed'
      setError(message)
      setMessages((prev) => {
        const copy = [...prev]
        copy[copy.length - 1] = {
          role: 'assistant',
          content: 'Copilot is unavailable. Start the backend API and retry.',
        }
        return copy
      })
    } finally {
      setLoading(false)
    }
  }

  return { messages, loading, error, send }
}
