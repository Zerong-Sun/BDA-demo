import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  CheckCircle2,
  Cpu,
  FileText,
  PackageCheck,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Terminal,
  TriangleAlert,
} from 'lucide-react'

import { ProjectContextBar } from '../features/projects/ProjectContextBar'
import { deliveryPackageDownloadUrl } from '../lib/api/client'
import { listProjectWorkflowRuns, getDeliveryPackageOrNull } from '../lib/api/projects'
import { listProjectCampaigns } from '../lib/api/campaigns'
import { cancelJob, listWorkflowJobs, syncJobResult } from '../lib/api/jobs'
import { applyRoutePlan, planRoute, searchCopilotKnowledge, type RoutePlan } from '../lib/api/copilot'
import {
  createModelPlugin,
  createServer,
  drainComputeNode,
  getClusterHealth,
  listComputeNodes,
  listModelPlugins,
  listServers,
  listScriptAssets,
  testServerConnection,
  validateModelPlugin,
} from '../lib/api/registry'
import { useProjectContext } from '../lib/hooks/useProjectContext'
import { useAppStore } from '../lib/store/appStore'
import { useToastStore } from '../components/ui/toastStore'
import { StatusPill } from '../components/ui/StatusPill'
import { statusTone } from '../components/ui/statusTone'
import {
  createBenchmarkRun,
  createDataset,
  createParameterPreset,
  createWorkflowTemplate,
  listBenchmarkRuns,
  listDatasets,
  listParameterPresets,
  listWorkflowTemplates,
} from '../lib/api/platformRegistry'
import type { Job } from '../lib/schemas/job'
import type { ModelPlugin } from '../lib/schemas/registry'

function asRecord(value: unknown): Record<string, unknown> {
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

function portCount(schema: unknown) {
  const ports = asRecord(schema).ports
  return Array.isArray(ports) ? ports.length : 0
}

function fieldCount(schema: unknown) {
  const fields = asRecord(schema).fields
  return Array.isArray(fields) ? fields.length : 0
}

function outputArtifactCount(job: Job) {
  const output = asRecord(job.output_artifacts)
  const artifacts = output.artifacts
  return Array.isArray(artifacts) ? artifacts.length : 0
}

function projectPath(path: string, projectId: string) {
  return projectId ? `${path}?project=${encodeURIComponent(projectId)}` : path
}

function parseJsonObject(value: string, label: string): Record<string, unknown> {
  const trimmed = value.trim()
  if (!trimmed) return {}
  const parsed = JSON.parse(trimmed) as unknown
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error(`${label} must be a JSON object.`)
  }
  return parsed as Record<string, unknown>
}

function parseList(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean)
}

function pluginRisk(plugin: ModelPlugin) {
  const resource = asRecord(plugin.resource_requirement_json)
  const inputs = portCount(plugin.input_schema_json)
  const outputs = portCount(plugin.output_schema_json)
  const fields = fieldCount(plugin.parameter_schema_json)
  if (plugin.status === 'restricted') return 'restricted'
  if (!inputs || !outputs || !fields) return 'needs schema'
  if (resource.gpu_count || resource.min_vram_gb) return 'gpu gated'
  return 'ready'
}

function referenceNotes(plugin: ModelPlugin) {
  if (plugin.model_name !== 'RFdiffusion') return []
  const resource = asRecord(plugin.resource_requirement_json)
  return [
    `${fieldCount(plugin.parameter_schema_json)} editable parameters`,
    `${portCount(plugin.input_schema_json)} input ports, ${portCount(plugin.output_schema_json)} output ports`,
    `GPU ${String(resource.gpu_count ?? 1)}, minimum VRAM ${String(resource.min_vram_gb ?? 24)} GB`,
    'Script preview, checksum review, input manifest, and output manifest are the reference execution contract.',
  ]
}

const PLATFORM_TEMPLATES = [
  {
    id: 'enzyme',
    label: 'Enzyme optimization',
    query: 'enzyme catalysis active site substrate thermal pH',
    objective: 'Create an enzyme optimization workflow that preserves active-site residues while improving stability, solubility, and assay readiness.',
  },
  {
    id: 'antigen',
    label: 'Antigen display',
    query: 'antigen epitope vaccine nanoparticle display',
    objective: 'Create an antigen display workflow that preserves epitope geometry and packages constructs for immunogen validation.',
  },
  {
    id: 'cage',
    label: 'Protein cage assembly',
    query: 'protein cage symmetry assembly nanocage multimer',
    objective: 'Create a symmetric protein cage assembly workflow with interface scoring and multimer confidence gates.',
  },
  {
    id: 'intracellular',
    label: 'Intracellular tool',
    query: 'intracellular compact binder degrader localization cell expression',
    objective: 'Create an intracellular protein tool workflow optimized for compact constructs, expression compatibility, and cell-based validation.',
  },
]

function PluginCard({ plugin, onValidate, validating }: { plugin: ModelPlugin; onValidate: (pluginId: string) => void; validating: boolean }) {
  const risk = pluginRisk(plugin)
  const notes = referenceNotes(plugin)
  return (
    <article className="rounded border border-bda-border bg-bda-bg p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <strong className="text-sm">{plugin.model_name}</strong>
            {plugin.model_name === 'RFdiffusion' ? (
              <span className="rounded border border-bda-cyan/40 px-1.5 py-0.5 text-[10px] uppercase text-bda-cyan">
                reference
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-bda-muted">
            {plugin.provider} · v{plugin.version} · {plugin.model_type}
          </p>
        </div>
        <StatusPill label={plugin.status} tone={statusTone(plugin.status)} />
      </div>
      <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-bda-muted">{plugin.description}</p>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <Metric label="inputs" value={portCount(plugin.input_schema_json)} />
        <Metric label="outputs" value={portCount(plugin.output_schema_json)} />
        <Metric label="params" value={fieldCount(plugin.parameter_schema_json)} />
      </div>
      {notes.length ? (
        <ul className="mt-3 grid gap-1 text-xs text-bda-muted">
          {notes.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
      <div className="mt-3 flex items-center justify-between gap-2">
        <span className={`text-xs ${risk === 'ready' ? 'text-bda-green' : risk === 'gpu gated' ? 'text-bda-amber' : 'text-bda-red'}`}>
          {risk}
        </span>
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded border border-bda-border px-2 py-1 text-xs text-bda-muted hover:text-bda-text disabled:opacity-50"
          disabled={validating}
          onClick={() => onValidate(plugin.model_plugin_id)}
        >
          <ShieldCheck className="h-3.5 w-3.5" />
          Validate
        </button>
      </div>
    </article>
  )
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded border border-bda-border bg-bda-panel p-2">
      <span className="block text-[10px] uppercase tracking-wide text-bda-muted">{label}</span>
      <strong className="mt-1 block text-sm text-bda-text">{value}</strong>
    </div>
  )
}

export function OperationsPage() {
  const navigate = useNavigate()
  const { projectId } = useProjectContext()
  const setProjectWorkflowRunId = useAppStore((state) => state.setProjectWorkflowRunId)
  const showToast = useToastStore((state) => state.show)
  const queryClient = useQueryClient()
  const [pluginFilter, setPluginFilter] = useState('all')
  const [knowledgeQuery, setKnowledgeQuery] = useState('protein design workflow evidence hierarchy developability')
  const [templatePlans, setTemplatePlans] = useState<Record<string, RoutePlan>>({})
  const [newModel, setNewModel] = useState({
    model_name: '',
    model_type: '',
    provider: 'custom',
    version: 'custom-1.0',
    description: '',
    supported_task_types: '',
    supported_file_types: '',
    container_image: '',
    command_template: '',
    api_endpoint: '',
    input_schema_json: '{\n  "ports": []\n}',
    output_schema_json: '{\n  "ports": []\n}',
    parameter_schema_json: '{\n  "fields": []\n}',
    resource_requirement_json: '{\n  "gpu_count": 0\n}',
  })
  const [newServer, setNewServer] = useState({
    server_name: '',
    server_type: 'http_worker',
    base_url: '',
    health_check_endpoint: '/health',
    capabilities_json: '{\n  "roles": []\n}',
  })
  const [platformDraft, setPlatformDraft] = useState({
    datasetName: '',
    benchmarkName: '',
    presetName: '',
    templateName: '',
  })

  const plugins = useQuery({ queryKey: ['model-plugins'], queryFn: listModelPlugins })
  const computeNodes = useQuery({ queryKey: ['compute-nodes'], queryFn: listComputeNodes })
  const servers = useQuery({ queryKey: ['servers'], queryFn: listServers })
  const clusterHealth = useQuery({ queryKey: ['cluster-health'], queryFn: getClusterHealth })
  const workflows = useQuery({
    queryKey: ['workflow-runs', projectId],
    queryFn: () => listProjectWorkflowRuns(projectId),
    enabled: Boolean(projectId),
  })
  const campaigns = useQuery({
    queryKey: ['campaigns', projectId],
    queryFn: () => listProjectCampaigns(projectId),
    enabled: Boolean(projectId),
  })
  const deliveryPackage = useQuery({
    queryKey: ['delivery-package', projectId],
    queryFn: () => getDeliveryPackageOrNull(projectId),
    enabled: Boolean(projectId),
  })
  const scriptAssets = useQuery({
    queryKey: ['script-assets'],
    queryFn: () => listScriptAssets(),
  })
  const datasets = useQuery({ queryKey: ['platform-datasets'], queryFn: listDatasets })
  const benchmarkRegistry = useQuery({ queryKey: ['platform-benchmark-runs'], queryFn: listBenchmarkRuns })
  const parameterPresets = useQuery({ queryKey: ['platform-parameter-presets'], queryFn: listParameterPresets })
  const workflowTemplates = useQuery({ queryKey: ['platform-workflow-templates'], queryFn: listWorkflowTemplates })
  const knowledge = useQuery({
    queryKey: ['copilot-knowledge', knowledgeQuery],
    queryFn: () => searchCopilotKnowledge(knowledgeQuery),
    enabled: false,
  })
  const jobQueries = useQueries({
    queries: (workflows.data ?? []).map((workflow) => ({
      queryKey: ['workflow-jobs', workflow.workflow_run_id],
      queryFn: () => listWorkflowJobs(workflow.workflow_run_id),
      enabled: Boolean(workflow.workflow_run_id),
    })),
  })

  const jobs = useMemo(
    () => jobQueries.flatMap((query) => query.data ?? []),
    [jobQueries],
  )
  const refreshJobQueries = async () => {
    await Promise.all((workflows.data ?? []).map((workflow) =>
      queryClient.invalidateQueries({ queryKey: ['workflow-jobs', workflow.workflow_run_id] }),
    ))
  }
  const activeJobs = jobs.filter((job) => ['queued', 'staging', 'running', 'collecting_outputs'].includes(job.status))
  const finishedJobs = jobs.filter((job) => ['completed', 'failed', 'cancelled'].includes(job.status))
  const pluginList = plugins.data ?? []
  const campaignItems = campaigns.data?.items ?? []
  const visiblePlugins = pluginList.filter((plugin) => pluginFilter === 'all' || plugin.model_type === pluginFilter)
  const pluginTypes = [...new Set(pluginList.map((plugin) => plugin.model_type))].sort()
  const sweetProteinActive = [plugins.data, workflows.data, campaigns.data]
    .flat()
    .some((item) => JSON.stringify(item ?? '').toLowerCase().includes('sweet') || JSON.stringify(item ?? '').toLowerCase().includes('monellin') || JSON.stringify(item ?? '').toLowerCase().includes('brazzein'))
  const benchmarkRows = pluginList.map((plugin) => {
    const pluginJobs = jobs.filter((job) => job.plugin_id === plugin.model_plugin_id)
    const completed = pluginJobs.filter((job) => job.status === 'completed').length
    const failed = pluginJobs.filter((job) => job.status === 'failed').length
    const artifacts = pluginJobs.reduce((sum, job) => sum + outputArtifactCount(job), 0)
    return {
      plugin,
      runs: pluginJobs.length,
      completed,
      failed,
      artifacts,
      successRate: pluginJobs.length ? Math.round((completed / pluginJobs.length) * 100) : null,
    }
  }).sort((a, b) => b.runs - a.runs || a.plugin.model_name.localeCompare(b.plugin.model_name))
  const activeLearningSignals = [
    {
      label: 'Exploit',
      value: jobs.filter((job) => outputArtifactCount(job) > 0).length,
      note: 'Use completed model outputs to nominate high-confidence variants.',
    },
    {
      label: 'Explore',
      value: Math.max(0, (workflows.data?.length ?? 0) - campaignItems.length),
      note: 'Route gaps suggest where diversity or alternate templates can be added.',
    },
    {
      label: 'Review',
      value: campaignItems.filter((campaign) => campaign.status !== 'completed').length,
      note: 'Open campaign decisions should feed next-round constraints.',
    },
  ]

  const validatePlugin = useMutation({
    mutationFn: validateModelPlugin,
    onSuccess: (result) => showToast(`${result.model_plugin_id} ${result.status}`, result.valid ? 'success' : 'error'),
    onError: (error) => showToast(error instanceof Error ? error.message : 'Plugin validation failed', 'error'),
  })
  const registerModel = useMutation({
    mutationFn: () => createModelPlugin({
      model_name: newModel.model_name,
      model_type: newModel.model_type,
      provider: newModel.provider,
      version: newModel.version,
      description: newModel.description || null,
      supported_task_types: parseList(newModel.supported_task_types),
      supported_file_types: parseList(newModel.supported_file_types),
      container_image: newModel.container_image || null,
      command_template: newModel.command_template || null,
      api_endpoint: newModel.api_endpoint || null,
      input_schema_json: parseJsonObject(newModel.input_schema_json, 'Input schema'),
      output_schema_json: parseJsonObject(newModel.output_schema_json, 'Output schema'),
      parameter_schema_json: parseJsonObject(newModel.parameter_schema_json, 'Parameter schema'),
      resource_requirement_json: parseJsonObject(newModel.resource_requirement_json, 'Resource requirement'),
      status: 'experimental',
    }),
    onSuccess: async (plugin) => {
      await queryClient.invalidateQueries({ queryKey: ['model-plugins'] })
      showToast(`${plugin.model_name} registered as experimental`, 'success')
      setNewModel((current) => ({ ...current, model_name: '', description: '', container_image: '', command_template: '', api_endpoint: '' }))
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Model registration failed', 'error'),
  })
  const registerServer = useMutation({
    mutationFn: () => createServer({
      server_name: newServer.server_name,
      server_type: newServer.server_type,
      base_url: newServer.base_url || null,
      health_check_endpoint: newServer.health_check_endpoint || null,
      capabilities_json: parseJsonObject(newServer.capabilities_json, 'Capabilities'),
      auth_type: 'none',
      enabled: true,
    }),
    onSuccess: async (server) => {
      await queryClient.invalidateQueries({ queryKey: ['servers'] })
      showToast(`${server.server_name} registered`, 'success')
      setNewServer((current) => ({ ...current, server_name: '', base_url: '' }))
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Server registration failed', 'error'),
  })
  const testServer = useMutation({
    mutationFn: testServerConnection,
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ['servers'] })
      showToast(result.connected ? 'Server connection available' : result.reason ?? 'Server unavailable', result.connected ? 'success' : 'error')
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Connection test failed', 'error'),
  })
  const drainNode = useMutation({
    mutationFn: drainComputeNode,
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ['compute-nodes'] })
      showToast(`${result.compute_node.node_name} draining`, 'success')
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Drain failed', 'error'),
  })
  const createPlatformDataset = useMutation({
    mutationFn: () => createDataset({
      name: platformDraft.datasetName,
      dataset_type: 'project_artifacts',
      project_id: projectId || null,
      metadata_json: { source: 'operations_quick_create' },
    }),
    onSuccess: async () => {
      setPlatformDraft((current) => ({ ...current, datasetName: '' }))
      await queryClient.invalidateQueries({ queryKey: ['platform-datasets'] })
      showToast('Dataset registered', 'success')
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Dataset registration failed', 'error'),
  })
  const createPlatformBenchmark = useMutation({
    mutationFn: () => createBenchmarkRun({
      name: platformDraft.benchmarkName,
      model_plugin_id: pluginList[0]?.model_plugin_id ?? null,
      dataset_id: datasets.data?.items[0]?.dataset_id ?? null,
      metrics_json: { success_rate: null, runs: 0 },
      context_json: { source: 'operations_quick_create' },
      status: 'planned',
    }),
    onSuccess: async () => {
      setPlatformDraft((current) => ({ ...current, benchmarkName: '' }))
      await queryClient.invalidateQueries({ queryKey: ['platform-benchmark-runs'] })
      showToast('Benchmark run planned', 'success')
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Benchmark registration failed', 'error'),
  })
  const createPlatformPreset = useMutation({
    mutationFn: () => createParameterPreset({
      name: platformDraft.presetName,
      model_plugin_id: pluginList[0]?.model_plugin_id ?? null,
      parameters_json: {},
      scope: 'model',
    }),
    onSuccess: async () => {
      setPlatformDraft((current) => ({ ...current, presetName: '' }))
      await queryClient.invalidateQueries({ queryKey: ['platform-parameter-presets'] })
      showToast('Parameter preset registered', 'success')
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Preset registration failed', 'error'),
  })
  const createPlatformTemplate = useMutation({
    mutationFn: () => createWorkflowTemplate({
      name: platformDraft.templateName,
      template_type: 'operations',
      nodes_json: [],
      edges_json: [],
      tags_json: ['operations'],
    }),
    onSuccess: async () => {
      setPlatformDraft((current) => ({ ...current, templateName: '' }))
      await queryClient.invalidateQueries({ queryKey: ['platform-workflow-templates'] })
      showToast('Workflow template registered', 'success')
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Template registration failed', 'error'),
  })
  const syncJob = useMutation({
    mutationFn: (job: Job) => syncJobResult(job.job_id),
    onSuccess: async (result) => {
      const count = Array.isArray(result.outputs?.artifacts) ? result.outputs.artifacts.length : 0
      showToast(result.outputs?.manifest_found ? `Synced ${count} artifacts` : `Job is ${result.live_status}`, result.outputs?.manifest_found ? 'success' : 'info')
      await Promise.all([
        refreshJobQueries(),
        queryClient.invalidateQueries({ queryKey: ['workflow-graph'] }),
        queryClient.invalidateQueries({ queryKey: ['project-artifacts'] }),
      ])
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Job sync failed', 'error'),
  })
  const cancel = useMutation({
    mutationFn: (job: Job) => cancelJob(job.job_id),
    onSuccess: () => refreshJobQueries(),
    onError: (error) => showToast(error instanceof Error ? error.message : 'Cancel failed', 'error'),
  })
  const draftTemplate = useMutation({
    mutationFn: async (template: typeof PLATFORM_TEMPLATES[number]) => {
      const plan = await planRoute({
        project_id: projectId,
        target: template.query,
        objective: template.objective,
        constraints: { source: 'platform_template', template_id: template.id },
      })
      return { template, plan }
    },
    onSuccess: ({ template, plan }) => {
      setTemplatePlans((current) => ({ ...current, [template.id]: plan }))
      showToast(`${template.label} routes prepared`, 'success')
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Template planning failed', 'error'),
  })
  const applyTemplate = useMutation({
    mutationFn: async (template: typeof PLATFORM_TEMPLATES[number]) => {
      const plan = templatePlans[template.id]
      const route = plan?.route_options[0]
      if (!plan || !route) throw new Error('Draft routes before creating a workflow.')
      return applyRoutePlan({
        project_id: projectId,
        route_id: route.route_id,
        objective: template.objective,
        target: plan.target,
        selected_module_ids: route.modules.filter((module) => module.available).map((module) => module.module_id),
        constraints: { source: 'platform_template', template_id: template.id },
      })
    },
    onSuccess: async (result) => {
      const runId = String(result.workflow_run.workflow_run_id)
      setProjectWorkflowRunId(projectId, runId)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['workflow-runs', projectId] }),
        queryClient.invalidateQueries({ queryKey: ['workflow-graph', runId] }),
      ])
      showToast('Platform template created as workflow', 'success')
      navigate(projectPath('/workflow', projectId))
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to create workflow from template', 'error'),
  })

  return (
    <section className="space-y-4">
      <ProjectContextBar />
      <div className="bda-card p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-bda-cyan">Operations</p>
            <h1 className="text-2xl font-semibold">Plugins, jobs, campaigns, and delivery readiness</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link className="inline-flex items-center gap-2 rounded border border-bda-border px-3 py-2 text-sm hover:border-bda-cyan/50" to={projectPath('/workflow', projectId)}>
              <Activity className="h-4 w-4" />
              Open workflow
            </Link>
            <a className="inline-flex items-center gap-2 rounded bg-bda-cyan px-3 py-2 text-sm font-medium text-bda-bg" href={deliveryPackageDownloadUrl(projectId)} target="_blank" rel="noreferrer">
              <PackageCheck className="h-4 w-4" />
              Export report package
            </a>
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
        <section className="bda-card">
          <div className="bda-card-header">
            <div>
              <p className="text-xs uppercase tracking-wide text-bda-cyan">Plugin registry</p>
              <h2 className="text-sm font-semibold">Model contracts and RFdiffusion reference plugin</h2>
            </div>
            <select
              className="rounded border border-bda-border bg-bda-bg px-2 py-1 text-xs"
              value={pluginFilter}
              onChange={(event) => setPluginFilter(event.target.value)}
            >
              <option value="all">All model types</option>
              {pluginTypes.map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
          <div className="bda-card-body">
            <form
              className="mb-4 rounded border border-bda-border bg-bda-bg p-3"
              onSubmit={(event) => {
                event.preventDefault()
                registerModel.mutate()
              }}
            >
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-xs uppercase tracking-wide text-bda-cyan">New model intake</p>
                  <h3 className="text-sm font-semibold">Register an experimental model contract</h3>
                </div>
                <button
                  type="submit"
                  className="rounded bg-bda-cyan px-3 py-1.5 text-xs font-medium text-bda-bg disabled:opacity-50"
                  disabled={registerModel.isPending || !newModel.model_name.trim() || !newModel.model_type.trim()}
                >
                  {registerModel.isPending ? 'Registering...' : 'Register model'}
                </button>
              </div>
              <div className="grid gap-2 md:grid-cols-4">
                <ModelInput label="Name" value={newModel.model_name} onChange={(value) => setNewModel((current) => ({ ...current, model_name: value }))} required />
                <ModelInput label="Type" value={newModel.model_type} onChange={(value) => setNewModel((current) => ({ ...current, model_type: value }))} required />
                <ModelInput label="Provider" value={newModel.provider} onChange={(value) => setNewModel((current) => ({ ...current, provider: value }))} />
                <ModelInput label="Version" value={newModel.version} onChange={(value) => setNewModel((current) => ({ ...current, version: value }))} />
              </div>
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                <ModelInput label="Container image" value={newModel.container_image} onChange={(value) => setNewModel((current) => ({ ...current, container_image: value }))} />
                <ModelInput label="API endpoint" value={newModel.api_endpoint} onChange={(value) => setNewModel((current) => ({ ...current, api_endpoint: value }))} />
              </div>
              <label className="mt-2 block">
                <span className="mb-1 block text-[10px] uppercase tracking-wide text-bda-muted">Command template</span>
                <input
                  className="w-full rounded border border-bda-border bg-bda-panel px-2 py-1.5 text-xs"
                  value={newModel.command_template}
                  onChange={(event) => setNewModel((current) => ({ ...current, command_template: event.target.value }))}
                  placeholder="python run_model.py --input {input_manifest} --out {output_dir}"
                />
              </label>
              <label className="mt-2 block">
                <span className="mb-1 block text-[10px] uppercase tracking-wide text-bda-muted">Description</span>
                <textarea
                  className="min-h-16 w-full rounded border border-bda-border bg-bda-panel px-2 py-1.5 text-xs"
                  value={newModel.description}
                  onChange={(event) => setNewModel((current) => ({ ...current, description: event.target.value }))}
                />
              </label>
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                <ModelInput label="Task types" value={newModel.supported_task_types} onChange={(value) => setNewModel((current) => ({ ...current, supported_task_types: value }))} placeholder="binder_design, scaffold_redesign" />
                <ModelInput label="File types" value={newModel.supported_file_types} onChange={(value) => setNewModel((current) => ({ ...current, supported_file_types: value }))} placeholder="pdb, fasta, csv" />
              </div>
              <div className="mt-2 grid gap-2 lg:grid-cols-4">
                <ModelJsonField label="Input schema" value={newModel.input_schema_json} onChange={(value) => setNewModel((current) => ({ ...current, input_schema_json: value }))} />
                <ModelJsonField label="Output schema" value={newModel.output_schema_json} onChange={(value) => setNewModel((current) => ({ ...current, output_schema_json: value }))} />
                <ModelJsonField label="Parameters" value={newModel.parameter_schema_json} onChange={(value) => setNewModel((current) => ({ ...current, parameter_schema_json: value }))} />
                <ModelJsonField label="Resources" value={newModel.resource_requirement_json} onChange={(value) => setNewModel((current) => ({ ...current, resource_requirement_json: value }))} />
              </div>
            </form>
            <div className="grid gap-3 lg:grid-cols-2">
              {visiblePlugins.map((plugin) => (
                <PluginCard
                  key={plugin.model_plugin_id}
                  plugin={plugin}
                  validating={validatePlugin.isPending}
                  onValidate={(pluginId) => validatePlugin.mutate(pluginId)}
                />
              ))}
            </div>
          </div>
        </section>

        <aside className="grid gap-4">
          <section className="bda-card">
            <div className="bda-card-header">
              <div>
                <p className="text-xs uppercase tracking-wide text-bda-cyan">Compute readiness</p>
                <h2 className="text-sm font-semibold">Cluster and script inventory</h2>
              </div>
              {clusterHealth.data?.connected ? <CheckCircle2 className="h-4 w-4 text-bda-green" /> : <TriangleAlert className="h-4 w-4 text-bda-amber" />}
            </div>
            <div className="bda-card-body grid gap-3 text-sm">
              <div className="grid grid-cols-3 gap-2">
                <Metric label="mode" value={clusterHealth.data?.mode ?? 'unknown'} />
                <Metric label="nodes" value={computeNodes.data?.length ?? 0} />
                <Metric label="scripts" value={scriptAssets.data?.length ?? 0} />
              </div>
              <form
                className="rounded border border-bda-border bg-bda-panel p-3"
                onSubmit={(event) => {
                  event.preventDefault()
                  registerServer.mutate()
                }}
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <strong className="text-xs">Server intake</strong>
                  <button
                    type="submit"
                    className="rounded bg-bda-cyan px-2 py-1 text-xs font-medium text-bda-bg disabled:opacity-50"
                    disabled={registerServer.isPending || !newServer.server_name.trim()}
                  >
                    Add
                  </button>
                </div>
                <div className="grid gap-2">
                  <ModelInput label="Name" value={newServer.server_name} onChange={(value) => setNewServer((current) => ({ ...current, server_name: value }))} required />
                  <ModelInput label="Base URL" value={newServer.base_url} onChange={(value) => setNewServer((current) => ({ ...current, base_url: value }))} placeholder="https://worker.example/api" />
                  <div className="grid gap-2 sm:grid-cols-2">
                    <ModelInput label="Type" value={newServer.server_type} onChange={(value) => setNewServer((current) => ({ ...current, server_type: value }))} />
                    <ModelInput label="Health path" value={newServer.health_check_endpoint} onChange={(value) => setNewServer((current) => ({ ...current, health_check_endpoint: value }))} />
                  </div>
                  <ModelJsonField label="Capabilities" value={newServer.capabilities_json} onChange={(value) => setNewServer((current) => ({ ...current, capabilities_json: value }))} />
                </div>
              </form>
              <div className="space-y-2">
                {(servers.data ?? []).slice(0, 4).map((server) => (
                  <div key={server.server_id} className="flex items-start justify-between gap-2 rounded border border-bda-border bg-bda-panel p-2">
                    <div className="min-w-0">
                      <strong className="block truncate text-xs">{server.server_name}</strong>
                      <p className="mt-1 truncate text-[11px] text-bda-muted">{server.base_url ?? server.server_type ?? 'server'} · {server.network_status}</p>
                    </div>
                    <button
                      type="button"
                      className="rounded border border-bda-border px-2 py-1 text-[11px] text-bda-muted hover:text-bda-text disabled:opacity-50"
                      disabled={testServer.isPending}
                      onClick={() => testServer.mutate(server.server_id)}
                    >
                      Test
                    </button>
                  </div>
                ))}
              </div>
              <div className="space-y-2">
                {(computeNodes.data ?? []).slice(0, 4).map((node) => (
                  <div key={node.compute_node_id} className="flex items-start justify-between gap-2 rounded border border-bda-border bg-bda-panel p-2">
                    <div>
                      <strong className="text-xs">{node.node_name}</strong>
                      <p className="mt-1 text-[11px] text-bda-muted">{node.node_type} · {node.scheduler_type ?? 'scheduler'} · {node.status}</p>
                    </div>
                    <button
                      type="button"
                      className="rounded border border-bda-border px-2 py-1 text-[11px] text-bda-muted hover:text-bda-text disabled:opacity-50"
                      disabled={drainNode.isPending || node.status === 'draining'}
                      onClick={() => drainNode.mutate(node.compute_node_id)}
                    >
                      Drain
                    </button>
                  </div>
                ))}
              </div>
              <p className="text-xs text-bda-muted">
                {clusterHealth.data?.connected
                  ? `Queues: ${(clusterHealth.data.queues ?? []).slice(0, 4).join(', ') || 'not reported'}`
                  : clusterHealth.data?.reason ?? 'Cluster health is not available yet.'}
              </p>
            </div>
          </section>

          <section className="bda-card">
            <div className="bda-card-header">
              <div>
                <p className="text-xs uppercase tracking-wide text-bda-cyan">Sweet protein showcase</p>
                <h2 className="text-sm font-semibold">{sweetProteinActive ? 'Project context detected' : 'Template ready'}</h2>
              </div>
              <FileText className="h-4 w-4 text-bda-cyan" />
            </div>
            <div className="bda-card-body text-sm text-bda-muted">
              <p>
                Monellin and brazzein routes should keep evidence, structures, constraints, scripts, candidates, and experiment package traceable.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link className="rounded border border-bda-border px-2 py-1 text-xs hover:text-bda-text" to={projectPath('/research', projectId)}>Open evidence</Link>
                <Link className="rounded border border-bda-border px-2 py-1 text-xs hover:text-bda-text" to={projectPath('/candidates', projectId)}>Review candidates</Link>
              </div>
            </div>
          </section>
        </aside>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.8fr)]">
        <section className="bda-card">
          <div className="bda-card-header">
            <div>
              <p className="text-xs uppercase tracking-wide text-bda-cyan">Platform templates</p>
              <h2 className="text-sm font-semibold">Reusable BDA apps for new design domains</h2>
            </div>
            <Sparkles className="h-4 w-4 text-bda-cyan" />
          </div>
          <div className="bda-card-body grid gap-3 md:grid-cols-2">
            {PLATFORM_TEMPLATES.map((template) => {
              const plan = templatePlans[template.id]
              const route = plan?.route_options[0]
              return (
                <article key={template.id} className="rounded border border-bda-border bg-bda-bg p-3">
                  <strong className="text-sm">{template.label}</strong>
                  <p className="mt-2 text-xs leading-relaxed text-bda-muted">{template.objective}</p>
                  {route ? (
                    <p className="mt-2 rounded border border-bda-border p-2 text-xs text-bda-muted">
                      Recommended: {route.label} · {route.estimated_steps} modules
                    </p>
                  ) : null}
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="rounded border border-bda-border px-2 py-1 text-xs text-bda-muted hover:text-bda-text disabled:opacity-50"
                      disabled={draftTemplate.isPending}
                      onClick={() => draftTemplate.mutate(template)}
                    >
                      Draft routes
                    </button>
                    <button
                      type="button"
                      className="rounded bg-bda-cyan px-2 py-1 text-xs font-medium text-bda-bg disabled:opacity-50"
                      disabled={!route || applyTemplate.isPending}
                      onClick={() => applyTemplate.mutate(template)}
                    >
                      Create workflow
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        </section>

        <aside className="bda-card">
          <div className="bda-card-header">
            <div>
              <p className="text-xs uppercase tracking-wide text-bda-cyan">Knowledge base</p>
              <h2 className="text-sm font-semibold">Reusable evidence and workflow memory</h2>
            </div>
          </div>
          <div className="bda-card-body">
            <div className="flex gap-2">
              <input
                className="min-w-0 flex-1 rounded border border-bda-border bg-bda-bg px-2 py-1.5 text-xs"
                value={knowledgeQuery}
                onChange={(event) => setKnowledgeQuery(event.target.value)}
              />
              <button
                type="button"
                className="rounded border border-bda-border px-2 py-1.5 text-xs text-bda-muted hover:text-bda-text"
                onClick={() => knowledge.refetch()}
              >
                Search
              </button>
            </div>
            <div className="bda-scroll-area mt-3 max-h-72 space-y-2 pr-1">
              {(knowledge.data?.items ?? []).map((item) => (
                <article key={item.knowledge_entry_id} className="rounded border border-bda-border bg-bda-bg p-2">
                  <strong className="text-xs">{item.title}</strong>
                  <p className="mt-1 text-xs text-bda-muted">{item.summary}</p>
                  <p className="mt-1 text-[10px] uppercase tracking-wide text-bda-muted">{item.category} · {item.confidence}</p>
                </article>
              ))}
              {knowledge.data?.items.length === 0 ? (
                <p className="rounded border border-dashed border-bda-border p-3 text-center text-xs text-bda-muted">No matching knowledge entries.</p>
              ) : null}
            </div>
          </div>
        </aside>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(340px,0.8fr)]">
        <section className="bda-card">
          <div className="bda-card-header">
            <div>
              <p className="text-xs uppercase tracking-wide text-bda-cyan">Platform registry</p>
              <h2 className="text-sm font-semibold">Datasets, presets, templates, and benchmarks</h2>
            </div>
          </div>
          <div className="bda-card-body grid gap-3 md:grid-cols-2">
            <QuickRegistryItem
              label="Dataset"
              value={platformDraft.datasetName}
              count={datasets.data?.total ?? 0}
              placeholder="Round 1 validated structures"
              onChange={(value) => setPlatformDraft((current) => ({ ...current, datasetName: value }))}
              onCreate={() => createPlatformDataset.mutate()}
              disabled={createPlatformDataset.isPending || !platformDraft.datasetName.trim()}
              items={(datasets.data?.items ?? []).slice(0, 3).map((item) => item.name)}
            />
            <QuickRegistryItem
              label="Benchmark"
              value={platformDraft.benchmarkName}
              count={benchmarkRegistry.data?.total ?? 0}
              placeholder="RFdiffusion smoke benchmark"
              onChange={(value) => setPlatformDraft((current) => ({ ...current, benchmarkName: value }))}
              onCreate={() => createPlatformBenchmark.mutate()}
              disabled={createPlatformBenchmark.isPending || !platformDraft.benchmarkName.trim()}
              items={(benchmarkRegistry.data?.items ?? []).slice(0, 3).map((item) => item.name)}
            />
            <QuickRegistryItem
              label="Preset"
              value={platformDraft.presetName}
              count={parameterPresets.data?.total ?? 0}
              placeholder="Conservative GPU defaults"
              onChange={(value) => setPlatformDraft((current) => ({ ...current, presetName: value }))}
              onCreate={() => createPlatformPreset.mutate()}
              disabled={createPlatformPreset.isPending || !platformDraft.presetName.trim()}
              items={(parameterPresets.data?.items ?? []).slice(0, 3).map((item) => item.name)}
            />
            <QuickRegistryItem
              label="Template"
              value={platformDraft.templateName}
              count={workflowTemplates.data?.total ?? 0}
              placeholder="Sweet protein route"
              onChange={(value) => setPlatformDraft((current) => ({ ...current, templateName: value }))}
              onCreate={() => createPlatformTemplate.mutate()}
              disabled={createPlatformTemplate.isPending || !platformDraft.templateName.trim()}
              items={(workflowTemplates.data?.items ?? []).slice(0, 3).map((item) => item.name)}
            />
          </div>
        </section>

        <aside className="bda-card">
          <div className="bda-card-header">
            <div>
              <p className="text-xs uppercase tracking-wide text-bda-cyan">Registry coverage</p>
              <h2 className="text-sm font-semibold">Second-stage completion</h2>
            </div>
          </div>
          <div className="bda-card-body grid grid-cols-2 gap-2">
            <Metric label="datasets" value={datasets.data?.total ?? 0} />
            <Metric label="benchmarks" value={benchmarkRegistry.data?.total ?? 0} />
            <Metric label="presets" value={parameterPresets.data?.total ?? 0} />
            <Metric label="templates" value={workflowTemplates.data?.total ?? 0} />
          </div>
        </aside>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(340px,0.8fr)]">
        <section className="bda-card">
          <div className="bda-card-header">
            <div>
              <p className="text-xs uppercase tracking-wide text-bda-cyan">Job operations</p>
              <h2 className="text-sm font-semibold">{jobs.length} jobs across {workflows.data?.length ?? 0} workflow routes</h2>
            </div>
            <button
              type="button"
              className="rounded border border-bda-border p-1 text-bda-muted hover:text-bda-text"
              onClick={() => void refreshJobQueries()}
              title="Refresh jobs"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
          <div className="bda-card-body">
            <div className="mb-3 grid grid-cols-3 gap-2">
              <Metric label="active" value={activeJobs.length} />
              <Metric label="finished" value={finishedJobs.length} />
              <Metric label="artifacts" value={jobs.reduce((sum, job) => sum + outputArtifactCount(job), 0)} />
            </div>
            <div className="bda-scroll-area max-h-96 space-y-2 pr-1">
              {jobs.length === 0 ? (
                <p className="rounded border border-dashed border-bda-border p-4 text-center text-sm text-bda-muted">
                  No compute jobs yet. Create a workflow route, preview a script, or submit a node to populate this queue.
                </p>
              ) : jobs.map((job) => (
                <article key={job.job_id} className="rounded border border-bda-border bg-bda-bg p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <strong className="block truncate text-sm">{job.job_id}</strong>
                      <p className="mt-1 truncate text-xs text-bda-muted">{job.plugin_id ?? 'unknown plugin'} · {job.node_run_id ?? 'workflow job'}</p>
                    </div>
                    <StatusPill label={job.status} tone={statusTone(job.status)} />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 rounded border border-bda-border px-2 py-1 text-xs text-bda-muted hover:text-bda-text"
                      onClick={() => syncJob.mutate(job)}
                    >
                      <Terminal className="h-3.5 w-3.5" />
                      Sync
                    </button>
                    {['queued', 'running', 'staging'].includes(job.status) ? (
                      <button
                        type="button"
                        className="rounded border border-bda-border px-2 py-1 text-xs text-bda-muted hover:text-bda-text"
                        onClick={() => cancel.mutate(job)}
                      >
                        Cancel
                      </button>
                    ) : null}
                    {job.workflow_run_id ? (
                      <Link className="rounded border border-bda-border px-2 py-1 text-xs text-bda-muted hover:text-bda-text" to={projectPath('/workflow', projectId)}>
                        Open route
                      </Link>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <aside className="grid gap-4">
          <section className="bda-card">
            <div className="bda-card-header">
              <div>
                <p className="text-xs uppercase tracking-wide text-bda-cyan">Campaign loop</p>
                <h2 className="text-sm font-semibold">{campaignItems.length} campaigns</h2>
              </div>
              <Cpu className="h-4 w-4 text-bda-cyan" />
            </div>
            <div className="bda-card-body space-y-2">
              {campaignItems.slice(0, 4).map((campaign) => (
                <Link key={campaign.campaign_id} className="block rounded border border-bda-border bg-bda-bg p-3 text-sm hover:border-bda-cyan/50" to={projectPath('/research', projectId)}>
                  <strong>{campaign.name}</strong>
                  <p className="mt-1 text-xs text-bda-muted">Round {campaign.current_round}/{campaign.max_rounds} · {campaign.status}</p>
                </Link>
              ))}
              {campaignItems.length ? null : (
                <p className="rounded border border-dashed border-bda-border p-3 text-sm text-bda-muted">Create a campaign from Research to turn experiment feedback into next-round constraints.</p>
              )}
            </div>
          </section>

          <section className="bda-card">
            <div className="bda-card-header">
              <div>
                <p className="text-xs uppercase tracking-wide text-bda-cyan">Report builder</p>
                <h2 className="text-sm font-semibold">{deliveryPackage.data ? 'Delivery package ready' : 'Package not generated'}</h2>
              </div>
              <PackageCheck className="h-4 w-4 text-bda-green" />
            </div>
            <div className="bda-card-body text-sm text-bda-muted">
              <p>
                Export includes dossier context, workflow graph, candidate set, experiment templates, recommendations, manifest, and checksums.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <a className="rounded bg-bda-green px-3 py-2 text-xs font-medium text-bda-bg" href={deliveryPackageDownloadUrl(projectId)} target="_blank" rel="noreferrer">
                  Download ZIP
                </a>
                <Link className="rounded border border-bda-border px-3 py-2 text-xs hover:text-bda-text" to={projectPath('/results', projectId)}>
                  Open results
                </Link>
              </div>
            </div>
          </section>
        </aside>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(340px,0.8fr)]">
        <section className="bda-card">
          <div className="bda-card-header">
            <div>
              <p className="text-xs uppercase tracking-wide text-bda-cyan">Benchmark registry</p>
              <h2 className="text-sm font-semibold">Plugin performance from project jobs</h2>
            </div>
          </div>
          <div className="bda-card-body bda-scroll-area max-h-80">
            <table className="w-full text-left text-xs">
              <thead className="text-bda-muted">
                <tr>
                  <th className="py-2 pr-2">Plugin</th>
                  <th className="py-2 pr-2">Runs</th>
                  <th className="py-2 pr-2">Success</th>
                  <th className="py-2 pr-2">Artifacts</th>
                </tr>
              </thead>
              <tbody>
                {benchmarkRows.slice(0, 10).map((row) => (
                  <tr key={row.plugin.model_plugin_id} className="border-t border-bda-border">
                    <td className="py-2 pr-2">{row.plugin.model_name}</td>
                    <td className="py-2 pr-2">{row.runs}</td>
                    <td className="py-2 pr-2">{row.successRate == null ? 'n/a' : `${row.successRate}%`}</td>
                    <td className="py-2 pr-2">{row.artifacts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="bda-card">
          <div className="bda-card-header">
            <div>
              <p className="text-xs uppercase tracking-wide text-bda-cyan">Active-learning queue</p>
              <h2 className="text-sm font-semibold">Next-round selection balance</h2>
            </div>
          </div>
          <div className="bda-card-body grid gap-2">
            {activeLearningSignals.map((signal) => (
              <div key={signal.label} className="rounded border border-bda-border bg-bda-bg p-3">
                <div className="flex items-center justify-between gap-2">
                  <strong className="text-sm">{signal.label}</strong>
                  <span className="text-sm text-bda-cyan">{signal.value}</span>
                </div>
                <p className="mt-1 text-xs text-bda-muted">{signal.note}</p>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </section>
  )
}

function ModelInput({
  label,
  value,
  onChange,
  placeholder,
  required,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  required?: boolean
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[10px] uppercase tracking-wide text-bda-muted">{label}</span>
      <input
        className="w-full rounded border border-bda-border bg-bda-panel px-2 py-1.5 text-xs"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required={required}
      />
    </label>
  )
}

function ModelJsonField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[10px] uppercase tracking-wide text-bda-muted">{label}</span>
      <textarea
        className="min-h-28 w-full rounded border border-bda-border bg-bda-panel px-2 py-1.5 font-mono text-[11px]"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  )
}

function QuickRegistryItem({
  label,
  value,
  count,
  placeholder,
  onChange,
  onCreate,
  disabled,
  items,
}: {
  label: string
  value: string
  count: number
  placeholder: string
  onChange: (value: string) => void
  onCreate: () => void
  disabled: boolean
  items: string[]
}) {
  return (
    <div className="rounded border border-bda-border bg-bda-bg p-3">
      <div className="flex items-center justify-between gap-2">
        <strong className="text-xs">{label}</strong>
        <span className="text-xs text-bda-cyan">{count}</span>
      </div>
      <div className="mt-2 flex gap-2">
        <input
          className="min-w-0 flex-1 rounded border border-bda-border bg-bda-panel px-2 py-1.5 text-xs"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
        />
        <button
          type="button"
          className="rounded bg-bda-cyan px-2 py-1.5 text-xs font-medium text-bda-bg disabled:opacity-50"
          disabled={disabled}
          onClick={onCreate}
        >
          Add
        </button>
      </div>
      <div className="mt-2 space-y-1">
        {items.length ? items.map((item) => (
          <p key={item} className="truncate text-[11px] text-bda-muted">{item}</p>
        )) : (
          <p className="text-[11px] text-bda-muted">No entries yet.</p>
        )}
      </div>
    </div>
  )
}
