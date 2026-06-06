import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listProjects } from '../lib/api/projects'
import { PageHead } from '../components/ui/PageHead'
import { StatusPill, statusTone } from '../components/ui/StatusPill'
import { useAppStore } from '../lib/store/appStore'

export function ExperimentsPage() {
  const setActiveProjectId = useAppStore((s) => s.setActiveProjectId)
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: listProjects,
  })

  return (
    <section>
      <PageHead
        eyebrow="Project experiment list"
        title="BDA Experiments"
        actions={
          <Link to="/workflow" className="rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg">
            New experiment
          </Link>
        }
      />

      <section className="mb-6 rounded-lg border border-bda-border bg-bda-panel p-4">
        <p className="text-xs uppercase tracking-wide text-bda-cyan">AI Beagle Copilot</p>
        <h2 className="mt-1 text-xl font-semibold">From design brief to traceable loop</h2>
        <p className="mt-2 max-w-3xl text-sm text-bda-muted">
          Plan routes, adjust workflow thresholds, interpret BLI/SEC evidence, and push constraints into the next design round.
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <Link to="/workflow" className="rounded-md border border-bda-border px-3 py-2 text-sm hover:border-bda-cyan/50">
            Plan route → Workflow
          </Link>
          <Link to="/candidates" className="rounded-md border border-bda-border px-3 py-2 text-sm hover:border-bda-cyan/50">
            Review top candidates
          </Link>
          <Link to="/results" className="rounded-md border border-bda-border px-3 py-2 text-sm hover:border-bda-cyan/50">
            Interpret lab results
          </Link>
        </div>
      </section>

      {isLoading ? (
        <p className="text-sm text-bda-muted">Loading projects...</p>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          {projects.map((project) => (
            <article
              key={project.project_id}
              className="overflow-hidden rounded-lg border border-bda-border bg-bda-panel"
            >
              <div className="h-36 bg-gradient-to-br from-bda-panel-hover to-bda-bg" />
              <div className="space-y-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-lg font-semibold">{project.project_name}</h2>
                  <StatusPill label={project.status} tone={statusTone(project.status)} />
                </div>
                <p className="text-sm text-bda-muted">{project.summary}</p>
                <Link
                  to="/workflow"
                  className="inline-flex rounded-md border border-bda-border px-3 py-1.5 text-sm hover:bg-bda-panel-hover"
                  onClick={() => setActiveProjectId(project.project_id)}
                >
                  Open project
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
