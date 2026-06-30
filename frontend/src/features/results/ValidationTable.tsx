import type { ExperimentResult } from '../../lib/schemas/candidate'

interface ValidationTableProps {
  results?: ExperimentResult[]
  loading?: boolean
  isError?: boolean
}

export function ValidationTable({ results, loading, isError }: ValidationTableProps) {
  if (loading) {
    return (
      <article className="bda-card p-4">
        <p className="text-sm text-bda-muted">Loading validation readouts...</p>
      </article>
    )
  }

  if (isError) {
    return (
      <article className="bda-card p-4">
        <p className="text-sm text-bda-red">Failed to load validation readouts.</p>
      </article>
    )
  }

  const rows =
    results && results.length > 0
      ? results.map((r) => ({
          id: r.result_id,
          cells: [
            r.experiment_type,
            r.pass_status,
            r.conclusion ?? r.value ?? '—',
            r.failure_reason ?? '—',
          ],
        }))
      : []

  return (
    <article className="bda-card flex min-h-0 flex-col">
      <div className="bda-card-header">
        <h2 className="text-lg font-semibold">Validation readouts</h2>
        <span className="rounded border border-bda-border px-2 py-1 text-xs text-bda-muted">
          {rows.length} rows
        </span>
      </div>
      {rows.length === 0 ? (
        <p className="p-4 text-sm text-bda-muted">No experiment results uploaded yet.</p>
      ) : (
        <div className="bda-table-shell bda-table-sticky max-h-[52vh]">
          <table className="min-w-[720px] text-sm">
            <thead className="bg-bda-bg text-left text-xs uppercase tracking-wide text-bda-muted">
              <tr>
                <th className="px-4 py-2">Step</th>
                <th className="px-4 py-2">Pass</th>
                <th className="px-4 py-2">Signal</th>
                <th className="px-4 py-2">Implication</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t border-bda-border/70">
                  <td className="px-4 py-2">{row.cells[0]}</td>
                  <td className="px-4 py-2">{row.cells[1]}</td>
                  <td className="max-w-xs break-words px-4 py-2">{row.cells[2]}</td>
                  <td className="max-w-xs break-words px-4 py-2">{row.cells[3]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  )
}
