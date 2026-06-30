import { useMemo, useState, type ReactNode } from 'react'
import { Copy, Download, FileCode2, Info, Network, Save, Settings2, UploadCloud } from 'lucide-react'
import type { WorkflowNode } from '../../lib/schemas/workflow'
import type { Artifact } from '../../lib/schemas/artifact'
import { formatBytes } from '../../lib/schemas/artifact'
import { downloadArtifact } from '../../lib/api/artifacts'
import { StatusPill } from '../../components/ui/StatusPill'
import { statusTone } from '../../components/ui/statusTone'
import { JobStatusDrawer } from '../jobs'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useToastStore } from '../../components/ui/toastStore'
import { listModelPlugins } from '../../lib/api/registry'
import { previewWorkflowNodeScript, submitWorkflowNode, updateWorkflowNode, validateWorkflowRun, type ScriptPreviewResponse } from '../../lib/api/workflow'
import { ParameterSchemaForm } from '../plugins'
import { defaultsFromFields, fieldsFromParameterSchema } from '../../lib/forms/parameterSchema'

interface WorkflowInspectorProps {
  workflowRunId?: string
  selectedNode?: WorkflowNode | null
  selectedArtifact?: Artifact | null
}

function parseJsonObject(value: unknown): Record<string, unknown> {
  if (!value) return {}
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : {}
    } catch {
      return {}
    }
  }
  return typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function isBlockingNodeIssue(issue: Record<string, unknown>, nodeRunId: string) {
  if (issue.code === 'missing_required_input' && issue.node_run_id === nodeRunId) return true
  if (issue.node_run_id === nodeRunId) return true
  return issue.code === 'cycle_detected'
}

export function WorkflowInspector(props: WorkflowInspectorProps) {
  const selectionKey = props.selectedNode?.node_run_id ?? props.selectedArtifact?.artifact_id ?? 'empty'
  return <WorkflowInspectorContent key={selectionKey} {...props} />
}

function WorkflowInspectorContent({ workflowRunId, selectedNode, selectedArtifact }: WorkflowInspectorProps) {
  const parameters = parseJsonObject(selectedNode?.parameters_json)
  const metrics = parseJsonObject(selectedNode?.metrics_json)
  const [draftParameters, setDraftParameters] = useState<Record<string, unknown>>(parameters)
  const [scriptPreview, setScriptPreview] = useState<ScriptPreviewResponse | null>(null)
  const [queueName, setQueueName] = useState('')
  const [resourceRequirement, setResourceRequirement] = useState('span[ptile=1]')
  const [gpuRequirement, setGpuRequirement] = useState('num=1')
  const showToast = useToastStore((s) => s.show)
  const queryClient = useQueryClient()
  const hasDownload = Boolean(selectedArtifact?.download_url ?? selectedArtifact?.preview_url)

  const { data: modelPlugins = [] } = useQuery({
    queryKey: ['model-plugins'],
    queryFn: listModelPlugins,
  })

  const activePlugin = useMemo(
    () => modelPlugins.find((plugin) => plugin.model_name === selectedNode?.model_name),
    [modelPlugins, selectedNode?.model_name],
  )
  const parameterFields = useMemo(
    () => fieldsFromParameterSchema(activePlugin?.parameter_schema_json, selectedNode?.model_name ?? undefined),
    [activePlugin?.parameter_schema_json, selectedNode?.model_name],
  )
  const parameterSchema = useMemo(() => ({ fields: parameterFields }), [parameterFields])
  const effectiveParameters = useMemo(
    () => ({ ...defaultsFromFields(parameterFields), ...draftParameters }),
    [draftParameters, parameterFields],
  )

  const saveParameters = useMutation({
    mutationFn: () => {
      if (!workflowRunId || !selectedNode) throw new Error('Select a workflow node first.')
      return updateWorkflowNode(workflowRunId, selectedNode.node_run_id, { parameters_json: effectiveParameters })
    },
    onSuccess: async () => {
      showToast('Node parameters saved', 'success')
      await queryClient.invalidateQueries({ queryKey: ['workflow-graph', workflowRunId] })
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to save parameters', 'error'),
  })

  const previewScript = useMutation({
    mutationFn: () => {
      if (!selectedNode) throw new Error('Select a workflow node first.')
      return previewWorkflowNodeScript(selectedNode.node_run_id, {
        override_params: effectiveParameters,
        queue_name: queueName.trim() || undefined,
        resource_requirement: resourceRequirement.trim() || undefined,
        gpu_requirement: gpuRequirement.trim() || undefined,
      })
    },
    onSuccess: (preview) => {
      setScriptPreview(preview)
      showToast('Script preview generated', 'success')
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Script preview failed', 'error'),
  })

  const submitReviewedScript = useMutation({
    mutationFn: async () => {
      if (!selectedNode) throw new Error('Select a workflow node first.')
      if (!scriptPreview) throw new Error('Generate a script preview first.')
      if (workflowRunId) {
        const validation = await validateWorkflowRun(workflowRunId)
        const hasBlockingInputWarning = validation.warnings.some((issue) => isBlockingNodeIssue(issue, selectedNode.node_run_id))
        if (validation.errors.length > 0 || hasBlockingInputWarning) {
          throw new Error('Resolve required node inputs before submission.')
        }
      }
      return submitWorkflowNode(selectedNode.node_run_id, {
        override_params: effectiveParameters,
        queue_name: queueName.trim() || undefined,
        resource_requirement: resourceRequirement.trim() || undefined,
        gpu_requirement: gpuRequirement.trim() || undefined,
      })
    },
    onSuccess: async (job) => {
      showToast(`Job ${job.job_id} ${job.status}`, 'success')
      await queryClient.invalidateQueries({ queryKey: ['workflow-graph', workflowRunId] })
      await queryClient.invalidateQueries({ queryKey: ['workflow-jobs', workflowRunId] })
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Submission failed', 'error'),
  })

  const downloadSelectedArtifact = async () => {
    if (!selectedArtifact) return
    try {
      await downloadArtifact(selectedArtifact)
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Artifact download failed', 'error')
    }
  }

  const downloadScriptPreview = () => {
    if (!scriptPreview || !selectedNode) return
    const blob = new Blob([scriptPreview.script], { type: 'text/x-shellscript' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${selectedNode.node_name.replace(/[^A-Za-z0-9_.-]+/g, '_') || 'workflow_node'}.lsf`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const copyScriptPreview = async () => {
    if (!scriptPreview) return
    await navigator.clipboard.writeText(scriptPreview.script)
    showToast('Script copied', 'success')
  }

  return (
    <aside className="bda-sticky-panel space-y-4 xl:max-h-[calc(100vh-8rem)] xl:overflow-hidden">
      <section className="bda-card flex min-h-0 flex-col xl:max-h-[calc(100vh-17rem)]">
        <div className="bda-card-header py-3">
          <div className="flex items-center gap-2">
            <Info className="h-4 w-4 text-bda-cyan" />
            <div>
              <p className="text-xs uppercase tracking-wide text-bda-cyan">Inspector</p>
              <h2 className="text-sm font-semibold">
                {selectedNode ? 'Node details' : selectedArtifact ? 'Artifact details' : 'Workflow summary'}
              </h2>
            </div>
          </div>
        </div>

        <div className="bda-card-body bda-scroll-area min-h-0">
          {selectedNode ? (
          <div className="space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate text-sm font-semibold">{selectedNode.node_name}</h3>
                <p className="mt-1 text-xs text-bda-muted">
                  {selectedNode.model_name ?? selectedNode.node_type}
                  {selectedNode.model_version ? ` · v${selectedNode.model_version}` : ''}
                </p>
              </div>
              <StatusPill label={selectedNode.status} tone={statusTone(selectedNode.status)} />
            </div>

            <InspectorBlock icon={<Settings2 className="h-3.5 w-3.5" />} title="Parameters">
              <div className="bda-scroll-area max-h-80 rounded-md border border-bda-border bg-bda-bg p-2">
                <ParameterSchemaForm schema={parameterSchema} values={effectiveParameters} onChange={setDraftParameters} />
              </div>
              <div className="mt-3 grid gap-2 rounded-md border border-bda-border bg-bda-bg p-2">
                <label className="grid gap-1 text-[11px] text-bda-muted">
                  LSF queue override
                  <input
                    className="rounded border border-bda-border bg-bda-panel px-2 py-1.5 text-xs text-bda-text"
                    value={queueName}
                    onChange={(event) => setQueueName(event.target.value)}
                    placeholder="leave blank for RFdiffusion default"
                  />
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <label className="grid gap-1 text-[11px] text-bda-muted">
                    Resource
                    <input
                      className="rounded border border-bda-border bg-bda-panel px-2 py-1.5 text-xs text-bda-text"
                      value={resourceRequirement}
                      onChange={(event) => setResourceRequirement(event.target.value)}
                    />
                  </label>
                  <label className="grid gap-1 text-[11px] text-bda-muted">
                    GPU
                    <input
                      className="rounded border border-bda-border bg-bda-panel px-2 py-1.5 text-xs text-bda-text"
                      value={gpuRequirement}
                      onChange={(event) => setGpuRequirement(event.target.value)}
                    />
                  </label>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="inline-flex items-center gap-1.5 rounded-md border border-bda-border px-2.5 py-1.5 text-xs text-bda-text hover:border-bda-cyan/50 disabled:opacity-50"
                  disabled={saveParameters.isPending}
                  onClick={() => saveParameters.mutate()}
                >
                  <Save className="h-3.5 w-3.5" />
                  {saveParameters.isPending ? 'Saving...' : 'Save parameters'}
                </button>
                <button
                  type="button"
                  className="inline-flex items-center gap-1.5 rounded-md bg-bda-cyan px-2.5 py-1.5 text-xs font-medium text-bda-bg disabled:opacity-50"
                  disabled={previewScript.isPending}
                  onClick={() => previewScript.mutate()}
                >
                  <FileCode2 className="h-3.5 w-3.5" />
                  {previewScript.isPending ? 'Generating...' : 'Generate script'}
                </button>
              </div>
              {scriptPreview ? (
                <div className="mt-3 rounded-md border border-bda-border bg-bda-bg">
                  <div className="flex items-center justify-between gap-2 border-b border-bda-border px-2 py-1.5">
                    <span className="truncate text-xs text-bda-muted">
                      {scriptPreview.plugin_id} · {scriptPreview.job_id}
                    </span>
                    <span className="flex gap-1">
                      <button
                        type="button"
                        className="rounded border border-bda-border p-1 text-bda-muted hover:text-bda-text"
                        onClick={() => void copyScriptPreview()}
                        title="Copy script"
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        className="rounded border border-bda-border p-1 text-bda-muted hover:text-bda-text"
                        onClick={downloadScriptPreview}
                        title="Download script"
                      >
                        <Download className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        className="rounded border border-bda-border p-1 text-bda-muted hover:text-bda-text disabled:opacity-50"
                        onClick={() => submitReviewedScript.mutate()}
                        disabled={submitReviewedScript.isPending}
                        title="Upload and submit"
                      >
                        <UploadCloud className="h-3.5 w-3.5" />
                      </button>
                    </span>
                  </div>
                  <pre className="bda-scroll-area max-h-72 p-2 text-[11px] leading-relaxed text-bda-muted">
                    {scriptPreview.script}
                  </pre>
                </div>
              ) : null}
            </InspectorBlock>

            <InspectorBlock icon={<Network className="h-3.5 w-3.5" />} title="Metrics">
              <div className="bda-scroll-area max-h-56">
                <KeyValueGrid data={metrics} empty="No metrics reported yet." />
              </div>
            </InspectorBlock>

            {selectedNode.logs ? (
              <pre className="bda-scroll-area max-h-32 rounded-md border border-bda-border bg-bda-bg p-2 text-xs text-bda-muted">
                {selectedNode.logs}
              </pre>
            ) : null}
          </div>
        ) : selectedArtifact ? (
          <div className="space-y-3">
            <div>
              <h3 className="break-words text-sm font-semibold">{selectedArtifact.display_name}</h3>
              <p className="mt-1 text-xs text-bda-muted">
                {selectedArtifact.artifact_type} · {selectedArtifact.format} · {formatBytes(selectedArtifact.size_bytes)}
              </p>
            </div>
            <InspectorBlock icon={<Network className="h-3.5 w-3.5" />} title="Lineage">
              <KeyValueGrid
                data={{
                  project_id: selectedArtifact.project_id,
                  workflow_run_id: selectedArtifact.workflow_run_id,
                  node_run_id: selectedArtifact.node_run_id,
                  checksum: selectedArtifact.checksum,
                  storage_uri: selectedArtifact.storage_uri,
                  created_by: selectedArtifact.created_by,
                }}
                empty="No lineage fields are attached yet."
              />
            </InspectorBlock>
            <div className="bda-scroll-area max-h-72">
              <KeyValueGrid data={selectedArtifact.metadata} empty="No metadata parsed yet." />
            </div>
            {hasDownload ? (
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-md border border-bda-border px-3 py-2 text-sm text-bda-text hover:border-bda-cyan/50"
                onClick={() => void downloadSelectedArtifact()}
              >
                <Download className="h-4 w-4" />
                Download artifact
              </button>
            ) : (
              <p className="rounded border border-dashed border-bda-border p-3 text-xs text-bda-muted">
                No download URL is available for this artifact yet.
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-2 text-xs leading-relaxed text-bda-muted">
            <p>Select a node to edit parameters, inspect logs, and review outputs.</p>
            <p>Select an artifact to preview metadata or download the source file.</p>
          </div>
        )}
        </div>
      </section>

      <JobStatusDrawer workflowRunId={workflowRunId} selectedNodeId={selectedNode?.node_run_id ?? null} overrideParams={effectiveParameters} />
    </aside>
  )
}

function InspectorBlock({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <div>
      <h4 className="mb-2 flex items-center gap-1.5 text-xs font-medium text-bda-muted">
        {icon}
        {title}
      </h4>
      {children}
    </div>
  )
}

function KeyValueGrid({ data, empty }: { data: Record<string, unknown>; empty: string }) {
  const entries = Object.entries(data).filter(([, value]) => value !== undefined && value !== null && value !== '')
  if (entries.length === 0) {
    return <p className="rounded border border-dashed border-bda-border p-3 text-xs text-bda-muted">{empty}</p>
  }
  return (
    <dl className="grid gap-2">
      {entries.map(([key, value]) => (
        <div key={key} className="rounded-md border border-bda-border bg-bda-bg p-2">
          <dt className="text-[10px] uppercase tracking-wide text-bda-muted">{key}</dt>
          <dd className="mt-1 break-words text-xs text-bda-text">
            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
          </dd>
        </div>
      ))}
    </dl>
  )
}
