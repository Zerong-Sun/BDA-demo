import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Play, Plus, Sparkles } from 'lucide-react'
import { WorkflowCanvas, type WorkflowCanvasHandle } from '../features/workflow/WorkflowCanvas'
import { NodeBuilder } from '../features/workflow/NodeBuilder'
import { mapApiGraphToGraph } from '../features/workflow/workflowMapper'
import { ComputeStatusStrip } from '../features/workflow/ComputeStatusStrip'
import { WorkflowResourceSidebar } from '../features/workflow/WorkflowResourceSidebar'
import { WorkflowInspector } from '../features/workflow/WorkflowInspector'
import { defaultWorkflowEdges, defaultWorkflowNodes, type NodeTemplate } from '../features/workflow/workflowTypes'
import { ApiState } from '../components/ui/ApiState'
import { getLatestWorkflowRunOrNull, listProjectWorkflowRuns } from '../lib/api/projects'
import { createWorkflowRun, getWorkflowGraph, submitWorkflowRun } from '../lib/api/workflow'
import { applyRoutePlan, planRoute, type RoutePlan } from '../lib/api/copilot'
import { listProjectArtifacts } from '../lib/api/artifacts'
import { useProjectContext } from '../lib/hooks/useProjectContext'
import { useAppStore } from '../lib/store/appStore'
import { useToastStore } from '../components/ui/toastStore'
import { useI18n } from '../lib/i18n'
import type { Artifact } from '../lib/schemas/artifact'
import { ProjectContextBar } from '../features/projects/ProjectContextBar'
import type { ModelPlugin } from '../lib/schemas/registry'

function workflowNodeTypeForPlugin(plugin: ModelPlugin) {
  if (plugin.model_name === 'RFdiffusion') return 'backbone_generation'
  if (plugin.model_name === 'ProteinMPNN') return 'sequence_generation'
  if (['AlphaFold2', 'AlphaFold 3', 'Boltz', 'Chai-1'].includes(plugin.model_name)) return 'fold_prediction'
  if (plugin.model_name === 'Rosetta') return 'scoring'
  if (plugin.model_name === 'BindCraft') return 'workflow_pipeline'
  return plugin.model_type
}

function templateForPlugin(plugin: ModelPlugin): NodeTemplate {
  return {
    id: plugin.model_plugin_id,
    icon: plugin.model_name === 'RFdiffusion' ? 'wand-sparkles' : 'activity',
    title: plugin.model_name,
    body: plugin.description ?? `${plugin.model_type} model plugin`,
    resource: plugin.model_type.includes('manual') ? 'manual' : plugin.model_type.includes('gpu') ? 'gpu' : 'cpu',
    nodeType: workflowNodeTypeForPlugin(plugin),
    modelName: plugin.model_name,
    modelVersion: plugin.version,
    pluginId: plugin.model_plugin_id,
    parameterSchema: plugin.parameter_schema_json,
  }
}

function parseRecord(value: unknown): Record<string, unknown> {
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

function routeLabel(runId: string, metrics: unknown) {
  const route = String(parseRecord(metrics).route ?? '')
  if (route === 'monellin_redesign') return 'Monellin route'
  if (route === 'brazzein_redesign') return 'Brazzein route'
  if (route === 'monellin') return 'Monellin route'
  if (route === 'brazzein') return 'Brazzein route'
  if (runId.includes('449a8216')) return 'Monellin route'
  if (runId.includes('bbe4a091')) return 'Brazzein route'
  return runId.replace(/^run_/, '').slice(-18)
}

function parseLayoutNodeCount(run: { layout_json?: string | null }) {
  if (!run.layout_json) return 0
  try {
    const parsed = JSON.parse(run.layout_json) as { nodes?: unknown[] }
    return Array.isArray(parsed.nodes) ? parsed.nodes.length : 0
  } catch {
    return 0
  }
}

export function WorkflowPage() {
  const [builderOpen, setBuilderOpen] = useState(false)
  const [goal, setGoal] = useState('Design 10,000 PD-1 binder candidates and nominate 48 constructs for BLI/SEC validation.')
  const [routePlan, setRoutePlan] = useState<RoutePlan | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState<string>('')
  const [selectedModuleIds, setSelectedModuleIds] = useState<string[]>([])
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

  const { data: projectWorkflowRuns = [] } = useQuery({
    queryKey: ['workflow-runs', projectId],
    queryFn: () => listProjectWorkflowRuns(projectId),
    enabled: Boolean(projectId),
  })

  const routeIds = useMemo(() => new Set(projectWorkflowRuns.map((run) => run.workflow_run_id)), [projectWorkflowRuns])
  const preferredWorkflowRun = useMemo(() => {
    if (projectWorkflowRuns.length === 0) return latestWorkflowRun ?? null
    return [...projectWorkflowRuns].sort((a, b) => {
      const aNodes = parseLayoutNodeCount(a)
      const bNodes = parseLayoutNodeCount(b)
      if (aNodes !== bNodes) return bNodes - aNodes
      if (a.status !== b.status) {
        if (a.status === 'completed') return -1
        if (b.status === 'completed') return 1
      }
      return a.workflow_run_id.localeCompare(b.workflow_run_id)
    })[0] ?? latestWorkflowRun ?? null
  }, [latestWorkflowRun, projectWorkflowRuns])

  const cachedWorkflowRun = projectWorkflowRuns.find((run) => run.workflow_run_id === applicationWorkflowRunId)
  const cachedNodeCount = cachedWorkflowRun ? parseLayoutNodeCount(cachedWorkflowRun) : 0
  const preferredNodeCount = preferredWorkflowRun ? parseLayoutNodeCount(preferredWorkflowRun) : 0
  const cachedWorkflowRunId =
    applicationWorkflowRunId && routeIds.has(applicationWorkflowRunId) && (cachedNodeCount > 0 || preferredNodeCount === 0)
      ? applicationWorkflowRunId
      : undefined

  const workflowRunId =
    cachedWorkflowRunId ??
    preferredWorkflowRun?.workflow_run_id ??
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

  const selectedRoute = routePlan?.route_options.find((route) => route.route_id === selectedRouteId) ?? null

  const createWorkflow = useMutation({
    mutationFn: () => createWorkflowRun(projectId),
    onSuccess: (run) => {
      setProjectWorkflowRunId(projectId, run.workflow_run_id)
      queryClient.invalidateQueries({ queryKey: ['workflow-graph', run.workflow_run_id] })
      showToast('Workflow run created', 'success')
    },
    onError: () => showToast('Failed to create workflow run', 'error'),
  })

  const generatePlan = useMutation({
    mutationFn: () =>
      planRoute({
        project_id: projectId,
        target: goal,
        objective: goal,
      }),
    onSuccess: (plan) => {
      const recommended = plan.route_options.find((route) => route.recommended) ?? plan.route_options[0]
      setRoutePlan(plan)
      setSelectedRouteId(recommended?.route_id ?? '')
      setSelectedModuleIds(recommended?.modules.filter((module) => module.available).map((module) => module.module_id) ?? [])
      showToast('Route options prepared from project knowledge', 'success')
    },
    onError: (error) =>
      showToast(
        error instanceof Error ? `Failed to prepare route options: ${error.message}` : 'Failed to prepare route options',
        'error',
      ),
  })

  const applyPlannedRoute = useMutation({
    mutationFn: async () => {
      if (!selectedRoute) throw new Error('Select a route first')
      return applyRoutePlan({
        project_id: projectId,
        route_id: selectedRoute.route_id,
        objective: goal,
        target: routePlan?.target ?? goal,
        selected_module_ids: selectedModuleIds,
      })
    },
    onSuccess: (result) => {
      const runId = String(result.workflow_run.workflow_run_id)
      setProjectWorkflowRunId(projectId, runId)
      showToast('Selected route created as a workflow', 'success')
      queryClient.invalidateQueries({ queryKey: ['workflow-runs', projectId] })
      queryClient.invalidateQueries({ queryKey: ['workflow-run', 'latest', projectId] })
      queryClient.invalidateQueries({ queryKey: ['workflow-graph', runId] })
    },
    onError: () => showToast('Failed to create selected route', 'error'),
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

  const addPluginNode = async (plugin: ModelPlugin) => {
    if (!workflowRunId || readOnly) return
    try {
      await canvasRef.current?.addNodeFromTemplate(templateForPlugin(plugin), plugin.model_name, [], {})
      showToast(`Added ${plugin.model_name} to workflow`, 'success')
      queryClient.invalidateQueries({ queryKey: ['workflow-graph', workflowRunId] })
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Failed to add plugin node', 'error')
    }
  }

  return (
    <section>
      <ProjectContextBar />
      <ComputeStatusStrip />

      {projectWorkflowRuns.length > 1 ? (
        <div className="mb-4 flex flex-wrap items-center gap-2 rounded-lg border border-bda-border bg-bda-panel px-3 py-2">
          <span className="text-xs uppercase tracking-wide text-bda-cyan">Routes</span>
          {projectWorkflowRuns.map((run) => (
            <button
              key={run.workflow_run_id}
              type="button"
              className={`rounded-md border px-3 py-1.5 text-xs ${
                run.workflow_run_id === workflowRunId
                  ? 'border-bda-cyan bg-bda-cyan/10 text-bda-cyan'
                  : 'border-bda-border text-bda-muted hover:border-bda-cyan/50 hover:text-bda-text'
              }`}
              onClick={() => {
                setProjectWorkflowRunId(projectId, run.workflow_run_id)
                setSelectedNodeId(null)
                setSelectedArtifactId(undefined)
              }}
            >
              {routeLabel(run.workflow_run_id, run.summary_metrics_json)} · {run.status}
            </button>
          ))}
        </div>
      ) : null}

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
            {workflowRunId ? (
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-md border border-bda-border px-3 py-2 text-sm font-medium text-bda-text hover:border-bda-cyan/50 disabled:opacity-50"
                disabled={createWorkflow.isPending}
                onClick={() => createWorkflow.mutate()}
                title="Create an additional workflow route under the active project"
              >
                <Plus className="h-4 w-4" />
                New route
              </button>
            ) : null}
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
        {isDemoMode ? (
          <span className="text-xs text-bda-muted">Demo mode: displaying read-only reference project data.</span>
        ) : workflowRun ? (
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
        {!isDemoMode && (!workflowRunId || workflowNodes.length === 0) ? (
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
                  placeholder="Example: Create a new anti-insect protein project, infer routes from the knowledge base, and generate an auditable workflow."
                />
              </div>
              <button
                type="button"
                className="inline-flex items-center justify-center gap-2 rounded-md bg-bda-cyan px-4 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
                disabled={generatePlan.isPending || readOnly || !goal.trim()}
                onClick={() => generatePlan.mutate()}
              >
                <Sparkles className="h-4 w-4" />
                Plan routes
              </button>
            </div>
            {routePlan ? (
              <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(280px,360px)]">
                <div className="grid gap-3">
                  <div className="flex flex-wrap gap-2">
                    {routePlan.route_options.map((route) => (
                      <button
                        key={route.route_id}
                        type="button"
                        className={`rounded-md border px-3 py-2 text-left text-sm ${
                          route.route_id === selectedRouteId
                            ? 'border-bda-cyan bg-bda-cyan/10 text-bda-cyan'
                            : 'border-bda-border text-bda-text hover:border-bda-cyan/50'
                        }`}
                        onClick={() => {
                          setSelectedRouteId(route.route_id)
                          setSelectedModuleIds(route.modules.filter((module) => module.available).map((module) => module.module_id))
                        }}
                      >
                        <span className="block font-medium">{route.label}</span>
                        <span className="block text-xs text-bda-muted">{route.estimated_steps} modules</span>
                      </button>
                    ))}
                  </div>
                  {selectedRoute ? (
                    <div className="grid gap-3">
                      <div>
                        <p className="text-sm text-bda-text">{selectedRoute.summary}</p>
                        <ul className="mt-2 grid gap-1 text-xs text-bda-muted">
                          {selectedRoute.rationale.map((item) => <li key={item}>{item}</li>)}
                        </ul>
                      </div>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {selectedRoute.modules.map((module) => (
                          <label
                            key={module.module_id}
                            className={`flex items-start gap-2 rounded-md border border-bda-border bg-bda-bg p-3 text-sm ${
                              module.available ? 'text-bda-text' : 'text-bda-muted opacity-70'
                            }`}
                          >
                            <input
                              type="checkbox"
                              className="mt-1"
                              disabled={!module.available}
                              checked={selectedModuleIds.includes(module.module_id)}
                              onChange={(event) => {
                                setSelectedModuleIds((current) =>
                                  event.target.checked
                                    ? [...new Set([...current, module.module_id])]
                                    : current.filter((id) => id !== module.module_id),
                                )
                              }}
                            />
                            <span>
                              <span className="block font-medium">{module.model_name}</span>
                              <span className="block text-xs text-bda-muted">{module.summary}</span>
                            </span>
                          </label>
                        ))}
                      </div>
                      <button
                        type="button"
                        className="inline-flex w-fit items-center gap-2 rounded-md bg-bda-green px-3 py-2 text-sm font-medium text-bda-bg disabled:opacity-50"
                        disabled={applyPlannedRoute.isPending || selectedModuleIds.length === 0}
                        onClick={() => applyPlannedRoute.mutate()}
                      >
                        <Sparkles className="h-4 w-4" />
                        Create workflow from selected route
                      </button>
                    </div>
                  ) : null}
                </div>
                <aside className="grid gap-3 text-xs text-bda-muted">
                  <div>
                    <p className="mb-1 uppercase tracking-wide text-bda-cyan">Knowledge used</p>
                    <ul className="grid gap-1">
                      {routePlan.knowledge_context.map((item) => (
                        <li key={item.knowledge_entry_id}>{item.title}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="mb-1 uppercase tracking-wide text-bda-cyan">Analysis process</p>
                    <ol className="grid gap-1">
                      {routePlan.analysis_trace.map((item) => <li key={item}>{item}</li>)}
                    </ol>
                  </div>
                </aside>
              </div>
            ) : (
              <p className="mt-3 text-xs text-bda-muted">New projects can build a knowledge-guided route first, choose modules, and then create a workflow graph for script preview and submission.</p>
            )}
          </section>
        ) : null}

        {!workflowRunId && !isDemoMode ? (
          <div className="mb-4 rounded-lg border border-dashed border-bda-border bg-bda-panel p-6 text-center text-sm text-bda-muted">
            <p>This project does not have a workflow run yet. Create an empty run or enter an objective to generate a project-specific recommended workflow.</p>
          </div>
        ) : null}

        <div className="grid gap-4 2xl:grid-cols-[320px_minmax(0,1fr)_360px]">
          <div className="order-2 2xl:order-1">
            <WorkflowResourceSidebar
              projectId={projectId}
              artifacts={visibleArtifacts}
              selectedNode={selectedNode}
              selectedArtifactId={selectedArtifactId}
              onArtifactUploaded={(artifact) => {
                setArtifacts((current) => [artifact, ...current.filter((item) => item.artifact_id !== artifact.artifact_id)])
                queryClient.invalidateQueries({ queryKey: ['project-artifacts', projectId] })
                setSelectedArtifactId(artifact.artifact_id)
                setSelectedNodeId(null)
              }}
              onArtifactSelected={(artifact) => {
                setSelectedArtifactId(artifact.artifact_id)
                setSelectedNodeId(null)
              }}
              onPluginAdd={(plugin) => void addPluginNode(plugin)}
              readOnly={readOnly || !workflowRunId}
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
                    setSelectedArtifactId(undefined)
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
