import { MetricCard } from '../../components/ui/MetricCard'
import type { ProjectOverview } from '../../lib/api/projects'
import { useI18n } from '../../lib/i18n'
import { useQuery } from '@tanstack/react-query'
import { getClusterHealth } from '../../lib/api/registry'

interface OverviewCardsProps {
  overview: ProjectOverview
}

export function OverviewCards({ overview }: OverviewCardsProps) {
  const { t } = useI18n()
  const { data: clusterHealth } = useQuery({
    queryKey: ['cluster-health'],
    queryFn: getClusterHealth,
    refetchInterval: 30_000,
  })

  const hitLabel = overview.results_summary?.hit_rate_label ?? '—'
  const computeLabel = overview.compute_status.label
  const computeAvailable = overview.compute_status.gpu_available || overview.compute_status.cpu_available
  const remoteConnected = clusterHealth?.mode === 'remote_lsf' && clusterHealth.connected

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
        value={remoteConnected || computeAvailable ? 'Connected' : 'Offline'}
        supporting={
          remoteConnected
            ? `南科大 LSF · ${clusterHealth.queues.length} queues visible`
            : computeLabel
        }
      />
      <MetricCard
        label={t.experiments.overview.nextAction}
        value="Continue"
        supporting={overview.next_action}
      />
    </div>
  )
}
