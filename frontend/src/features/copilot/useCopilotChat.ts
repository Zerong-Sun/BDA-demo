import { matchSkill } from './skills/registry'
import { sendCopilotMessage, streamCopilotMessage } from '../../lib/api/copilot'
import { useAppStore, type CopilotChatMessage } from '../../lib/store/appStore'
import { useState } from 'react'

const MAX_COPILOT_HISTORY = 20

export function useCopilotChat(projectId?: string, pageContext?: string) {
  const messages = useAppStore((state) => state.copilotMessages)
  const setMessages = useAppStore((state) => state.setCopilotMessages)
  const resetMessages = useAppStore((state) => state.resetCopilotMessages)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const send = async (input: string) => {
    const trimmed = input.trim()
    if (!trimmed || loading) return

    const skill = matchSkill(trimmed)?.name
    const nextMessages: CopilotChatMessage[] = [...messages, { role: 'user', content: trimmed }]
    setMessages(nextMessages)
    setLoading(true)
    setError(null)

    const scopedMessages: CopilotChatMessage[] = pageContext
      ? [
          {
            role: 'system',
            content:
              `Current BDA UI context for this turn: ${pageContext}. ` +
              'Use it to preserve continuity across pages, but do not mention it unless it changes the answer.',
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
          content: `Copilot request failed: ${message}`,
        }
        return copy
      })
    } finally {
      setLoading(false)
    }
  }

  return { messages, loading, error, send, resetMessages }
}
