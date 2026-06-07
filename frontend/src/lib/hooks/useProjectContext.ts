import { useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listProjects } from '../api/projects'

const DEFAULT_PROJECT_ID = 'proj_pd1_0423'

export function useProjectContext() {
  const [searchParams, setSearchParams] = useSearchParams()

  const { data: projects = [], isLoading: projectsLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: listProjects,
    staleTime: 30_000,
  })

  const urlProjectId = searchParams.get('project')

  const projectId = useMemo(() => {
    const exists = (id: string) => projects.some((p) => p.project_id === id)
    if (urlProjectId && exists(urlProjectId)) return urlProjectId
    if (exists(DEFAULT_PROJECT_ID)) return DEFAULT_PROJECT_ID
    return projects[0]?.project_id ?? DEFAULT_PROJECT_ID
  }, [urlProjectId, projects])

  useEffect(() => {
    if (projectsLoading || !projectId) return
    if (projectId !== urlProjectId) {
      const next = new URLSearchParams(searchParams)
      next.set('project', projectId)
      setSearchParams(next, { replace: true })
    }
  }, [projectId, urlProjectId, projectsLoading, searchParams, setSearchParams])

  const activeProject = projects.find((p) => p.project_id === projectId) ?? null

  const setProjectId = (nextProjectId: string) => {
    const next = new URLSearchParams(searchParams)
    next.set('project', nextProjectId)
    setSearchParams(next)
  }

  return {
    projectId,
    activeProject,
    projects,
    projectsLoading,
    setProjectId,
  }
}
