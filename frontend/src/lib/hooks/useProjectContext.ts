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

  const sortedProjects = useMemo(() => {
    const priority = (project: (typeof projects)[number]) => {
      if (project.status === 'running' && project.owner_id && project.owner_id !== 'demo-user') return 0
      if (project.status === 'running') return 1
      if (project.project_id === 'proj_pd1_0423') return 2
      return 3
    }
    return [...projects].sort((a, b) => priority(a) - priority(b) || a.project_name.localeCompare(b.project_name))
  }, [projects])

  const urlProjectId = searchParams.get('project')

  const projectId = useMemo(() => {
    const exists = (id: string) => sortedProjects.some((p) => p.project_id === id)
    if (urlProjectId && exists(urlProjectId)) return urlProjectId
    if (activeProjectId && exists(activeProjectId)) return activeProjectId
    return ''
  }, [activeProjectId, urlProjectId, sortedProjects])

  useEffect(() => {
    if (projectsLoading || !projectId) return
    if (activeProjectId !== projectId) setActiveProjectId(projectId)
  }, [activeProjectId, projectId, projectsLoading, setActiveProjectId])

  const activeProject = sortedProjects.find((p) => p.project_id === projectId) ?? null

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
    projects: sortedProjects,
    projectsLoading,
    projectsError,
    projectsQueryError,
    refetchProjects,
    setProjectId,
    hasProject: Boolean(activeProject),
  }
}
