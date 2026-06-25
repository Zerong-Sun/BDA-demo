import { useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Download, Info, Network, Play, Save, Settings2, Terminal } from 'lucide-react'
import type { WorkflowNode } from '../../lib/schemas/workflow'
import type { Artifact } from '../../lib/schemas/artifact'
import { formatBytes } from '../../lib/schemas/artifact'
import { API_BASE } from '../../lib/api/client'
import { StatusPill } from '../../components/ui/StatusPill'
import { statusTone } from '../../components/ui/statusTone'
import { JobStatusDrawer } from '../jobs'
import {
  completeWorkflowNodeReview,
  previewWorkflowNodeSubmission,
  submitWorkflowNode,
  updateWorkflowNode,
  type NodeSubmissionPreview,
} from '../../lib/api/workflow'
import { useToastStore } from '../../components/ui/toastStore'
import { listModelPlugins } from '../../lib/api/registry'
import { ParameterSchemaForm } from '../plugins'
import {
  experimentResultTemplateUrl,
  getWorkflowExperimentPlan,
  getWorkflowParameterRecommendations,
  updateExperimentPlanStep,
  type ExperimentPlanStep,
} from '../../lib/api/copilot'

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

function previewHref(artifact: Artifact): string | undefined {
  const url = artifact.download_url ?? artifact.preview_url
  if (!url) return undefined
  if (url.startsWith('/api/')) return url
  return `${API_BASE}${url.startsWith('/') ? url : `/${url}`}`
}

export function WorkflowInspector({ workflowRunId, selectedNode, selectedArtifact }: WorkflowInspectorProps) {
  const parameters = parseJsonObject(selectedNode?.parameters_json)
  const metrics = parseJsonObject(selectedNode?.metrics_json)
  const href = selectedArtifact ? previewHref(selectedArtifact) : undefined
  const queryClient = useQueryClient()
  const showToast = useToastStore((state) => state.show)
  const [parameterText, setParameterText] = useState(JSON.stringify(parameters, null, 2))
  const [parameterError, setParameterError] = useState('')
  const [preview, setPreview] = useState<NodeSubmissionPreview | null>(null)
  const { data: modelPlugins = [] } = useQuery({
    queryKey: ['model-plugins'],
    queryFn: listModelPlugins,
    enabled: Boolean(selectedNode?.model_name),
  })
  const { data: experimentPlan } = useQuery({
    queryKey: ['experiment-plan', workflowRunId],
    queryFn: () => getWorkflowExperimentPlan(workflowRunId!),
    enabled: Boolean(workflowRunId && selectedNode?.node_type === 'experiment'),
    retry: false,
  })
  const { data: recommendationData } = useQuery({
    queryKey: ['parameter-recommendations', workflowRunId, selectedNode?.node_run_id],
    queryFn: () => getWorkflowParameterRecommendations(
      workflowRunId!,
      selectedNode!.node_run_id,
    ),
    enabled: Boolean(workflowRunId && selectedNode?.model_name),
  })
  const updateExperimentStep = useMutation({
    mutationFn: ({
      step,
      status,
      notes,
      resultArtifactId,
    }: {
      step: ExperimentPlanStep
      status: string
      notes: string
      resultArtifactId?: string
    }) => updateExperimentPlanStep(step.experiment_plan_step_id, {
      status,
      notes,
      result_artifact_id: resultArtifactId,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiment-plan', workflowRunId] })
      refreshWorkflow()
      showToast('Experiment step updated', 'success')
    },
    onError: (error) => showToast(error.message, 'error'),
  })
  const selectedPlugin = modelPlugins.find(
    (plugin) => plugin.model_name === selectedNode?.model_name,
  )

  const refreshWorkflow = () => {
    queryClient.invalidateQueries({ queryKey: ['workflow-graph', workflowRunId] })
    queryClient.invalidateQueries({ queryKey: ['workflow-jobs', workflowRunId] })
  }
  const saveParameters = useMutation({
    mutationFn: () => {
      if (!workflowRunId || !selectedNode) throw new Error('No node selected')
      let parsed: Record<string, unknown>
      try {
        parsed = JSON.parse(parameterText) as Record<string, unknown>
      } catch {
        throw new Error('Parameters must be valid JSON')
      }
      return updateWorkflowNode(workflowRunId, selectedNode.node_run_id, {
        parameters_json: parsed,
      })
    },
    onSuccess: () => {
      setPreview(null)
      setParameterError('')
      showToast('Node parameters saved', 'success')
      refreshWorkflow()
    },
    onError: (error) => setParameterError(error.message),
  })
  const previewSubmission = useMutation({
    mutationFn: async () => {
      if (!selectedNode) throw new Error('No node selected')
      if (parameterText !== JSON.stringify(parameters, null, 2)) {
        await saveParameters.mutateAsync()
      }
      return previewWorkflowNodeSubmission(selectedNode.node_run_id)
    },
    onSuccess: (result) => {
      setPreview(result)
      setParameterError('')
    },
    onError: (error) => setParameterError(error.message),
  })
  const submitNode = useMutation({
    mutationFn: () => {
      if (!selectedNode || !preview) throw new Error('Preview the node first')
      return submitWorkflowNode(selectedNode.node_run_id, preview.parameter_checksum)
    },
    onSuccess: () => {
      showToast('Node submitted to compute', 'success')
      refreshWorkflow()
    },
    onError: (error) => setParameterError(error.message),
  })
  const completeReview = useMutation({
    mutationFn: () => {
      if (!selectedNode) throw new Error('No node selected')
      return completeWorkflowNodeReview(selectedNode.node_run_id)
    },
    onSuccess: () => {
      showToast('Manual review gate completed', 'success')
      refreshWorkflow()
    },
    onError: (error) => setParameterError(error.message),
  })
  const attachArtifact = useMutation({
    mutationFn: () => {
      if (!workflowRunId || !selectedNode || !selectedArtifact) {
        throw new Error('Select both a node and an artifact')
      }
      const port = selectedNode.model_name === 'RFdiffusion'
        ? 'target_structure'
        : selectedArtifact.artifact_type
      const existingInputs = parseJsonObject(selectedNode.input_files_json)
      return updateWorkflowNode(workflowRunId, selectedNode.node_run_id, {
        input_files_json: {
          ...existingInputs,
          [port]: [{ artifact_id: selectedArtifact.artifact_id }],
        },
      })
    },
    onSuccess: () => {
      setPreview(null)
      showToast('Artifact attached to node', 'success')
      refreshWorkflow()
    },
    onError: (error) => setParameterError(error.message),
  })
  const completableManualTypes = new Set([
    'research_review',
    'structure_preparation',
    'review_gate',
    'selection',
  ])
  const isManualNode = Boolean(
    selectedNode
    && !selectedNode.model_name
    && completableManualTypes.has(selectedNode.node_type),
  )

  return (
    <aside className="space-y-4">
      <section className="rounded-lg border border-bda-border bg-bda-panel p-3">
        <div className="mb-3 flex items-center gap-2">
          <Info className="h-4 w-4 text-bda-cyan" />
          <div>
            <p className="text-xs uppercase tracking-wide text-bda-cyan">Inspector</p>
            <h2 className="text-sm font-semibold">
              {selectedNode ? 'Node details' : selectedArtifact ? 'Artifact details' : 'Workflow summary'}
            </h2>
          </div>
        </div>

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
              {selectedPlugin ? (
                <ParameterSchemaForm
                  schema={selectedPlugin.parameter_schema_json}
                  values={parseJsonObject(parameterText)}
                  onChange={(next) => {
                    setParameterText(JSON.stringify(next, null, 2))
                    setParameterError('')
                    setPreview(null)
                  }}
                />
              ) : null}
              <details className="mt-3 rounded-md border border-bda-border bg-bda-bg p-2">
                <summary className="cursor-pointer text-xs text-bda-muted">Expert JSON</summary>
                <textarea
                  aria-label="Node parameters"
                  className="mt-2 min-h-56 w-full rounded-md border border-bda-border bg-bda-bg p-2 font-mono text-xs"
                  value={parameterText}
                  onChange={(event) => {
                    setParameterText(event.target.value)
                    setParameterError('')
                    setPreview(null)
                  }}
                />
              </details>
              {parameterError ? <p className="mt-2 text-xs text-bda-red">{parameterError}</p> : null}
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="inline-flex items-center gap-1 rounded border border-bda-border px-2 py-1.5 text-xs disabled:opacity-40"
                  disabled={!workflowRunId || saveParameters.isPending}
                  onClick={() => saveParameters.mutate()}
                >
                  <Save className="h-3.5 w-3.5" />
                  Save
                </button>
                {isManualNode ? (
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded bg-bda-green px-2 py-1.5 text-xs text-bda-bg disabled:opacity-40"
                    disabled={selectedNode.status === 'completed' || completeReview.isPending}
                    onClick={() => completeReview.mutate()}
                  >
                    <Check className="h-3.5 w-3.5" />
                    Complete review
                  </button>
                ) : (
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded border border-bda-cyan px-2 py-1.5 text-xs text-bda-cyan disabled:opacity-40"
                    disabled={previewSubmission.isPending}
                    onClick={() => previewSubmission.mutate()}
                  >
                    <Terminal className="h-3.5 w-3.5" />
                    Preview run
                  </button>
                )}
                {selectedArtifact ? (
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded border border-bda-border px-2 py-1.5 text-xs disabled:opacity-40"
                    disabled={attachArtifact.isPending}
                    onClick={() => attachArtifact.mutate()}
                  >
                    <Download className="h-3.5 w-3.5" />
                    Attach {selectedArtifact.display_name}
                  </button>
                ) : null}
              </div>
            </InspectorBlock>
            {recommendationData?.items.length ? (
              <InspectorBlock icon={<Info className="h-3.5 w-3.5" />} title="Copilot recommendation provenance">
                <div className="space-y-2">
                  {recommendationData.items.map((item) => (
                    <div
                      key={item.parameter_recommendation_id}
                      className={`rounded border p-2 text-xs ${
                        item.differs_from_recommendation
                          ? 'border-bda-amber/50 bg-bda-amber/10'
                          : 'border-bda-border bg-bda-bg'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">{item.parameter_key}</span>
                        <span className="text-[10px] uppercase text-bda-muted">
                          {item.confidence ?? 'unrated'}
                        </span>
                      </div>
                      <p className="mt-1 text-bda-muted">
                        recommended {JSON.stringify(item.recommended_value_json)}
                        {' · '}current {JSON.stringify(item.current_value)}
                      </p>
                      {Object.keys(item.recommended_range_json ?? {}).length ? (
                        <p className="mt-1 text-bda-muted">
                          range {JSON.stringify(item.recommended_range_json)}
                        </p>
                      ) : null}
                      {item.rationale ? <p className="mt-1">{item.rationale}</p> : null}
                      {item.source_refs_json?.length ? (
                        <p className="mt-1 break-all text-[10px] text-bda-cyan">
                          sources: {item.source_refs_json.join(', ')}
                        </p>
                      ) : null}
                    </div>
                  ))}
                </div>
              </InspectorBlock>
            ) : null}

            {preview ? (
              <InspectorBlock icon={<Terminal className="h-3.5 w-3.5" />} title="Submission preview">
                {preview.blockers.length > 0 ? (
                  <div className="space-y-1 rounded border border-bda-amber/40 bg-bda-amber/10 p-2 text-xs text-bda-amber">
                    {preview.blockers.map((blocker, index) => (
                      <p key={`${blocker.code}-${index}`}>{blocker.message}</p>
                    ))}
                  </div>
                ) : null}
                {preview.validation.warnings.length > 0 ? (
                  <div className="mt-2 space-y-1 rounded border border-bda-border p-2 text-xs text-bda-muted">
                    {preview.validation.warnings.map((warning) => (
                      <p key={warning.parameter}>{warning.parameter}: {warning.message}</p>
                    ))}
                  </div>
                ) : null}
                <p className="mt-2 text-[10px] uppercase tracking-wide text-bda-muted">Trusted runner</p>
                <pre className="mt-2 max-h-52 overflow-auto rounded border border-bda-border bg-black/30 p-2 text-xs text-bda-muted">
                  {preview.command || 'No command available.'}
                </pre>
                {preview.model_command_preview ? (
                  <>
                    <p className="mt-2 text-[10px] uppercase tracking-wide text-bda-muted">Resolved model invocation</p>
                    <pre className="mt-2 max-h-52 overflow-auto rounded border border-bda-border bg-black/30 p-2 text-xs text-bda-muted">
                      {preview.model_command_preview}
                    </pre>
                  </>
                ) : null}
                <button
                  type="button"
                  className="mt-2 inline-flex items-center gap-1 rounded bg-bda-green px-3 py-2 text-xs text-bda-bg disabled:opacity-40"
                  disabled={!preview.ready || submitNode.isPending}
                  onClick={() => submitNode.mutate()}
                >
                  <Play className="h-3.5 w-3.5" />
                  Confirm and submit
                </button>
              </InspectorBlock>
            ) : null}

            <InspectorBlock icon={<Network className="h-3.5 w-3.5" />} title="Metrics">
              <KeyValueGrid data={metrics} empty="No metrics reported yet." />
            </InspectorBlock>

            {selectedNode.logs ? (
              <pre className="max-h-32 overflow-auto rounded-md border border-bda-border bg-bda-bg p-2 text-xs text-bda-muted">
                {selectedNode.logs}
              </pre>
            ) : null}
            {selectedNode.node_type === 'experiment' && experimentPlan ? (
              <InspectorBlock icon={<Network className="h-3.5 w-3.5" />} title="Experiment plan">
                <p className="mb-2 text-xs text-bda-muted">{experimentPlan.objective}</p>
                <div className="mb-3 flex gap-2">
                  <a
                    className="inline-flex items-center gap-1 rounded border border-bda-border px-2 py-1 text-xs"
                    href={experimentResultTemplateUrl(experimentPlan.experiment_plan_id)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Download className="h-3.5 w-3.5" />
                    CSV result template
                  </a>
                  <a
                    className="inline-flex items-center gap-1 rounded border border-bda-border px-2 py-1 text-xs"
                    href={experimentResultTemplateUrl(experimentPlan.experiment_plan_id, 'json')}
                    target="_blank"
                    rel="noreferrer"
                  >
                    JSON schema
                  </a>
                </div>
                <div className="space-y-2">
                  {experimentPlan.steps.map((step) => (
                    <ExperimentStepEditor
                      key={`${step.experiment_plan_step_id}:${step.updated_at}`}
                      step={step}
                      selectedArtifact={selectedArtifact}
                      saving={updateExperimentStep.isPending}
                      onSave={(status, notes, resultArtifactId) =>
                        updateExperimentStep.mutate({ step, status, notes, resultArtifactId })}
                    />
                  ))}
                </div>
                <div className="mt-3 rounded border border-bda-amber/40 bg-bda-amber/10 p-2 text-xs text-bda-amber">
                  Human sensory and safety studies require independent ethics, safety, and regulatory approval.
                </div>
              </InspectorBlock>
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
            <KeyValueGrid data={selectedArtifact.metadata} empty="No metadata parsed yet." />
            {href ? (
              <a
                href={href}
                className="inline-flex items-center gap-2 rounded-md border border-bda-border px-3 py-2 text-sm text-bda-text hover:border-bda-cyan/50"
              >
                <Download className="h-4 w-4" />
                Open artifact
              </a>
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
      </section>

      <JobStatusDrawer workflowRunId={workflowRunId} selectedNodeId={selectedNode?.node_run_id ?? null} />
    </aside>
  )
}

function ExperimentStepEditor({
  step,
  selectedArtifact,
  saving,
  onSave,
}: {
  step: ExperimentPlanStep
  selectedArtifact?: Artifact | null
  saving: boolean
  onSave: (status: string, notes: string, resultArtifactId?: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState(step.status)
  const [notes, setNotes] = useState(step.notes ?? '')
  return (
    <div className="rounded border border-bda-border bg-bda-bg p-2">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-2 text-left"
        onClick={() => setOpen((value) => !value)}
      >
        <span className="text-xs font-medium">{step.stage_order}. {step.title}</span>
        <span className="text-[10px] uppercase text-bda-cyan">{status}</span>
      </button>
      {open ? (
        <div className="mt-2 space-y-2 text-xs">
          <p className="text-bda-muted">{step.purpose}</p>
          <p><span className="text-bda-muted">Readouts:</span> {step.readouts_json.join(', ')}</p>
          <p><span className="text-bda-muted">Criteria:</span> {step.acceptance_criteria_json.join(', ')}</p>
          <select
            className="w-full rounded border border-bda-border bg-bda-panel px-2 py-1"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="planned">Planned</option>
            <option value="ready">Ready</option>
            <option value="in_progress">In progress</option>
            <option value="completed">Completed</option>
            <option value="blocked">Blocked</option>
          </select>
          <textarea
            className="min-h-20 w-full rounded border border-bda-border bg-bda-panel p-2"
            placeholder="Owner, SOP reference, result summary, or blocker"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
          <button
            type="button"
            className="rounded border border-bda-border px-2 py-1 disabled:opacity-40"
            disabled={saving}
            onClick={() => onSave(status, notes, selectedArtifact?.artifact_id)}
          >
            Save step{selectedArtifact ? ` + attach ${selectedArtifact.display_name}` : ''}
          </button>
        </div>
      ) : null}
    </div>
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
