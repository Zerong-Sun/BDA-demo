interface MetricCardProps {
  label: string
  value: string
  supporting?: string
}

export function MetricCard({ label, value, supporting }: MetricCardProps) {
  return (
    <article className="rounded-lg border border-bda-border bg-bda-panel p-4">
      <span className="text-xs uppercase tracking-wide text-bda-muted">{label}</span>
      <strong className="mt-2 block text-3xl font-semibold text-bda-text">{value}</strong>
      {supporting ? <p className="mt-1 text-sm text-bda-muted">{supporting}</p> : null}
    </article>
  )
}
