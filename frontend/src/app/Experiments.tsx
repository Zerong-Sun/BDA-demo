import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { LoaderCircle, Trash2 } from 'lucide-react'
import { getProjectOverview } from '../lib/api/projects'
import { useDeleteProjectLifecycle } from '../lib/hooks/useDeleteProjectLifecycle'
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
    action: 'Open PD-1 project',
  },
  proj_nanocage_0518: {
    preview: 'Programmable protein cage cargo display planning',
    action: 'Open nanocage project',
  },
  proj_enzyme_0507: {
    preview: 'Expression and thermal-shift constrained scaffold repair',
    action: 'Open enzyme repair project',
  },
}

function projectCard(project: Project) {
  const configured = projectCards[project.project_id]
  if (configured) return configured
  const normalized = `${project.project_id} ${project.project_name} ${project.project_type}`.toLowerCase()
  if (normalized.includes('sweetprotein') || normalized.includes('sweet_protein')) {
    return {
      preview: 'Sweet protein RFdiffusion run, uploaded inputs, LSF jobs, and downstream review',
      action: 'Open sweet-protein project',
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
  onDelete,
  isDeleting,
}: {
  project: Project
  openLabel: string
  onOpen: (projectId: string) => void
  onDelete: (project: Project) => void
  isDeleting: boolean
}) {
  const card = projectCard(project)
  return (
    <article className="flex min-h-[21rem] flex-col overflow-hidden rounded-lg border border-bda-border bg-bda-panel">
      <div className="flex h-36 items-center justify-center bg-gradient-to-br from-bda-panel-hover to-bda-bg px-4 text-center text-sm text-bda-muted">
        {card.preview}
      </div>
      <div className="flex min-h-0 flex-1 flex-col space-y-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <h2 className="line-clamp-2 min-w-0 text-lg font-semibold leading-snug">{project.project_name}</h2>
          <StatusPill label={project.status} tone={statusTone(project.status)} />
        </div>
        <p className="line-clamp-3 text-sm text-bda-muted">{project.summary || 'No project summary yet.'}</p>
        <div className="mt-auto flex flex-wrap items-center justify-between gap-2">
          <Link
            to={`/workflow?project=${encodeURIComponent(project.project_id)}`}
            className="inline-flex rounded-md border border-bda-border px-3 py-1.5 text-sm hover:bg-bda-panel-hover"
            onClick={() => onOpen(project.project_id)}
          >
            {card.action ?? openLabel}
          </Link>
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-md border border-bda-red/40 px-2.5 py-1.5 text-sm text-bda-red hover:bg-bda-red/10 disabled:opacity-50"
            disabled={isDeleting}
            onClick={() => onDelete(project)}
          >
            {isDeleting ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
            Move to trash
          </button>
        </div>
      </div>
    </article>
  )
}

export function ExperimentsPage() {
  const { t } = useI18n()
  const setCopilotOpen = useAppStore((s) => s.setCopilotOpen)
  const { projects, projectsLoading, projectsError, projectsQueryError, refetchProjects, projectId, setProjectId } =
    useProjectContext()
  const projectDelete = useDeleteProjectLifecycle()

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
          title="Research projects"
          description="Select or create a project. Workflows, candidates, experimental results, and delivery packages are archived under the active project."
          compact
        />
        {projectDelete.isSuccess ? (
          <p className="mt-2 text-xs text-bda-muted">
            Project moved to {projectDelete.data.workspace.trash_root ?? 'project trash'}.
          </p>
        ) : null}
        {projectDelete.isError ? (
          <p className="mt-2 text-xs text-bda-red">
            {projectDelete.error instanceof Error
              ? projectDelete.error.message
              : 'Project deletion failed. Check the backend service.'}
          </p>
        ) : null}
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
            <span className="text-xs text-bda-muted">Select or create a project to make its context available to Copilot.</span>
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
                onDelete={projectDelete.confirmAndDeleteProject}
                isDeleting={projectDelete.deletingProjectId === project.project_id && projectDelete.isPending}
              />
            ))}
          </div>
        )}
      </ApiState>
    </section>
  )
}
