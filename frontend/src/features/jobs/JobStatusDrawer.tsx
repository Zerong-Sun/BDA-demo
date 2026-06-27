import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CircleStop, Download, RotateCw, Terminal } from 'lucide-react'
import { cancelJob, getJobLogs, listWorkflowJobs, syncJobResult } from '../../lib/api/jobs'
import { submitWorkflowNode } from '../../lib/api/workflow'
import type { Job } from '../../lib/schemas/job'
import { StatusPill } from '../../components/ui/StatusPill'
import { statusTone } from '../../components/ui/statusTone'
import { useToastStore } from '../../components/ui/toastStore'
import { Link } from 'react-router-dom'
import { useProjectContext } from '../../lib/hooks/useProjectContext'

interface JobStatusDrawerProps {
  workflowRunId?: string
  selectedNodeId?: string | null
  overrideParams?: Record<string, unknown>
}

export function JobStatusDrawer({ workflowRunId, selectedNodeId, overrideParams }: JobStatusDrawerProps) {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [manualOpen, setManualOpen] = useState(false)
  const [queueName, setQueueName] = useState('gpu-bme-liz')
  const [cpuCount, setCpuCount] = useState(8)
  const [resourceRequirement, setResourceRequirement] = useState('span[ptile=1]')
  const [gpuRequirement, setGpuRequirement] = useState('num=1')
  const queryClient = useQueryClient()
  const showToast = useToastStore((s) => s.show)
  const { projectId } = useProjectContext()

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

  const submitManual = useMutation({
    mutationFn: () => {
      if (!selectedNodeId) throw new Error('Select a workflow node first.')
      return submitWorkflowNode(selectedNodeId, {
        override_params: overrideParams,
        queue_name: queueName.trim() || undefined,
        cpu_count: cpuCount,
        resource_requirement: resourceRequirement.trim() || undefined,
        gpu_requirement: gpuRequirement.trim() || undefined,
      })
    },
    onSuccess: async (result) => {
      showToast(`Submitted job ${result.job_id}`, 'success')
      await queryClient.invalidateQueries({ queryKey: ['workflow-jobs', workflowRunId] })
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Manual submit failed', 'error'),
  })

  const syncResult = useMutation({
    mutationFn: (job: Job) => syncJobResult(job.job_id),
    onSuccess: async (result) => {
      const artifacts = Array.isArray(result.outputs?.artifacts) ? result.outputs.artifacts.length : 0
      const message =
        result.outputs?.manifest_found === true
          ? `Synced ${artifacts} output artifact${artifacts === 1 ? '' : 's'}`
          : `Job is ${result.live_status}; no output manifest yet`
      showToast(message, result.outputs?.manifest_found === true ? 'success' : 'info')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['workflow-jobs', workflowRunId] }),
        queryClient.invalidateQueries({ queryKey: ['job-logs', result.job.job_id] }),
        queryClient.invalidateQueries({ queryKey: ['workflow-graph', workflowRunId] }),
        queryClient.invalidateQueries({ queryKey: ['project-artifacts'] }),
        queryClient.invalidateQueries({ queryKey: ['candidates'] }),
      ])
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to sync cluster result', 'error'),
  })

  const outputSummary = useMemo(() => {
    if (!selectedJob?.output_artifacts || typeof selectedJob.output_artifacts !== 'object') return null
    const payload = selectedJob.output_artifacts as Record<string, unknown>
    const artifacts = Array.isArray(payload.artifacts) ? payload.artifacts : []
    const metrics = payload.metrics && typeof payload.metrics === 'object' ? (payload.metrics as Record<string, unknown>) : {}
    return {
      manifestFound: payload.manifest_found === true,
      artifactCount: artifacts.length,
      backboneCount: Number(metrics.backbone_count ?? artifacts.length) || artifacts.length,
    }
  }, [selectedJob])

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

      <div className="mb-3 rounded-md border border-bda-border bg-bda-panel p-2">
        {!selectedNodeId ? (
          <p className="text-xs leading-relaxed text-bda-muted">
            Manual LSF submit: 先在流程图里点选一个节点，再在这里手动填写队列或资源请求。
          </p>
        ) : (
          <>
          <button
            type="button"
            className="flex w-full items-center justify-between text-left text-xs font-medium text-bda-text"
            onClick={() => setManualOpen((value) => !value)}
          >
            <span>Manual LSF submit</span>
            <span className="text-bda-muted">{manualOpen ? 'Hide' : 'Edit queue'}</span>
          </button>
          {manualOpen ? (
            <div className="mt-3 grid gap-2">
              <label className="grid gap-1 text-[11px] text-bda-muted">
                Queue
                <input
                  className="rounded border border-bda-border bg-bda-bg px-2 py-1.5 text-xs text-bda-text"
                  value={queueName}
                  onChange={(event) => setQueueName(event.target.value)}
                  placeholder="gpu-bme-liz"
                />
              </label>
              <div className="grid grid-cols-2 gap-2">
                <label className="grid gap-1 text-[11px] text-bda-muted">
                  CPU tasks
                  <input
                    className="rounded border border-bda-border bg-bda-bg px-2 py-1.5 text-xs text-bda-text"
                    type="number"
                    min={1}
                    max={256}
                    value={cpuCount}
                    onChange={(event) => setCpuCount(Number(event.target.value) || 1)}
                  />
                </label>
                <label className="grid gap-1 text-[11px] text-bda-muted">
                  GPU
                  <input
                    className="rounded border border-bda-border bg-bda-bg px-2 py-1.5 text-xs text-bda-text"
                    value={gpuRequirement}
                    onChange={(event) => setGpuRequirement(event.target.value)}
                    placeholder="num=1"
                  />
                </label>
              </div>
              <label className="grid gap-1 text-[11px] text-bda-muted">
                Resource requirement
                <input
                  className="rounded border border-bda-border bg-bda-bg px-2 py-1.5 text-xs text-bda-text"
                  value={resourceRequirement}
                  onChange={(event) => setResourceRequirement(event.target.value)}
                  placeholder="span[ptile=1]"
                />
              </label>
              <p className="text-[11px] leading-relaxed text-bda-muted">
                用这个入口可以换队列或资源请求；会为当前选中节点创建新的 LSF job。
              </p>
              <button
                type="button"
                className="rounded bg-bda-cyan px-3 py-2 text-xs font-medium text-bda-bg disabled:opacity-50"
                disabled={submitManual.isPending || !queueName.trim()}
                onClick={() => submitManual.mutate()}
              >
                {submitManual.isPending ? 'Submitting…' : 'Submit selected node'}
              </button>
            </div>
          ) : null}
          </>
        )}
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
              <p className="mt-1 truncate text-xs text-bda-muted">
                {job.plugin_id ?? 'unknown plugin'}
                {job.external_id ? ` · LSF ${job.external_id}` : ''}
              </p>
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
            {selectedJob.external_id ? (
              <button
                type="button"
                className="inline-flex items-center gap-1 rounded border border-bda-border px-2 py-1 text-xs text-bda-muted hover:text-bda-text disabled:opacity-40"
                disabled={syncResult.isPending}
                onClick={() => syncResult.mutate(selectedJob)}
                title="Check LSF status and collect generated outputs"
              >
                <Download className="h-3.5 w-3.5" />
                {syncResult.isPending ? 'Syncing…' : 'Sync result'}
              </button>
            ) : null}
          </div>
          {outputSummary ? (
            <div className="rounded-md border border-bda-border bg-bda-panel p-2 text-xs text-bda-muted">
              <div className="flex items-center justify-between gap-2">
                <span>
                  {outputSummary.manifestFound
                    ? `${outputSummary.backboneCount} generated backbone${outputSummary.backboneCount === 1 ? '' : 's'} registered`
                    : 'No output manifest registered yet'}
                </span>
                <span>{outputSummary.artifactCount} artifact{outputSummary.artifactCount === 1 ? '' : 's'}</span>
              </div>
              {outputSummary.manifestFound ? (
                <div className="mt-2 flex flex-wrap gap-2">
                  <Link
                    className="rounded border border-bda-border px-2 py-1 hover:text-bda-text"
                    to={`/candidates?project=${encodeURIComponent(projectId)}`}
                  >
                    Review candidates
                  </Link>
                  <Link
                    className="rounded border border-bda-border px-2 py-1 hover:text-bda-text"
                    to={`/workflow?project=${encodeURIComponent(projectId)}`}
                  >
                    Continue workflow
                  </Link>
                </div>
              ) : null}
            </div>
          ) : null}
          <pre className="max-h-48 overflow-auto rounded-md border border-bda-border bg-black/30 p-2 text-xs leading-relaxed text-bda-muted">
            {logPayload?.logs ||
              selectedJob.logs ||
              selectedJob.error_message ||
              (selectedJob.external_id
                ? `No log output yet. The cluster job ${selectedJob.external_id} is ${selectedJob.status}; queued jobs often have an empty tail until they start running.`
                : 'No logs available yet. This job has not received an external scheduler id.')}
          </pre>
        </div>
      ) : null}
    </section>
  )
}
