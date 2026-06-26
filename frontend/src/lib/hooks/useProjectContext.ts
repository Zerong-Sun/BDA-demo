import { useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listProjects } from '../api/projects'
import { useAppStore } from '../store/appStore'

export function useProjectContext() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeProjectId = useAppStore((state) => state.activeProjectId)
  const setActiveProjectId = useAppStore((state) => state.setActiveProjectId)

  const {
    data: projects = [],
    isLoading: projectsLoading,
    isError: projectsError,
    error: projectsQueryError,
    refetch: refetchProjects,
  } = useQuery({
    queryKey: ['projects'],
    queryFn: listProjects,
    staleTime: 30_000,
  })

  const urlProjectId = searchParams.get('project')

  const projectId = useMemo(() => {
    const exists = (id: string) => projects.some((p) => p.project_id === id)
    if (urlProjectId && exists(urlProjectId)) return urlProjectId
    if (activeProjectId && exists(activeProjectId)) return activeProjectId
    return ''
  }, [activeProjectId, urlProjectId, projects])

  useEffect(() => {
    if (projectsLoading || !projectId) return
    if (activeProjectId !== projectId) setActiveProjectId(projectId)
  }, [activeProjectId, projectId, projectsLoading, setActiveProjectId])

  const activeProject = projects.find((p) => p.project_id === projectId) ?? null

  const setProjectId = (nextProjectId: string) => {
    setActiveProjectId(nextProjectId)
    const next = new URLSearchParams(searchParams)
    if (nextProjectId) next.set('project', nextProjectId)
    else next.delete('project')
    setSearchParams(next)
  }

  return {
    projectId,
    activeProject,
    projects,
    projectsLoading,
    projectsError,
    projectsQueryError,
    refetchProjects,
    setProjectId,
    hasProject: Boolean(activeProject),
  }
}
