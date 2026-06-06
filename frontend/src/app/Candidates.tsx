import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { listCandidates } from '../lib/api/candidates'
import { getCandidateFunnel } from '../lib/api/projects'
import { PageHead } from '../components/ui/PageHead'
import { CandidateFilters } from '../features/candidates/CandidateFilters'
import { CandidateTable } from '../features/candidates/CandidateTable'
import { CandidateDetail } from '../features/candidates/CandidateDetail'
import type { Candidate } from '../lib/schemas/candidate'
import { useAppStore } from '../lib/store/appStore'
import { useToastStore } from '../components/ui/Toast'

export function CandidatesPage() {
  const projectId = useAppStore((s) => s.activeProjectId)
  const showToast = useToastStore((s) => s.show)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('All')
  const [priorityOnly, setPriorityOnly] = useState(false)
  const [selected, setSelected] = useState<Candidate | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['candidates', projectId, search, status, priorityOnly],
    queryFn: () =>
      listCandidates(projectId, {
        search: search || undefined,
        status: status === 'All' ? undefined : status,
        decision: priorityOnly ? 'Anchor,Order,Retest' : undefined,
        limit: 10,
        sort: 'interface_score',
        order: 'desc',
      }),
  })

  const { data: funnel } = useQuery({
    queryKey: ['candidate-funnel', projectId],
    queryFn: () => getCandidateFunnel(projectId),
  })

  const candidates = useMemo(() => data?.items ?? [], [data])
  const totalCount = data?.total ?? candidates.length
  const activeCandidate = selected ?? candidates[0] ?? null

  const exportCsv = () => {
    if (!candidates.length) return
    const header = [
      'candidate_id',
      'family',
      'interface_score',
      'pred_kd',
      'plddt',
      'status',
      'decision',
    ]
    const rows = candidates.map((c) =>
      [
        c.candidate_id,
        c.family,
        c.interface_score,
        c.pred_kd,
        c.plddt,
        c.status,
        c.decision,
      ].join(','),
    )
    const blob = new Blob([[header.join(','), ...rows].join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'bda_candidates.csv'
    a.click()
    URL.revokeObjectURL(url)
    showToast('Candidate CSV exported', 'success')
  }

  return (
    <section>
      <PageHead
        eyebrow="BDA selection layer"
        title="Candidate table"
        actions={
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-md border border-bda-border px-3 py-2 text-sm hover:bg-bda-panel"
            onClick={exportCsv}
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
        }
      />

      <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-5">
        {(
          [
            ['Generated', funnel?.generated ?? '—'],
            ['Designed', funnel?.designed ?? '—'],
            ['Folded', funnel?.folded ?? '—'],
            ['Scored', funnel?.scored ?? '—'],
            ['Ordered', funnel?.ordered ?? '—'],
          ] as const
        ).map(([label, value]) => (
          <article key={label} className="rounded-lg border border-bda-border bg-bda-panel p-3">
            <span className="text-xs text-bda-muted">{label}</span>
            <strong className="mt-1 block text-xl">
              {typeof value === 'number' ? value.toLocaleString() : value}
            </strong>
          </article>
        ))}
      </div>

      <CandidateFilters
        search={search}
        status={status}
        priorityOnly={priorityOnly}
        onSearchChange={setSearch}
        onStatusChange={setStatus}
        onPriorityOnlyChange={setPriorityOnly}
      />

      {isLoading ? (
        <p className="text-sm text-bda-muted">Loading candidates...</p>
      ) : isError ? (
        <p className="text-sm text-bda-red">Failed to load candidates. Start the backend API on port 8100.</p>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
          <div className="space-y-4">
            <CandidateTable
              data={candidates}
              selectedId={activeCandidate?.candidate_id}
              onSelect={setSelected}
            />
            <article className="rounded-lg border border-bda-border bg-bda-panel p-4 text-sm text-bda-muted">
              Showing top {candidates.length} of {totalCount} candidates ranked by interface score and pLDDT.
              Anchor candidates are highlighted for round-two motif preservation.
            </article>
          </div>
          <CandidateDetail candidate={activeCandidate} />
        </div>
      )}
    </section>
  )
}
