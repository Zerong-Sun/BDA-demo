import { fireEvent, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../../test/mocks/handlers'
import { renderWithProviders } from '../../test/renderWithProviders'
import { useAppStore } from '../../lib/store/appStore'
import { Topbar } from './Topbar'

describe('Topbar logout', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    window.location.hash = '/experiments?project=proj_live'
    useAppStore.setState({
      activeProjectId: 'proj_live',
      workflowRunIdsByProject: { proj_live: 'run_live' },
      language: 'zh',
      copilotOpen: false,
    })
    server.use(
      http.get('/api/v1/projects', () =>
        HttpResponse.json({
          data: {
            items: [
              {
                project_id: 'proj_live',
                project_name: 'Live Project',
                project_type: 'protein_design',
                status: 'active',
                owner_id: 'user_admin',
                summary: 'Still available',
                local_workspace: {
                  backend: 'local',
                  status: 'ready',
                  root: 'projects/proj_live',
                  manifest: 'projects/proj_live/manifest.json',
                },
              },
            ],
            total: 1,
            limit: 50,
            offset: 0,
          },
          trace_id: 'test',
        }),
      ),
    )
  })

  it('clears only authentication session data', () => {
    sessionStorage.setItem('bda_token', 'token')
    sessionStorage.setItem(
      'bda_user',
      JSON.stringify({ username: 'admin', display_name: 'Admin User' }),
    )

    renderWithProviders(<Topbar />)

    fireEvent.click(screen.getByRole('button', { name: 'Logout' }))

    expect(sessionStorage.getItem('bda_token')).toBeNull()
    expect(sessionStorage.getItem('bda_user')).toBeNull()
    expect(useAppStore.getState().activeProjectId).toBe('proj_live')
    expect(useAppStore.getState().workflowRunIdsByProject.proj_live).toBe('run_live')
    expect(useAppStore.getState().language).toBe('zh')
    expect(useAppStore.getState().copilotOpen).toBe(false)
    expect(window.location.hash).toContain('/login')
  })
})
