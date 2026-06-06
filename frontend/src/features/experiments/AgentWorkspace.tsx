import { Link } from 'react-router-dom'
import { useI18n } from '../../lib/i18n'

interface AgentWorkspaceProps {
  projectId: string
}

export function AgentWorkspace({ projectId }: AgentWorkspaceProps) {
  const { t } = useI18n()
  const query = `?project=${encodeURIComponent(projectId)}`

  const panels = [
    {
      title: t.experiments.agent.planRoute,
      body: t.experiments.agent.planRouteBody,
      to: `/workflow${query}`,
    },
    {
      title: t.experiments.agent.adjustWorkflow,
      body: t.experiments.agent.adjustWorkflowBody,
      to: `/workflow${query}`,
    },
    {
      title: t.experiments.agent.interpretLab,
      body: t.experiments.agent.interpretLabBody,
      to: `/results${query}`,
    },
  ]

  return (
    <section className="mb-6 grid gap-3 lg:grid-cols-3">
      {panels.map((panel) => (
        <Link
          key={panel.title}
          to={panel.to}
          className="rounded-lg border border-bda-border bg-bda-panel p-4 hover:border-bda-cyan/40"
        >
          <h3 className="text-sm font-semibold text-bda-text">{panel.title}</h3>
          <p className="mt-2 text-sm text-bda-muted">{panel.body}</p>
        </Link>
      ))}
    </section>
  )
}
