import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, ChevronUp, Play, Plus } from 'lucide-react'
import { WorkflowCanvas, type WorkflowCanvasHandle } from '../features/workflow/WorkflowCanvas'
import { NodeBuilder } from '../features/workflow/NodeBuilder'
import { mapApiNodesToGraph } from '../features/workflow/workflowMapper'
import { MolStarViewerLazy } from '../features/pdb-viewer/MolStarViewerLazy'
import { PDBFileUpload } from '../features/pdb-viewer/PDBFileUpload'
import { ComputeStatusStrip } from '../features/workflow/ComputeStatusStrip'
import { PluginRegistryPanel } from '../features/workflow/PluginRegistryPanel'
import { ApiState } from '../components/ui/ApiState'
import { getLatestWorkflowRunOrNull } from '../lib/api/projects'
import { createWorkflowRun, listWorkflowNodes, submitWorkflowRun } from '../lib/api/workflow'
import { useAppStore } from '../lib/store/appStore'
import { useProjectContext } from '../lib/hooks/useProjectContext'
import { useToastStore } from '../components/ui/Toast'
import { useI18n } from '../lib/i18n'

export function WorkflowPage() {
  const [builderOpen, setBuilderOpen] = useState(true)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const canvasRef = useRef<WorkflowCanvasHandle>(null)
  const targetIntakeOpen = useAppStore((s) => s.targetIntakeOpen)
  const setTargetIntakeOpen = useAppStore((s) => s.setTargetIntakeOpen)
  const { projectId } = useProjectContext()
  const { t } = useI18n()
  const showToast = useToastStore((s) => s.show)
  const queryClient = useQueryClient()

  const {
    data: workflowRun,
    isError: workflowError,
    error: workflowQueryError,
    refetch: refetchWorkflow,
  } = useQuery({
    queryKey: ['workflow-run', projectId],
    queryFn: () => getLatestWorkflowRunOrNull(projectId),
  })

  const { data: workflowNodes = [] } = useQuery({
    queryKey: ['workflow-nodes', workflowRun?.workflow_run_id],
    queryFn: () => listWorkflowNodes(workflowRun!.workflow_run_id),
    enabled: Boolean(workflowRun?.workflow_run_id),
    refetchInterval: (query) => {
      const nodes = query.state.data ?? []
      return nodes.some((node) => node.status === 'running') ? 3000 : false
    },
  })

  const graph = useMemo(
    () => (workflowNodes.length > 0 ? mapApiNodesToGraph(workflowNodes) : null),
    [workflowNodes],
  )

  const readOnly = workflowRun?.status === 'completed'

  const createWorkflow = useMutation({
    mutationFn: () => createWorkflowRun(projectId),
    onSuccess: (run) => {
      queryClient.setQueryData(['workflow-run', projectId], run)
      showToast('Workflow run created', 'success')
    },
    onError: () => showToast('Failed to create workflow run', 'error'),
  })

  const startWorkflow = useMutation({
    mutationFn: () => submitWorkflowRun(workflowRun!.workflow_run_id),
    onSuccess: (response) => {
      if (response.status === 'blocked') {
        showToast(response.message ?? 'Compute not connected', 'info')
      } else {
        showToast('Workflow submitted to compute', 'success')
      }
      queryClient.invalidateQueries({ queryKey: ['workflow-nodes', workflowRun?.workflow_run_id] })
    },
    onError: () => showToast('Failed to start workflow', 'error'),
  })

  return (
    <section>
      <ComputeStatusStrip />
      <PluginRegistryPanel />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {!workflowRun ? (
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
            disabled={createWorkflow.isPending}
            onClick={() => createWorkflow.mutate()}
          >
            <Plus className="h-4 w-4" />
            Create workflow run
          </button>
        ) : (
          <>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
              disabled={readOnly}
              onClick={() => setBuilderOpen((v) => !v)}
            >
              <Plus className="h-4 w-4" />
              {t.workflow.addNode}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md bg-bda-green px-3 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
              disabled={startWorkflow.isPending}
              onClick={() => startWorkflow.mutate()}
            >
              <Play className="h-4 w-4" />
              {t.workflow.startWorkflow}
            </button>
          </>
        )}
        {workflowRun ? (
          <span className="text-xs text-bda-muted">
            Run {workflowRun.workflow_run_id} · {workflowRun.status}
          </span>
        ) : (
          <span className="text-xs text-bda-muted">No workflow run for this project yet</span>
        )}
      </div>

      <ApiState
        isError={workflowError}
        error={workflowQueryError}
        onRetry={() => void refetchWorkflow()}
      >
        {!workflowRun ? (
          <div className="mb-4 rounded-lg border border-dashed border-bda-border bg-bda-panel p-6 text-center text-sm text-bda-muted">
            <p>Create a workflow run to add nodes, upload target structures, and submit to compute.</p>
          </div>
        ) : (
          <NodeBuilder
            open={builderOpen && !readOnly}
            onClose={() => setBuilderOpen(false)}
            onAdd={async (template, methods) => {
              try {
                await canvasRef.current?.addNodeFromTemplate(template, methods)
                showToast(`Added ${template.title} to workflow`, 'success')
                queryClient.invalidateQueries({ queryKey: ['workflow-nodes', workflowRun?.workflow_run_id] })
              } catch {
                showToast('Failed to add workflow node', 'error')
              }
            }}
          />
        )}

        <div className="mb-4 rounded-lg border border-bda-border bg-bda-panel">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3 text-left"
            onClick={() => setTargetIntakeOpen(!targetIntakeOpen)}
          >
            <span className="text-sm font-medium">{t.workflow.targetIntake}</span>
            {targetIntakeOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
          {targetIntakeOpen ? (
            <div className="grid gap-4 border-t border-bda-border p-4 xl:grid-cols-[1.4fr_1fr]">
              <PDBFileUpload projectId={projectId} onFileSelected={setUploadedFile} />
              <MolStarViewerLazy file={uploadedFile} height={220} />
            </div>
          ) : null}
        </div>

        <WorkflowCanvas
          ref={canvasRef}
          initialNodes={graph?.nodes}
          initialEdges={graph?.edges}
          workflowRunId={workflowRun?.workflow_run_id}
          readOnly={readOnly}
          onNodeAdded={() =>
            queryClient.invalidateQueries({ queryKey: ['workflow-nodes', workflowRun?.workflow_run_id] })
          }
        />
      </ApiState>
    </section>
  )
}
