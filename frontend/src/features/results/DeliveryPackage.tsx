import type { DeliveryPackageData } from '../../lib/api/projects'

interface DeliveryPackageProps {
  packageData: DeliveryPackageData | null
  loading?: boolean
}

const DEFAULT_ITEMS = [
  'Executive summary and route rationale',
  'FASTA and score table for ordered sequences',
  'High-priority structures and experimental readouts',
  'Round-two model update brief',
]

export function DeliveryPackage({ packageData, loading }: DeliveryPackageProps) {
  const constraints = packageData?.redesign_constraints ?? {}
  const preserveCandidate =
    typeof constraints.preserve_candidate === 'string' ? constraints.preserve_candidate : 'PD1Binder_c4361'

  const briefItems = [
    `Preserve ${preserveCandidate} interface motif and hydrogen-bond geometry`,
    constraints.increase_scaffold_diversity
      ? 'Increase scaffold diversity across F2, F5, and reserve families'
      : 'Maintain current scaffold diversity caps',
    constraints.penalize_exposed_hydrophobic_area
      ? 'Reduce hydrophobic patch exposure before MD selection'
      : 'Monitor developability metrics during selection',
    'Order 64 variants: 40 exploitation, 24 exploration',
  ]

  return (
    <article className="rounded-lg border border-bda-border bg-bda-panel p-4">
      <h2 className="mb-3 text-lg font-semibold">Delivery package</h2>
      {loading ? (
        <p className="text-sm text-bda-muted">Loading delivery package...</p>
      ) : (
        <>
          <ul className="space-y-2 text-sm text-bda-muted">
            {DEFAULT_ITEMS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          {packageData?.experiment_summary ? (
            <p className="mt-3 text-sm text-bda-text">{packageData.experiment_summary}</p>
          ) : null}
          <div className="mt-4 rounded-md border border-bda-border bg-bda-bg p-3">
            <h3 className="text-sm font-medium text-bda-text">Round-two design brief</h3>
            <ul className="mt-2 space-y-1 text-sm text-bda-muted">
              {briefItems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </>
      )}
    </article>
  )
}
