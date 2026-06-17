import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CircleStop, RotateCw, Terminal } from 'lucide-react'
import { cancelJob, getJobLogs, listWorkflowJobs } from '../../lib/api/jobs'
import type { Job } from '../../lib/schemas/job'
import { StatusPill } from '../../components/ui/StatusPill'
import { statusTone } from '../../components/ui/statusTone'
import { useToastStore } from '../../components/ui/toastStore'

interface JobStatusDrawerProps {
  workflowRunId?: string
  selectedNodeId?: string | null
}

export function JobStatusDrawer({ workflowRunId, selectedNodeId }: JobStatusDrawerProps) {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const showToast = useToastStore((s) => s.show)

  const { data: jobs = [] } = useQuery({
    queryKey: ['workflow-jobs', workflowRunId],
    queryFn: () => listWorkflowJobs(workflowRunId!),
    enabled: Boolean(workflowRunId),
    refetchInterval: (query) => {
      const data = query.state.data ?? []
      return data.some((job) => ['queued', 'running', 'staging', 'collecting_outputs'].includes(job.status)) ? 3000 : false
    },
  })

  const visibleJobs = useMemo(() => {
    if (!selectedNodeId) return jobs
    return jobs.filter((job) => job.node_run_id === selectedNodeId)
  }, [jobs, selectedNodeId])

  const selectedJob = visibleJobs.find((job) => job.job_id === selectedJobId) ?? visibleJobs[0]

  const { data: logPayload } = useQuery({
    queryKey: ['job-logs', selectedJob?.job_id],
    queryFn: () => getJobLogs(selectedJob!.job_id),
    enabled: Boolean(selectedJob?.job_id),
    refetchInterval: selectedJob && ['queued', 'running', 'staging'].includes(selectedJob.status) ? 3000 : false,
  })

  const cancel = useMutation({
    mutationFn: (job: Job) => cancelJob(job.job_id),
    onSuccess: () => {
      showToast('Job cancellation requested', 'info')
      queryClient.invalidateQueries({ queryKey: ['workflow-jobs', workflowRunId] })
    },
    onError: () => showToast('Failed to cancel job', 'error'),
  })

  return (
    <section className="rounded-md border border-bda-border bg-bda-bg p-3">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide text-bda-cyan">Jobs</p>
          <h3 className="text-sm font-semibold">{selectedNodeId ? 'Selected node runs' : 'Workflow runs'}</h3>
        </div>
        <button
          type="button"
          className="rounded border border-bda-border p-1 text-bda-muted hover:text-bda-text"
          onClick={() => queryClient.invalidateQueries({ queryKey: ['workflow-jobs', workflowRunId] })}
          title="Refresh jobs"
        >
          <RotateCw className="h-3.5 w-3.5" />
        </button>
      </div>

      {visibleJobs.length === 0 ? (
        <p className="rounded border border-dashed border-bda-border px-3 py-4 text-center text-xs text-bda-muted">
          No jobs yet. Run a node or submit the workflow to create one.
        </p>
      ) : (
        <div className="space-y-2">
          {visibleJobs.map((job) => (
            <button
              key={job.job_id}
              type="button"
              className={`w-full rounded-md border p-2 text-left ${
                selectedJob?.job_id === job.job_id ? 'border-bda-cyan bg-bda-cyan/10' : 'border-bda-border bg-bda-panel'
              }`}
              onClick={() => setSelectedJobId(job.job_id)}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-xs font-medium">{job.job_id}</span>
                <StatusPill label={job.status} tone={statusTone(job.status)} />
              </div>
              <p className="mt-1 truncate text-xs text-bda-muted">{job.plugin_id ?? 'unknown plugin'}</p>
            </button>
          ))}
        </div>
      )}

      {selectedJob ? (
        <div className="mt-3 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1 text-xs text-bda-muted">
              <Terminal className="h-3.5 w-3.5" />
              Log tail
            </span>
            {['queued', 'running', 'staging'].includes(selectedJob.status) ? (
              <button
                type="button"
                className="inline-flex items-center gap-1 rounded border border-bda-border px-2 py-1 text-xs text-bda-muted hover:text-bda-text disabled:opacity-40"
                disabled={cancel.isPending}
                onClick={() => cancel.mutate(selectedJob)}
              >
                <CircleStop className="h-3.5 w-3.5" />
                Cancel
              </button>
            ) : null}
          </div>
          <pre className="max-h-48 overflow-auto rounded-md border border-bda-border bg-black/30 p-2 text-xs leading-relaxed text-bda-muted">
            {logPayload?.logs || selectedJob.logs || selectedJob.error_message || 'No logs available yet.'}
          </pre>
        </div>
      ) : null}
    </section>
  )
}
