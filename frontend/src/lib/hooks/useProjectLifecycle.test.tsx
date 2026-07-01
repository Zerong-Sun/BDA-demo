import { fireEvent, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithProviders } from '../../test/renderWithProviders'
import { server } from '../../test/mocks/handlers'
import type { Project } from '../api/projects'
import { useAppStore } from '../store/appStore'
import { useDeleteProjectLifecycle } from './useDeleteProjectLifecycle'
import { useProjectContext } from './useProjectContext'

function makeProject(projectId: string): Project {
  return {
    project_id: projectId,
    project_name: `Project ${projectId}`,
    project_type: 'protein_design',
    status: 'active',
    owner_id: 'user_admin',
    summary: 'Lifecycle test project',
    local_workspace: {
      backend: 'local',
      status: 'ready',
      root: `projects/${projectId}`,
      manifest: `projects/${projectId}/manifest.json`,
    },
  }
}

function mockProjectList(projects: Project[]) {
  server.use(
    http.get('/api/v1/projects', () =>
      HttpResponse.json({
        data: {
          items: projects,
          total: projects.length,
          limit: 50,
          offset: 0,
        },
        trace_id: 'test',
      }),
    ),
  )
}

function ProjectContextProbe() {
  const { hasStaleProjectReference, projectId } = useProjectContext()
  return (
    <div>
      <span data-testid="project-id">{projectId || 'none'}</span>
      <span data-testid="stale-project">
        {hasStaleProjectReference ? 'stale' : 'fresh'}
      </span>
    </div>
  )
}

function DeleteProjectProbe() {
  const { projects } = useProjectContext()
  const projectDelete = useDeleteProjectLifecycle()
  const project = projects[0] ?? null
  return (
    <button
      type="button"
      disabled={!project || projectDelete.isPending}
      onClick={() => project && projectDelete.confirmAndDeleteProject(project)}
    >
      Move to trash
    </button>
  )
}

describe('project lifecycle hooks', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    window.location.hash = '/'
    useAppStore.setState({
      activeProjectId: '',
      workflowRunIdsByProject: {},
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('self-heals stale URL and persisted active project references', async () => {
    mockProjectList([makeProject('proj_live')])
    useAppStore.setState({ activeProjectId: 'proj_missing' })
    window.location.hash = '/workflow?project=proj_missing'

    renderWithProviders(<ProjectContextProbe />)

    await waitFor(() => expect(screen.getByTestId('stale-project')).toHaveTextContent('stale'))
    expect(screen.getByTestId('project-id')).toHaveTextContent('none')
    expect(useAppStore.getState().activeProjectId).toBe('')
    expect(window.location.hash).not.toContain('project=proj_missing')
  })

  it('clears current project state, URL, and workflow cache when a project is moved to trash', async () => {
    mockProjectList([makeProject('proj_delete_test')])
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    useAppStore.setState({
      activeProjectId: 'proj_delete_test',
      workflowRunIdsByProject: { proj_delete_test: 'run_old' },
    })
    window.location.hash = '/workflow?project=proj_delete_test'

    renderWithProviders(<DeleteProjectProbe />)

    const deleteButton = await screen.findByRole('button', { name: 'Move to trash' })
    await waitFor(() => expect(deleteButton).not.toBeDisabled())
    fireEvent.click(deleteButton)

    await waitFor(() =>
      expect(useAppStore.getState().workflowRunIdsByProject.proj_delete_test).toBeUndefined(),
    )
    expect(useAppStore.getState().activeProjectId).toBe('')
    expect(window.location.hash).toContain('/experiments')
    expect(window.location.hash).not.toContain('project=proj_delete_test')
  })
})
