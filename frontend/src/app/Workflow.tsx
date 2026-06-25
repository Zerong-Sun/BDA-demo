import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Play, Plus, Sparkles } from 'lucide-react'
import { WorkflowCanvas, type WorkflowCanvasHandle } from '../features/workflow/WorkflowCanvas'
import { NodeBuilder } from '../features/workflow/NodeBuilder'
import { mapApiGraphToGraph } from '../features/workflow/workflowMapper'
import { ComputeStatusStrip } from '../features/workflow/ComputeStatusStrip'
import { WorkflowResourceSidebar } from '../features/workflow/WorkflowResourceSidebar'
import { WorkflowInspector } from '../features/workflow/WorkflowInspector'
import { buildRecommendedWorkflow, defaultWorkflowEdges, defaultWorkflowNodes, nodeTemplates } from '../features/workflow/workflowTypes'
import { ApiState } from '../components/ui/ApiState'
import { getLatestWorkflowRunOrNull } from '../lib/api/projects'
import {
  addWorkflowNode,
  createWorkflowRun,
  evaluateReadyWorkflowNodes,
  getWorkflowAutomationPolicy,
  getWorkflowGraph,
  saveWorkflowLayout,
  submitWorkflowRun,
  updateWorkflowAutomationPolicy,
} from '../lib/api/workflow'
import { listProjectArtifacts } from '../lib/api/artifacts'
import { useProjectContext } from '../lib/hooks/useProjectContext'
import { useAppStore } from '../lib/store/appStore'
import { useToastStore } from '../components/ui/toastStore'
import { useI18n } from '../lib/i18n'
import type { Artifact } from '../lib/schemas/artifact'
import { ProjectContextBar } from '../features/projects/ProjectContextBar'

export function WorkflowPage() {
  const [builderOpen, setBuilderOpen] = useState(false)
  const [goal, setGoal] = useState('设计 10000 个 PD-1 binder 候选，并筛到 48 个进入 BLI/SEC 验证')
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | undefined>()
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const canvasRef = useRef<WorkflowCanvasHandle>(null)
  const { projectId } = useProjectContext()
  const { t } = useI18n()
  const appMode = useAppStore((s) => s.appMode)
  const workflowRunIdsByProject = useAppStore((s) => s.workflowRunIdsByProject)
  const setProjectWorkflowRunId = useAppStore((s) => s.setProjectWorkflowRunId)
  const showToast = useToastStore((s) => s.show)
  const queryClient = useQueryClient()
  const isDemoMode = appMode === 'demo'
  const applicationWorkflowRunId = workflowRunIdsByProject[projectId]

  const {
    data: latestWorkflowRun,
    isError: workflowError,
    error: workflowQueryError,
    refetch: refetchWorkflow,
  } = useQuery({
    queryKey: ['workflow-run', 'latest', projectId],
    queryFn: () => getLatestWorkflowRunOrNull(projectId),
    enabled: Boolean(projectId),
  })

  const workflowRunId =
    applicationWorkflowRunId ??
    latestWorkflowRun?.workflow_run_id

  const { data: workflowGraph } = useQuery({
    queryKey: ['workflow-graph', workflowRunId],
    queryFn: () => getWorkflowGraph(workflowRunId!),
    enabled: Boolean(workflowRunId),
    refetchInterval: (query) => {
      const nodes = query.state.data?.nodes ?? []
      return nodes.some((node) => ['queued', 'staging', 'running', 'collecting_outputs'].includes(node.status)) ? 3000 : false
    },
  })
  const { data: automationPolicy } = useQuery({
    queryKey: ['workflow-automation-policy', workflowRunId],
    queryFn: () => getWorkflowAutomationPolicy(workflowRunId!),
    enabled: Boolean(workflowRunId),
  })

  const { data: projectArtifacts = [] } = useQuery({
    queryKey: ['project-artifacts', projectId],
    queryFn: () => listProjectArtifacts(projectId),
  })

  const workflowNodes = useMemo(() => workflowGraph?.nodes ?? [], [workflowGraph?.nodes])
  const workflowArtifacts = useMemo(
    () => workflowGraph?.artifacts ?? [],
    [workflowGraph?.artifacts],
  )
  const visibleArtifacts = useMemo(() => {
    const byId = new Map<string, Artifact>()
    for (const artifact of [...workflowArtifacts, ...projectArtifacts, ...artifacts]) {
      byId.set(artifact.artifact_id, artifact)
    }
    return Array.from(byId.values())
  }, [artifacts, projectArtifacts, workflowArtifacts])

  const graph = useMemo(
    () => (workflowNodes.length > 0 ? mapApiGraphToGraph(workflowNodes, workflowGraph?.edges ?? []) : null),
    [workflowGraph?.edges, workflowNodes],
  )
  const selectedNode = workflowNodes.find((node) => node.node_run_id === selectedNodeId) ?? null
  const selectedArtifact = visibleArtifacts.find((artifact) => artifact.artifact_id === selectedArtifactId) ?? null

  const workflowRun = workflowGraph?.workflow_run ?? latestWorkflowRun
  const readOnly = isDemoMode || workflowRun?.status === 'completed'

  const createWorkflow = useMutation({
    mutationFn: () => createWorkflowRun(projectId),
    onSuccess: (run) => {
      setProjectWorkflowRunId(projectId, run.workflow_run_id)
      queryClient.invalidateQueries({ queryKey: ['workflow-graph', run.workflow_run_id] })
      showToast('Workflow run created', 'success')
    },
    onError: () => showToast('Failed to create workflow run', 'error'),
  })

  const generateRecommended = useMutation({
    mutationFn: async () => {
      const runId = applicationWorkflowRunId ?? (await createWorkflowRun(projectId)).workflow_run_id
      setProjectWorkflowRunId(projectId, runId)
      const steps = buildRecommendedWorkflow(goal)
      const existingNodes = graph?.nodes ?? []
      const existingEdges = graph?.edges ?? []
      const branchIndex = Math.floor(existingNodes.length / Math.max(steps.length, 1))
      const baseY = existingNodes.length === 0 ? 110 : 130 + branchIndex * 190
      const createdNodes: Array<{ id: string; position: { x: number; y: number } }> = []

      for (const [index, step] of steps.entries()) {
        const template = nodeTemplates[step.templateId]
        const col = index % 3
        const row = Math.floor(index / 3)
        const x = 80 + col * 280
        const y = baseY + row * 210
        const created = await addWorkflowNode(runId, {
          node_type: template.nodeType,
          node_name: step.name,
          model_name: template.modelName,
          model_version: template.modelVersion,
          model_plugin_id: template.pluginId,
          parameters_json: {
            methods: step.methods,
            ...step.parameters,
            copilot_goal: goal,
            planned: step.estimate.planned,
            current: step.estimate.current,
            estimate_unit: step.estimate.unit,
            estimated_time: step.estimate.duration,
          },
          position: { x, y },
        })
        createdNodes.push({ id: created.node_run_id, position: { x, y } })
      }

      const createdEdges = createdNodes.slice(0, -1).map((node, index) => ({
        id: `e-${node.id}-${createdNodes[index + 1].id}`,
        source_node_run_id: node.id,
        target_node_run_id: createdNodes[index + 1].id,
        source_port: 'output',
        target_port: 'input',
        edge_type: 'data',
      }))

      await saveWorkflowLayout(runId, {
        nodes: [
          ...existingNodes.map((node) => ({ node_run_id: node.id, position: node.position })),
          ...createdNodes.map((node) => ({ node_run_id: node.id, position: node.position })),
        ],
        edges: [
          ...existingEdges.map((edge) => ({
            id: edge.id,
            source_node_run_id: edge.source,
            target_node_run_id: edge.target,
            source_port: typeof edge.sourceHandle === 'string' ? edge.sourceHandle : 'output',
            target_port: typeof edge.targetHandle === 'string' ? edge.targetHandle : 'input',
            edge_type: edge.label === 'feedback' ? 'feedback' : 'data',
          })),
          ...createdEdges,
        ],
      })
      return runId
    },
    onSuccess: (runId) => {
      showToast('Recommended workflow generated and connected', 'success')
      queryClient.invalidateQueries({ queryKey: ['workflow-graph', runId] })
    },
    onError: () => showToast('Failed to generate recommended workflow', 'error'),
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
      queryClient.invalidateQueries({ queryKey: ['workflow-graph', workflowRunId] })
      queryClient.invalidateQueries({ queryKey: ['workflow-jobs', workflowRunId] })
    },
    onError: () => showToast('Failed to start workflow', 'error'),
  })
  const updateAutomation = useMutation({
    mutationFn: (mode: 'confirm_each_node' | 'auto_after_gate' | 'advisory_only') => {
      if (!workflowRunId) throw new Error('No workflow run available')
      return updateWorkflowAutomationPolicy(workflowRunId, {
        mode,
        auto_submit_ready: mode === 'auto_after_gate',
        notify_on_ready: true,
        notify_on_terminal: true,
        max_auto_retries: mode === 'auto_after_gate' ? 1 : 0,
        retry_backoff_seconds: 60,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-automation-policy', workflowRunId] })
      showToast('Automation policy updated', 'success')
    },
  })
  const evaluateReady = useMutation({
    mutationFn: () => evaluateReadyWorkflowNodes(workflowRunId!),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['workflow-graph', workflowRunId] })
      queryClient.invalidateQueries({ queryKey: ['workflow-jobs', workflowRunId] })
      showToast(
        `${result.ready_nodes.length} ready · ${result.waiting_external_nodes.length} waiting external`,
        'info',
      )
    },
  })

  return (
    <section>
      <ProjectContextBar />
      <ComputeStatusStrip />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {!workflowRunId && !isDemoMode ? (
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-md bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
            disabled={createWorkflow.isPending}
            onClick={() => createWorkflow.mutate()}
          >
            <Plus className="h-4 w-4" />
            Create workflow run
          </button>
        ) : isDemoMode ? null : (
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
              disabled={readOnly || startWorkflow.isPending}
              onClick={() => startWorkflow.mutate()}
            >
              <Play className="h-4 w-4" />
              {t.workflow.startWorkflow}
            </button>
          </>
        )}
        {isDemoMode ? (
          <span className="text-xs text-bda-muted">演示模式：读取项目已有演示数据，只读展示。</span>
        ) : workflowRun ? (
          <span className="text-xs text-bda-muted">
            Run {workflowRun.workflow_run_id} · {workflowRun.status}
          </span>
        ) : (
          <span className="text-xs text-bda-muted">No workflow run for this project yet</span>
        )}
        {workflowRunId && !isDemoMode ? (
          <>
            <select
              aria-label="Workflow automation policy"
              className="rounded border border-bda-border bg-bda-panel px-2 py-2 text-xs"
              value={automationPolicy?.mode ?? 'confirm_each_node'}
              disabled={updateAutomation.isPending}
              onChange={(event) => updateAutomation.mutate(
                event.target.value as 'confirm_each_node' | 'auto_after_gate' | 'advisory_only',
              )}
            >
              <option value="confirm_each_node">Confirm each node</option>
              <option value="auto_after_gate">Auto after approved gate</option>
              <option value="advisory_only">Advisory only</option>
            </select>
            <button
              type="button"
              className="rounded border border-bda-border px-2 py-2 text-xs"
              disabled={evaluateReady.isPending}
              onClick={() => evaluateReady.mutate()}
            >
              Evaluate gates
            </button>
          </>
        ) : null}
      </div>

      <ApiState
        isError={workflowError}
        error={workflowQueryError}
        onRetry={() => void refetchWorkflow()}
      >
        {!isDemoMode ? (
          <section className="mb-4 rounded-lg border border-bda-border bg-bda-panel p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
              <div className="min-w-0 flex-1">
                <label htmlFor="workflow-goal" className="mb-1 block text-xs uppercase tracking-wide text-bda-cyan">
                  Copilot route planner
                </label>
                <textarea
                  id="workflow-goal"
                  rows={2}
                  className="w-full resize-none rounded-md border border-bda-border bg-bda-bg px-3 py-2 text-sm text-bda-text"
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="输入你想做的事情，例如：设计 10000 个候选并筛选 48 个进入湿实验"
                />
              </div>
              <button
                type="button"
                className="inline-flex items-center justify-center gap-2 rounded-md bg-bda-cyan px-4 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
                disabled={generateRecommended.isPending || readOnly || !goal.trim()}
                onClick={() => generateRecommended.mutate()}
              >
                <Sparkles className="h-4 w-4" />
                生成推荐工作流
              </button>
            </div>
            <p className="mt-3 text-xs text-bda-muted">
              点击生成后才会在画布中创建真实节点和连线；生成前当前项目工作流保持为空。
            </p>
          </section>
        ) : null}

        {!workflowRunId && !isDemoMode ? (
          <div className="mb-4 rounded-lg border border-dashed border-bda-border bg-bda-panel p-6 text-center text-sm text-bda-muted">
            <p>当前项目还没有工作流。你可以手动创建空 run，也可以直接输入目标生成一套项目绑定的推荐工作流。</p>
          </div>
        ) : null}

        <div className="grid gap-4 2xl:grid-cols-[320px_minmax(0,1fr)_360px]">
          <div className="order-2 2xl:order-1">
            <WorkflowResourceSidebar
              projectId={projectId}
              artifacts={visibleArtifacts}
              selectedArtifactId={selectedArtifactId}
              onArtifactUploaded={(artifact) => {
                setArtifacts((current) => [artifact, ...current.filter((item) => item.artifact_id !== artifact.artifact_id)])
                queryClient.invalidateQueries({ queryKey: ['project-artifacts', projectId] })
                setSelectedArtifactId(artifact.artifact_id)
                setSelectedNodeId(null)
              }}
              onArtifactSelected={(artifact) => {
                setSelectedArtifactId(artifact.artifact_id)
              }}
            />
          </div>

          <main className="order-1 min-w-0 2xl:order-2">
            {isDemoMode ? (
              <WorkflowCanvas
                initialNodes={defaultWorkflowNodes}
                initialEdges={defaultWorkflowEdges}
                readOnly
                onNodeSelected={setSelectedNodeId}
              />
            ) : workflowRunId ? (
              <>
                <NodeBuilder
                  open={builderOpen && !readOnly}
                  onClose={() => setBuilderOpen(false)}
                  onAdd={async (template, nodeName, methods, parameters) => {
                    try {
                      await canvasRef.current?.addNodeFromTemplate(template, nodeName, methods, parameters)
                      showToast(`Added "${nodeName}" to workflow`, 'success')
                      setBuilderOpen(false)
                      queryClient.invalidateQueries({ queryKey: ['workflow-graph', workflowRunId] })
                    } catch (err) {
                      const message =
                        err instanceof Error ? err.message : 'Failed to add workflow node'
                      showToast(message, 'error')
                      throw err
                    }
                  }}
                />

                <WorkflowCanvas
                  ref={canvasRef}
                  initialNodes={graph?.nodes ?? []}
                  initialEdges={graph?.edges ?? []}
                  workflowRunId={workflowRunId}
                  readOnly={readOnly}
                  onNodeSelected={(nodeId) => {
                    setSelectedNodeId(nodeId)
                    if (nodeId) setSelectedArtifactId(undefined)
                  }}
                  onNodeAdded={() =>
                    queryClient.invalidateQueries({ queryKey: ['workflow-graph', workflowRunId] })
                  }
                />
              </>
            ) : (
              <WorkflowCanvas initialNodes={[]} initialEdges={[]} />
            )}
          </main>

          <div className="order-3">
            <WorkflowInspector
              key={selectedNode?.node_run_id ?? selectedArtifact?.artifact_id ?? 'workflow-summary'}
              workflowRunId={workflowRunId}
              selectedNode={selectedNode}
              selectedArtifact={selectedArtifact}
            />
          </div>
        </div>
      </ApiState>
    </section>
  )
}
