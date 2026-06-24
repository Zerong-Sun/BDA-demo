import type { ReactNode } from 'react'
import { ProjectChooser } from './ProjectChooser'
import { useProjectContext } from '../../lib/hooks/useProjectContext'

export function ProjectRequired({ children }: { children: ReactNode }) {
  const { hasProject, projectsLoading } = useProjectContext()

  if (projectsLoading) {
    return <div className="rounded-lg border border-bda-border bg-bda-panel p-6 text-sm text-bda-muted">正在加载实验项目…</div>
  }
  if (!hasProject) {
    return (
      <ProjectChooser
        title="先选择工作所属的实验项目"
        description="选择后，当前项目会自动贯穿工作流、候选物、实验结果与交付页面。也可以在这里创建新项目。"
      />
    )
  }
  return children
}
