import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getProjectOverview } from '../lib/api/projects'
import { useProjectContext } from '../lib/hooks/useProjectContext'
import { useAppStore } from '../lib/store/appStore'
import { useI18n } from '../lib/i18n'
import { PageHead } from '../components/ui/PageHead'
import { StatusPill } from '../components/ui/StatusPill'
import { statusTone } from '../components/ui/statusTone'
import { ApiState } from '../components/ui/ApiState'
import { OverviewCards } from '../features/experiments/OverviewCards'
import { AgentWorkspace } from '../features/experiments/AgentWorkspace'
import { ProjectChooser } from '../features/projects/ProjectChooser'
import type { Project } from '../lib/api/projects'

const projectCards: Record<string, { preview: string; action: string }> = {
  proj_pd1_0423: {
    preview: 'PD-1 binder structure preview and closed-loop validation',
    action: '打开 PD-1 项目',
  },
  proj_nanocage_0518: {
    preview: 'Programmable protein cage cargo display planning',
    action: '打开纳米笼项目',
  },
  proj_enzyme_0507: {
    preview: 'Expression and thermal-shift constrained scaffold repair',
    action: '打开酶修复项目',
  },
}

function projectCard(project: Project) {
  const configured = projectCards[project.project_id]
  if (configured) return configured
  const normalized = `${project.project_id} ${project.project_name} ${project.project_type}`.toLowerCase()
  if (normalized.includes('sweetprotein') || normalized.includes('sweet_protein')) {
    return {
      preview: 'Sweet protein RFdiffusion run, uploaded inputs, LSF jobs, and downstream review',
      action: '打开甜蛋白项目',
    }
  }
  return {
    preview: `${project.project_type} project`,
    action: null,
  }
}

function ProjectCard({
  project,
  openLabel,
  onOpen,
}: {
  project: Project
  openLabel: string
  onOpen: (projectId: string) => void
}) {
  const card = projectCard(project)
  return (
    <article className="overflow-hidden rounded-lg border border-bda-border bg-bda-panel">
      <div className="flex h-36 items-center justify-center bg-gradient-to-br from-bda-panel-hover to-bda-bg px-4 text-center text-sm text-bda-muted">
        {card.preview}
      </div>
      <div className="space-y-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <h2 className="text-lg font-semibold">{project.project_name}</h2>
          <StatusPill label={project.status} tone={statusTone(project.status)} />
        </div>
        <p className="text-sm text-bda-muted">{project.summary}</p>
        <Link
          to={`/workflow?project=${encodeURIComponent(project.project_id)}`}
          className="inline-flex rounded-md border border-bda-border px-3 py-1.5 text-sm hover:bg-bda-panel-hover"
          onClick={() => onOpen(project.project_id)}
        >
          {card.action ?? openLabel}
        </Link>
      </div>
    </article>
  )
}

export function ExperimentsPage() {
  const { t } = useI18n()
  const setCopilotOpen = useAppStore((s) => s.setCopilotOpen)
  const { projects, projectsLoading, projectsError, projectsQueryError, refetchProjects, projectId, setProjectId } =
    useProjectContext()

  const {
    data: overview,
    isLoading: overviewLoading,
    isError: overviewError,
    error: overviewQueryError,
    refetch,
  } = useQuery({
    queryKey: ['project-overview', projectId],
    queryFn: () => getProjectOverview(projectId),
    enabled: Boolean(projectId),
  })

  const query = projectId ? `?project=${encodeURIComponent(projectId)}` : ''

  return (
    <section>
      <PageHead
        eyebrow={t.experiments.eyebrow}
        title={t.experiments.title}
        actions={
          <Link to={`/workflow${query}`} className="rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg">
            {t.common.newExperiment}
          </Link>
        }
      />
      <div className="mb-6">
        <ProjectChooser
          title="实验项目"
          description="在这里选择或创建项目。工作流、候选物、实验结果和最终交付都会自动归档到当前项目。"
          compact
        />
      </div>
      <section className="mb-6 rounded-lg border border-bda-border bg-bda-panel p-4">
        <p className="text-xs uppercase tracking-wide text-bda-cyan">AI Beagle Copilot</p>
        <h2 className="mt-1 text-xl font-semibold">{t.experiments.copilotTitle}</h2>
        <p className="mt-2 max-w-3xl text-sm text-bda-muted">{t.experiments.copilotBody}</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg"
            onClick={() => setCopilotOpen(true)}
          >
            Open Copilot chat
          </button>
          {overview ? (
            <div className="flex flex-wrap gap-2 text-xs text-bda-muted">
              <span className="rounded border border-bda-border px-2 py-1">
                Candidates {overview.funnel.generated}
              </span>
              <span className="rounded border border-bda-border px-2 py-1">
                Ordered {overview.funnel.ordered}
              </span>
              <span className="rounded border border-bda-border px-2 py-1">
                Results {overview.results_summary?.hit_count ?? 0}
              </span>
              <span className="rounded border border-bda-border px-2 py-1">
                {overview.next_action || 'No recommended action yet'}
              </span>
            </div>
          ) : (
            <span className="text-xs text-bda-muted">选择或创建项目后，Copilot 会读取当前项目上下文。</span>
          )}
        </div>
      </section>

      {projectId ? <ApiState
        isLoading={overviewLoading}
        isError={overviewError}
        error={overviewQueryError}
        isEmpty={!overviewLoading && !overviewError && !overview}
        emptyMessage={t.common.loading}
        onRetry={() => void refetch()}
      >
        {overview ? <OverviewCards overview={overview} /> : null}
      </ApiState> : null}

      {projectId ? <AgentWorkspace projectId={projectId} /> : null}

      <ApiState
        isLoading={projectsLoading}
        isError={projectsError}
        error={projectsQueryError}
        onRetry={() => void refetchProjects()}
      >
        {projects.length === 0 ? (
          <p className="text-sm text-bda-muted">No projects configured. Run `python3 backend/scripts/init_db.py`.</p>
        ) : (
          <div className="grid gap-4 lg:grid-cols-3">
            {projects.map((project) => (
              <ProjectCard
                key={project.project_id}
                project={project}
                openLabel={t.common.openProject}
                onOpen={setProjectId}
              />
            ))}
          </div>
        )}
      </ApiState>
    </section>
  )
}
