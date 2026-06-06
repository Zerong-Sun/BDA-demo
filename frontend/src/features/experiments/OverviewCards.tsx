import { MetricCard } from '../../components/ui/MetricCard'
import type { ProjectOverview } from '../../lib/api/projects'
import { useI18n } from '../../lib/i18n'

interface OverviewCardsProps {
  overview: ProjectOverview
}

export function OverviewCards({ overview }: OverviewCardsProps) {
  const { t } = useI18n()

  const hitLabel = overview.results_summary?.hit_rate_label ?? '—'
  const computeLabel = overview.compute_status.label
  const computeAvailable = overview.compute_status.gpu_available || overview.compute_status.cpu_available

  return (
    <div className="mb-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        label={t.experiments.overview.activeProject}
        value={overview.project.project_name}
        supporting={overview.project.status}
      />
      <MetricCard
        label={t.experiments.overview.bindingPositives}
        value={hitLabel}
        supporting="BLI validation readout"
      />
      <MetricCard
        label={t.experiments.overview.computeAccess}
        value={computeAvailable ? 'Connected' : 'Offline'}
        supporting={computeLabel}
      />
      <MetricCard
        label={t.experiments.overview.nextAction}
        value="Continue"
        supporting={overview.next_action}
      />
    </div>
  )
}
