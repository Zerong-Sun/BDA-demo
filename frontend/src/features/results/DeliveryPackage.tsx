import { artifactUrl, deliveryPackageDownloadUrl } from '../../lib/api/client'
import type { DeliveryPackageData } from '../../lib/api/projects'

interface DeliveryPackageProps {
  packageData: DeliveryPackageData | null
  loading?: boolean
  projectId: string
}

const DEFAULT_ITEMS = [
  'Executive summary and route rationale',
  'FASTA and score table for ordered sequences',
  'High-priority structures and experimental readouts',
  'Round-two model update brief',
]

function parseConstraints(raw: DeliveryPackageData['redesign_constraints']) {
  if (!raw) return {}
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw) as Record<string, unknown>
    } catch {
      return {}
    }
  }
  return raw
}

function parseCandidateIds(raw: DeliveryPackageData['candidate_ids']) {
  if (Array.isArray(raw)) return raw
  try {
    return JSON.parse(raw) as string[]
  } catch {
    return []
  }
}

export function DeliveryPackage({ packageData, loading, projectId }: DeliveryPackageProps) {
  const constraints = parseConstraints(packageData?.redesign_constraints)
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

  const downloads = [
    { label: 'Report PDF', path: packageData?.report_file },
    { label: 'FASTA bundle', path: packageData?.fasta_file },
    { label: 'Structure bundle', path: packageData?.structure_bundle },
    { label: 'Score table', path: packageData?.score_table },
  ].filter((item) => item.path)

  return (
    <article className="bda-card bda-sticky-panel bda-scroll-area max-h-[calc(100vh-8rem)]">
      <div className="bda-card-header">
        <h2 className="text-lg font-semibold">Delivery package</h2>
        {packageData ? (
          <span className="rounded border border-bda-border px-2 py-1 text-xs text-bda-muted">
            {parseCandidateIds(packageData.candidate_ids).length} candidates
          </span>
        ) : null}
      </div>
      <div className="bda-card-body">
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
          {downloads.length ? (
            <ul className="mt-4 space-y-2 text-sm">
              {downloads.map((item) => (
                <li key={item.label}>
                  <a
                    className="text-bda-cyan hover:underline"
                    href={artifactUrl(String(item.path))}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Download {item.label}
                  </a>
                </li>
              ))}
            </ul>
          ) : null}
          {packageData ? (
            <p className="mt-3 text-xs text-bda-muted">
              Candidates: {parseCandidateIds(packageData.candidate_ids).join(', ')}
            </p>
          ) : null}
          <div className="mt-4 rounded-md border border-bda-border bg-bda-bg p-3">
            <h3 className="text-sm font-medium text-bda-text">Round-two design brief</h3>
            <ul className="mt-2 space-y-1 text-sm text-bda-muted">
              {briefItems.map((item) => (
                <li key={item} className="break-words">
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <a
            className="mt-4 inline-flex text-sm text-bda-cyan hover:underline"
            href={deliveryPackageDownloadUrl(projectId)}
            target="_blank"
            rel="noreferrer"
          >
            Download full ZIP package
          </a>
        </>
      )}
      </div>
    </article>
  )
}
