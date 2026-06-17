import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Play, Plus } from 'lucide-react'
import { WorkflowCanvas, type WorkflowCanvasHandle } from '../features/workflow/WorkflowCanvas'
import { NodeBuilder } from '../features/workflow/NodeBuilder'
import { mapApiNodesToGraph } from '../features/workflow/workflowMapper'
import { ComputeStatusStrip } from '../features/workflow/ComputeStatusStrip'
import { WorkflowResourceSidebar } from '../features/workflow/WorkflowResourceSidebar'
import { WorkflowInspector } from '../features/workflow/WorkflowInspector'
import { ApiState } from '../components/ui/ApiState'
import { getLatestWorkflowRunOrNull } from '../lib/api/projects'
import { createWorkflowRun, listWorkflowNodes, submitWorkflowRun } from '../lib/api/workflow'
import { useProjectContext } from '../lib/hooks/useProjectContext'
import { useToastStore } from '../components/ui/toastStore'
import { useI18n } from '../lib/i18n'
import type { Artifact } from '../lib/schemas/artifact'

export function WorkflowPage() {
  const [builderOpen, setBuilderOpen] = useState(true)
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | undefined>()
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const canvasRef = useRef<WorkflowCanvasHandle>(null)
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

  const workflowRunId = workflowRun?.workflow_run_id

  const { data: workflowNodes = [] } = useQuery({
    queryKey: ['workflow-nodes', workflowRunId],
    queryFn: () => listWorkflowNodes(workflowRunId!),
    enabled: Boolean(workflowRunId),
    refetchInterval: (query) => {
      const nodes = query.state.data ?? []
      return nodes.some((node) => node.status === 'running') ? 3000 : false
    },
  })

  const graph = useMemo(
    () => (workflowNodes.length > 0 ? mapApiNodesToGraph(workflowNodes) : null),
    [workflowNodes],
  )
  const selectedNode = workflowNodes.find((node) => node.node_run_id === selectedNodeId) ?? null
  const selectedArtifact = artifacts.find((artifact) => artifact.artifact_id === selectedArtifactId) ?? null

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
    mutationFn: () => {
      if (!workflowRunId) {
        throw new Error('No workflow run available')
      }
      return submitWorkflowRun(workflowRunId)
    },
    onSuccess: (response) => {
      if (response.status === 'blocked') {
        showToast(response.message ?? 'Compute not connected', 'info')
      } else {
        showToast('Workflow submitted to compute', 'success')
      }
      queryClient.invalidateQueries({ queryKey: ['workflow-nodes', workflowRunId] })
    },
    onError: () => showToast('Failed to start workflow', 'error'),
  })

  return (
    <section>
      <ComputeStatusStrip />

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
        ) : null}

        <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)_360px]">
          <WorkflowResourceSidebar
            projectId={projectId}
            artifacts={artifacts}
            selectedArtifactId={selectedArtifactId}
            onArtifactUploaded={(artifact) => {
              setArtifacts((current) => [artifact, ...current.filter((item) => item.artifact_id !== artifact.artifact_id)])
              setSelectedArtifactId(artifact.artifact_id)
              setSelectedNodeId(null)
            }}
            onArtifactSelected={(artifact) => {
              setSelectedArtifactId(artifact.artifact_id)
              setSelectedNodeId(null)
            }}
          />

          <main className="min-w-0">
            {workflowRun ? (
              <NodeBuilder
                open={builderOpen && !readOnly}
                onClose={() => setBuilderOpen(false)}
                onAdd={async (template, nodeName, methods, parameters) => {
                  try {
                    await canvasRef.current?.addNodeFromTemplate(template, nodeName, methods, parameters)
                    showToast(`Added "${nodeName}" to workflow`, 'success')
                    setBuilderOpen(false)
                    queryClient.invalidateQueries({ queryKey: ['workflow-nodes', workflowRunId] })
                  } catch (err) {
                    const message =
                      err instanceof Error ? err.message : 'Failed to add workflow node'
                    showToast(message, 'error')
                    throw err
                  }
                }}
              />
            ) : null}

            <WorkflowCanvas
              ref={canvasRef}
              initialNodes={graph?.nodes}
              initialEdges={graph?.edges}
              workflowRunId={workflowRun?.workflow_run_id}
              readOnly={readOnly}
              onNodeSelected={(nodeId) => {
                setSelectedNodeId(nodeId)
                if (nodeId) setSelectedArtifactId(undefined)
              }}
              onNodeAdded={() =>
                queryClient.invalidateQueries({ queryKey: ['workflow-nodes', workflowRun?.workflow_run_id] })
              }
            />
          </main>

          <WorkflowInspector
            workflowRunId={workflowRun?.workflow_run_id}
            selectedNode={selectedNode}
            selectedArtifact={selectedArtifact}
          />
        </div>
      </ApiState>
    </section>
  )
}
