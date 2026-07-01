import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithProviders } from '../../test/renderWithProviders'
import { defaultCopilotMessages, useAppStore } from '../../lib/store/appStore'
import type { CopilotChatRequest } from '../../lib/api/copilot'
import { CopilotChat } from './CopilotChat'

vi.mock('../../lib/api/copilot', () => ({
  streamCopilotMessage: vi.fn(async (_payload: CopilotChatRequest, onChunk: (text: string) => void) => {
    onChunk('Route context carried forward.')
  }),
  sendCopilotMessage: vi.fn(),
}))

describe('CopilotChat', () => {
  beforeEach(() => {
    useAppStore.setState({ copilotMessages: defaultCopilotMessages })
  })

  it('keeps one conversation across drawer/page remounts', async () => {
    const rendered = renderWithProviders(<CopilotChat pageContext="route=/workflow; project_id=proj_test" />)

    fireEvent.change(screen.getByLabelText('Ask the Copilot a question'), {
      target: { value: 'Plan the next protein workflow step' },
    })
    fireEvent.click(screen.getByLabelText('Send message'))

    await waitFor(() => {
      expect(screen.getByText('Route context carried forward.')).toBeInTheDocument()
    })

    rendered.unmount()
    renderWithProviders(<CopilotChat pageContext="route=/results; project_id=proj_test" />)

    expect(screen.getByText('Plan the next protein workflow step')).toBeInTheDocument()
    expect(screen.getByText('Route context carried forward.')).toBeInTheDocument()
  })
})
