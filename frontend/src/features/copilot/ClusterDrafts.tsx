import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Download, LoaderCircle, Play, RefreshCw, Terminal } from 'lucide-react'
import {
  confirmClusterDraft,
  downloadClusterOutput,
  getClusterDraft,
  listClusterDrafts,
  type ClusterDraft,
} from '../../lib/api/copilot'
import { formatBytes } from '../../lib/schemas/artifact'

function DraftCard({ draft }: { draft: ClusterDraft }) {
  const queryClient = useQueryClient()
  const confirm = useMutation({
    mutationFn: () => confirmClusterDraft(draft.draft_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cluster-drafts'] }),
  })
  const refresh = useMutation({
    mutationFn: () => getClusterDraft(draft.draft_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cluster-drafts'] }),
  })

  return (
    <article className="space-y-2 rounded-md border border-bda-border bg-bda-panel p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <strong className="text-sm text-bda-text">{draft.job_name}</strong>
          <p className="text-xs text-bda-muted">
            {draft.queue} · CPU {draft.cpu_count} · GPU {draft.gpu_count}
            {draft.external_id ? ` · LSF ${draft.external_id}` : ''}
          </p>
        </div>
        <span className="rounded border border-bda-border px-2 py-0.5 text-[10px] uppercase text-bda-cyan">
          {draft.status}
        </span>
      </div>
      {draft.rationale ? <p className="text-xs text-bda-muted">{draft.rationale}</p> : null}
      <details>
        <summary className="cursor-pointer text-xs text-bda-cyan">Review LSF script</summary>
        <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded bg-black/30 p-2 text-[11px] text-bda-muted">
          {draft.script}
        </pre>
        <p className="mt-1 break-all text-[10px] text-bda-muted">SHA-256: {draft.script_sha256}</p>
      </details>
      <div className="flex flex-wrap gap-2">
        {draft.status === 'awaiting_confirmation' ? (
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded bg-bda-green px-2.5 py-1.5 text-xs font-medium text-bda-bg disabled:opacity-50"
            disabled={confirm.isPending}
            onClick={() => confirm.mutate()}
          >
            {confirm.isPending ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
            Confirm and submit
          </button>
        ) : (
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded border border-bda-border px-2.5 py-1.5 text-xs text-bda-text"
            disabled={refresh.isPending}
            onClick={() => refresh.mutate()}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refresh.isPending ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        )}
      </div>
      {confirm.isError ? <p className="text-xs text-bda-red">Submission failed. Check SSH session and script.</p> : null}
      {draft.logs ? (
        <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded bg-black/30 p-2 text-[11px] text-bda-muted">
          {draft.logs}
        </pre>
      ) : null}
      {draft.output_files?.length ? (
        <div className="space-y-1">
          {draft.output_files.map((file) => (
            <button
              type="button"
              key={file.path}
              onClick={() => void downloadClusterOutput(draft.draft_id, file.path)}
              className="flex w-full items-center justify-between gap-2 text-left text-xs text-bda-cyan hover:underline"
            >
              <span className="inline-flex min-w-0 items-center gap-1">
                <Download className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{file.path}</span>
              </span>
              <span className="shrink-0 text-bda-muted">{formatBytes(file.size_bytes)}</span>
            </button>
          ))}
        </div>
      ) : null}
    </article>
  )
}

export function ClusterDrafts({ projectId }: { projectId?: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['cluster-drafts', projectId],
    queryFn: () => listClusterDrafts(projectId),
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? []
      return items.some((item) => ['submitted', 'queued', 'running'].includes(item.status)) ? 5000 : false
    },
  })

  return (
    <section className="space-y-3 border-b border-bda-border bg-bda-bg p-4">
      <div>
        <div className="flex items-center gap-2 text-sm font-medium text-bda-text">
          <Terminal className="h-4 w-4 text-bda-cyan" />
          Cluster job drafts
        </div>
        <p className="mt-1 text-xs text-bda-muted">
          Copilot can create drafts, but only this confirmation button can submit a real LSF job.
        </p>
      </div>
      {isLoading ? <p className="text-xs text-bda-muted">Loading drafts…</p> : null}
      {data?.items.length ? (
        data.items.map((draft) => <DraftCard key={draft.draft_id} draft={draft} />)
      ) : (
        <p className="rounded border border-dashed border-bda-border p-3 text-xs text-bda-muted">
          No drafts yet. Ask Copilot to prepare an LSF job for review.
        </p>
      )}
      {data?.items.some((item) => item.status === 'completed') ? (
        <p className="inline-flex items-center gap-1 text-xs text-bda-green">
          <CheckCircle2 className="h-3.5 w-3.5" /> Completed outputs are available above.
        </p>
      ) : null}
    </section>
  )
}
