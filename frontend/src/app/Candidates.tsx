import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { downloadCandidateStructures, listCandidates } from '../lib/api/candidates'
import { getCandidateFunnel } from '../lib/api/projects'
import { useProjectContext } from '../lib/hooks/useProjectContext'
import { useToastStore } from '../components/ui/toastStore'
import { useI18n } from '../lib/i18n'
import { PageHead } from '../components/ui/PageHead'
import { ApiState } from '../components/ui/ApiState'
import { CandidateFilters } from '../features/candidates/CandidateFilters'
import { CandidateTable } from '../features/candidates/CandidateTable'
import { CandidateDetail } from '../features/candidates/CandidateDetail'
import { ComputeStatusStrip } from '../features/workflow/ComputeStatusStrip'
import type { Candidate } from '../lib/schemas/candidate'
import { ProjectContextBar } from '../features/projects/ProjectContextBar'

const PAGE_SIZE = 10

export function CandidatesPage() {
  const { t } = useI18n()
  const { projectId } = useProjectContext()
  const showToast = useToastStore((s) => s.show)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('All')
  const [priorityOnly, setPriorityOnly] = useState(false)
  const [selected, setSelected] = useState<Candidate | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set())
  const [isDownloading, setIsDownloading] = useState(false)
  const [page, setPage] = useState(0)

  const {
    data,
    isLoading,
    isError,
    error: candidatesError,
    refetch,
  } = useQuery({
    queryKey: ['candidates', projectId, search, status, priorityOnly, page],
    queryFn: () =>
      listCandidates(projectId, {
        search: search || undefined,
        status: status === 'All' ? undefined : status,
        decision: priorityOnly ? 'Anchor,Order,Retest' : undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
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
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE))
  const activeCandidate = selected ?? candidates[0] ?? null
  const pageIds = useMemo(() => candidates.map((candidate) => candidate.candidate_id), [candidates])
  const selectedCount = selectedIds.size

  const exportCsv = () => {
    if (!candidates.length) return
    const header = [
      'candidate_id', 'family', 'interface_score', 'pred_kd', 'plddt',
      'solubility_score', 'clash_count', 'buried_sasa', 'status', 'decision',
    ]
    const rows = candidates.map((c) =>
      header.map((h) => (c as Record<string, unknown>)[h] ?? '').join(','),
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

  const toggleCandidate = (candidateId: string) => {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (next.has(candidateId)) {
        next.delete(candidateId)
      } else {
        next.add(candidateId)
      }
      return next
    })
  }

  const togglePage = () => {
    setSelectedIds((current) => {
      const next = new Set(current)
      const allSelected = pageIds.length > 0 && pageIds.every((candidateId) => next.has(candidateId))
      for (const candidateId of pageIds) {
        if (allSelected) {
          next.delete(candidateId)
        } else {
          next.add(candidateId)
        }
      }
      return next
    })
  }

  const downloadSelected = async () => {
    const ids = [...selectedIds]
    if (!ids.length) return
    setIsDownloading(true)
    try {
      await downloadCandidateStructures(ids, `${projectId}_selected_candidates.zip`)
      showToast(`Downloaded ${ids.length} candidate structure${ids.length === 1 ? '' : 's'}`, 'success')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Candidate download failed'
      showToast(message, 'error')
    } finally {
      setIsDownloading(false)
    }
  }

  const downloadPage = async () => {
    if (!pageIds.length) return
    setIsDownloading(true)
    try {
      await downloadCandidateStructures(pageIds, `${projectId}_page_${page + 1}_candidates.zip`)
      showToast(`Downloaded ${pageIds.length} visible candidate structures`, 'success')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Candidate download failed'
      showToast(message, 'error')
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <section>
      <ProjectContextBar />
      <PageHead
        eyebrow={t.candidates.eyebrow}
        title={t.candidates.title}
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border border-bda-border px-3 py-2 text-sm hover:bg-bda-panel"
              onClick={exportCsv}
            >
              <Download className="h-4 w-4" />
              {t.candidates.exportCsv}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border border-bda-border px-3 py-2 text-sm hover:bg-bda-panel disabled:opacity-50"
              disabled={!pageIds.length || isDownloading}
              onClick={() => void downloadPage()}
            >
              <Download className="h-4 w-4" />
              Download page
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
              disabled={!selectedCount || isDownloading}
              onClick={() => void downloadSelected()}
            >
              <Download className="h-4 w-4" />
              Download selected{selectedCount ? ` (${selectedCount})` : ''}
            </button>
          </div>
        }
      />
      <ComputeStatusStrip />

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
        onSearchChange={(value) => {
          setPage(0)
          setSearch(value)
        }}
        onStatusChange={(value) => {
          setPage(0)
          setStatus(value)
        }}
        onPriorityOnlyChange={(value) => {
          setPage(0)
          setPriorityOnly(value)
        }}
      />

      <ApiState isLoading={isLoading} isError={isError} error={candidatesError} onRetry={() => void refetch()}>
        <div className="grid min-h-0 gap-4 xl:h-[calc(100vh-22rem)] xl:min-h-[34rem] xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.9fr)]">
          <div className="flex min-h-[34rem] flex-col gap-4 overflow-hidden xl:min-h-0">
            <div className="shrink-0 flex flex-wrap items-center gap-2 rounded-lg border border-bda-border bg-bda-panel px-3 py-2 text-sm text-bda-muted">
              <span>{selectedCount} selected</span>
              <button
                type="button"
                className="rounded-md border border-bda-border px-2 py-1 text-bda-text hover:bg-bda-panel-hover"
                onClick={togglePage}
              >
                {pageIds.every((candidateId) => selectedIds.has(candidateId)) ? 'Clear page' : 'Select page'}
              </button>
              <button
                type="button"
                className="rounded-md border border-bda-border px-2 py-1 text-bda-text hover:bg-bda-panel-hover disabled:opacity-50"
                disabled={!selectedCount}
                onClick={() => setSelectedIds(new Set())}
              >
                Clear all
              </button>
            </div>
            <div className="min-h-0 flex-1">
              <CandidateTable
                data={candidates}
                selectedId={activeCandidate?.candidate_id}
                selectedIds={selectedIds}
                onSelect={setSelected}
                onToggleCandidate={toggleCandidate}
                onTogglePage={togglePage}
              />
            </div>
            <div className="shrink-0 flex items-center justify-between text-sm text-bda-muted">
              <span>
                Showing {page * PAGE_SIZE + 1}-{Math.min((page + 1) * PAGE_SIZE, totalCount)} of {totalCount}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="rounded-md border border-bda-border px-2 py-1 disabled:opacity-40"
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >
                  Previous
                </button>
                <button
                  type="button"
                  className="rounded-md border border-bda-border px-2 py-1 disabled:opacity-40"
                  disabled={page + 1 >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          </div>
          <CandidateDetail candidate={activeCandidate} projectId={projectId} />
        </div>
      </ApiState>
    </section>
  )
}
