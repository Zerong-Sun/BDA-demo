import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getProjectOverview } from '../lib/api/projects'
import { useProjectContext } from '../lib/hooks/useProjectContext'
import { useI18n } from '../lib/i18n'
import { PageHead } from '../components/ui/PageHead'
import { StatusPill, statusTone } from '../components/ui/StatusPill'
import { LoopStepper } from '../components/ui/LoopStepper'
import { ApiState } from '../components/ui/ApiState'
import { OverviewCards } from '../features/experiments/OverviewCards'
import { AgentWorkspace } from '../features/experiments/AgentWorkspace'

export function ExperimentsPage() {
  const { t } = useI18n()
  const { projects, projectsLoading, projectId, setProjectId } = useProjectContext()

  const {
    data: overview,
    isLoading: overviewLoading,
    isError: overviewError,
    refetch,
  } = useQuery({
    queryKey: ['project-overview', projectId],
    queryFn: () => getProjectOverview(projectId),
  })

  const query = `?project=${encodeURIComponent(projectId)}`

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
      <LoopStepper />

      <section className="mb-6 rounded-lg border border-bda-border bg-bda-panel p-4">
        <p className="text-xs uppercase tracking-wide text-bda-cyan">AI Beagle Copilot</p>
        <h2 className="mt-1 text-xl font-semibold">{t.experiments.copilotTitle}</h2>
        <p className="mt-2 max-w-3xl text-sm text-bda-muted">{t.experiments.copilotBody}</p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <Link to={`/workflow${query}`} className="rounded-md border border-bda-border px-3 py-2 text-sm hover:border-bda-cyan/50">
            {t.experiments.planRoute} → Workflow
          </Link>
          <Link to={`/candidates${query}`} className="rounded-md border border-bda-border px-3 py-2 text-sm hover:border-bda-cyan/50">
            {t.experiments.reviewCandidates}
          </Link>
          <Link to={`/results${query}`} className="rounded-md border border-bda-border px-3 py-2 text-sm hover:border-bda-cyan/50">
            {t.experiments.interpretResults}
          </Link>
        </div>
      </section>

      <ApiState
        isLoading={overviewLoading}
        isError={overviewError}
        isEmpty={!overviewLoading && !overviewError && !overview}
        emptyMessage={t.common.loading}
        onRetry={() => void refetch()}
      >
        {overview ? <OverviewCards overview={overview} /> : null}
      </ApiState>

      <AgentWorkspace projectId={projectId} />

      <ApiState isLoading={projectsLoading}>
        {projects.length === 0 ? (
          <p className="text-sm text-bda-muted">No projects configured. Run `python3 backend/scripts/init_db.py`.</p>
        ) : (
          <div className="grid gap-4 lg:grid-cols-3">
            {projects.map((project) => (
              <article
                key={project.project_id}
                className="overflow-hidden rounded-lg border border-bda-border bg-bda-panel"
              >
                <div className="flex h-36 items-center justify-center bg-gradient-to-br from-bda-panel-hover to-bda-bg px-4 text-center text-sm text-bda-muted">
                  {project.project_id === 'proj_pd1_0423'
                    ? 'PD-1 binder structure preview'
                    : `${project.project_type} project`}
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
                    onClick={() => setProjectId(project.project_id)}
                  >
                    {t.common.openProject}
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </ApiState>
    </section>
  )
}
