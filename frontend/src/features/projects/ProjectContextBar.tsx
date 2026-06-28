import { Link } from 'react-router-dom'
import { FlaskConical } from 'lucide-react'
import { useProjectContext } from '../../lib/hooks/useProjectContext'

export function ProjectContextBar() {
  const { activeProject } = useProjectContext()
  if (!activeProject) return null

  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-bda-cyan/25 bg-bda-cyan/5 px-4 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <FlaskConical className="h-4 w-4 shrink-0 text-bda-cyan" />
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-wide text-bda-cyan">Active research project</p>
          <p className="truncate text-sm font-medium text-bda-text">{activeProject.project_name}</p>
        </div>
        <span className="rounded border border-bda-border px-2 py-0.5 text-[10px] text-bda-muted">
          {activeProject.project_type} · {activeProject.status}
        </span>
      </div>
      <Link to="/experiments" className="text-xs text-bda-cyan hover:underline">
        Switch or create project
      </Link>
    </div>
  )
}
