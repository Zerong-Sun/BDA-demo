import type { ExperimentResult } from '../../lib/schemas/candidate'

interface ValidationTableProps {
  results?: ExperimentResult[]
  loading?: boolean
  isError?: boolean
}

export function ValidationTable({ results, loading, isError }: ValidationTableProps) {
  if (loading) {
    return (
      <article className="rounded-lg border border-bda-border bg-bda-panel p-4">
        <p className="text-sm text-bda-muted">Loading validation readouts...</p>
      </article>
    )
  }

  if (isError) {
    return (
      <article className="rounded-lg border border-bda-border bg-bda-panel p-4">
        <p className="text-sm text-bda-red">Failed to load validation readouts.</p>
      </article>
    )
  }

  const rows =
    results && results.length > 0
      ? results.map((r) => [
          r.experiment_type,
          r.pass_status,
          r.conclusion ?? r.value ?? '—',
          r.failure_reason ?? '—',
        ])
      : []

  return (
    <article className="rounded-lg border border-bda-border bg-bda-panel p-4">
      <h2 className="mb-3 text-lg font-semibold">Validation readouts</h2>
      {rows.length === 0 ? (
        <p className="text-sm text-bda-muted">No experiment results uploaded yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-bda-muted">
              <tr>
                <th className="pb-2 pr-4">Step</th>
                <th className="pb-2 pr-4">Pass</th>
                <th className="pb-2 pr-4">Signal</th>
                <th className="pb-2">Implication</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.join('-')} className="border-t border-bda-border/70">
                  <td className="py-2 pr-4">{row[0]}</td>
                  <td className="py-2 pr-4">{row[1]}</td>
                  <td className="py-2 pr-4">{row[2]}</td>
                  <td className="py-2">{row[3]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  )
}
