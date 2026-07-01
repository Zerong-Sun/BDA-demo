import { useMutation, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'
import { deleteProject, type Project } from '../api/projects'
import { useAppStore } from '../store/appStore'
import { useProjectContext } from './useProjectContext'

const PROJECT_DEPENDENT_PATHS = new Set(['/workflow', '/candidates', '/results'])

export const DELETE_PROJECT_CONFIRMATION =
  'Move "{projectName}" to project trash?\n\nThe database project and its linked workflow data will be removed. The local workspace will be moved to backend/artifacts/project_trash for recovery, not physically emptied.'

export function invalidateDeletedProjectQueries(queryClient: QueryClient, projectId: string) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ['projects'] }),
    queryClient.invalidateQueries({ queryKey: ['project-overview', projectId] }),
    queryClient.invalidateQueries({ queryKey: ['workflow-run', 'latest', projectId] }),
    queryClient.invalidateQueries({ queryKey: ['workflow-runs', projectId] }),
    queryClient.invalidateQueries({ queryKey: ['project-artifacts', projectId] }),
    queryClient.invalidateQueries({ queryKey: ['candidates', projectId] }),
    queryClient.invalidateQueries({ queryKey: ['candidate-funnel', projectId] }),
    queryClient.invalidateQueries({ queryKey: ['experiment-results', projectId] }),
    queryClient.invalidateQueries({ queryKey: ['results-summary', projectId] }),
    queryClient.invalidateQueries({ queryKey: ['delivery-package', projectId] }),
    queryClient.invalidateQueries({ queryKey: ['campaigns', projectId] }),
    queryClient.invalidateQueries({ queryKey: ['project-research-summary', projectId] }),
  ])
}

export function useDeleteProjectLifecycle() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const location = useLocation()
  const clearProjectState = useAppStore((state) => state.clearProjectState)
  const { projectId, setProjectId } = useProjectContext()

  const mutation = useMutation({
    mutationFn: (deleteProjectId: string) => deleteProject(deleteProjectId),
    onSuccess: async (_result, deletedProjectId) => {
      clearProjectState(deletedProjectId)
      if (projectId === deletedProjectId) {
        setProjectId('')
        if (PROJECT_DEPENDENT_PATHS.has(location.pathname)) {
          navigate('/experiments', { replace: true })
        }
      }
      await invalidateDeletedProjectQueries(queryClient, deletedProjectId)
    },
  })

  const confirmAndDeleteProject = (project: Project) => {
    const ok = window.confirm(
      DELETE_PROJECT_CONFIRMATION.replace('{projectName}', project.project_name),
    )
    if (ok) mutation.mutate(project.project_id)
  }

  return {
    ...mutation,
    confirmAndDeleteProject,
    deletingProjectId: mutation.variables ?? null,
  }
}
