import type { ReactNode } from 'react'
import { ProjectChooser } from './ProjectChooser'
import { useProjectContext } from '../../lib/hooks/useProjectContext'

export function ProjectRequired({ children }: { children: ReactNode }) {
  const { hasProject, projectsLoading, hasStaleProjectReference } = useProjectContext()

  if (projectsLoading) {
    return <div className="rounded-lg border border-bda-border bg-bda-panel p-6 text-sm text-bda-muted">Loading research projects...</div>
  }
  if (!hasProject) {
    return (
      <ProjectChooser
        title="Select the research project for this workspace"
        description={
          hasStaleProjectReference
            ? 'The previous project is no longer available or was moved to trash. Select another project to continue.'
            : 'The selected project provides context across workflows, candidates, experimental results, and delivery pages. You may also create a new project here.'
        }
      />
    )
  }
  return children
}
