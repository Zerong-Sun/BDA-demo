import { MetricCard } from '../../components/ui/MetricCard'
import type { ResultsSummary } from '../../lib/api/projects'

interface ResultsMetricsProps {
  summary: ResultsSummary | null
  loading?: boolean
}

export function ResultsMetrics({ summary, loading }: ResultsMetricsProps) {
  if (loading) {
    return <p className="mb-5 text-sm text-bda-muted">Loading results summary...</p>
  }

  if (!summary) {
    return (
      <div className="mb-5 rounded-lg border border-dashed border-bda-border bg-bda-panel p-4 text-sm text-bda-muted">
        Results summary is not available for this project yet.
      </div>
    )
  }

  return (
    <div className="mb-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        label="Hit rate"
        value={`${summary.hit_rate_pct}%`}
        supporting={summary.hit_rate_label}
      />
      <MetricCard
        label="Best Kd"
        value={summary.best_kd}
        supporting={
          summary.best_kd_candidate
            ? `${summary.best_kd_candidate} (BLI)`
            : 'No BLI measurement yet'
        }
      />
      <MetricCard
        label="Main failure"
        value={summary.main_failure}
        supporting={summary.main_failure_detail}
      />
      <MetricCard
        label="Decision"
        value={summary.decision}
        supporting={summary.decision_detail}
      />
    </div>
  )
}
