import { useEffect, useMemo, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listProjects } from '../api/projects'
import { useAppStore } from '../store/appStore'

const DEFAULT_PROJECT_ID = 'proj_pd1_0423'

export function useProjectContext() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeProjectId = useAppStore((s) => s.activeProjectId)
  const setActiveProjectId = useAppStore((s) => s.setActiveProjectId)

  const { data: projects = [], isLoading: projectsLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: listProjects,
    staleTime: 30_000,
  })

  const urlProjectId = searchParams.get('project')
  const syncedRef = useRef(false)

  useEffect(() => {
    if (syncedRef.current || projectsLoading) return
    syncedRef.current = true

    if (urlProjectId && projects.some((p) => p.project_id === urlProjectId)) {
      if (urlProjectId !== activeProjectId) {
        setActiveProjectId(urlProjectId)
      }
      return
    }

    if (!urlProjectId && activeProjectId && projects.some((p) => p.project_id === activeProjectId)) {
      const next = new URLSearchParams(searchParams)
      next.set('project', activeProjectId)
      setSearchParams(next, { replace: true })
    }
  }, [urlProjectId, activeProjectId, projects, projectsLoading, searchParams, setActiveProjectId, setSearchParams])

  const projectId = useMemo(() => {
    const exists = (id: string) => projects.some((p) => p.project_id === id)
    if (exists(activeProjectId)) return activeProjectId
    if (urlProjectId && exists(urlProjectId)) return urlProjectId
    return projects[0]?.project_id ?? DEFAULT_PROJECT_ID
  }, [activeProjectId, urlProjectId, projects])

  const activeProject = projects.find((p) => p.project_id === projectId) ?? null

  const setProjectId = (nextProjectId: string) => {
    syncedRef.current = true
    setActiveProjectId(nextProjectId)
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
