import { apiRequest } from './client'
import { fetchPaginatedList } from './pagination'
import {
  ComputeNodeSchema,
  MethodPluginSchema,
  ModelPluginSchema,
  ScriptAssetSchema,
  ScriptUploadResultSchema,
  ServerConnectionSchema,
  type ComputeNode,
  type MethodPlugin,
  type ModelPlugin,
  type ScriptAsset,
  type ScriptUploadResult,
  type ServerConnection,
} from '../schemas/registry'

export function listModelPlugins(): Promise<ModelPlugin[]> {
  return fetchPaginatedList('/model-plugins', ModelPluginSchema)
}

export interface CreateModelPluginPayload {
  model_name: string
  model_type: string
  provider?: string
  version?: string
  description?: string | null
  input_schema_json?: Record<string, unknown>
  output_schema_json?: Record<string, unknown>
  parameter_schema_json?: Record<string, unknown>
  artifact_schema_json?: Record<string, unknown>
  supported_task_types?: string[]
  supported_file_types?: string[]
  resource_requirement_json?: Record<string, unknown>
  default_compute_node_id?: string | null
  container_image?: string | null
  command_template?: string | null
  api_endpoint?: string | null
  license?: string | null
  citation?: string | null
  status?: 'active' | 'experimental' | 'disabled' | 'restricted'
}

export function createModelPlugin(payload: CreateModelPluginPayload): Promise<ModelPlugin> {
  return apiRequest<ModelPlugin>(
    '/model-plugins',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    ModelPluginSchema,
  )
}

export function listMethodPlugins(): Promise<MethodPlugin[]> {
  return fetchPaginatedList('/method-plugins', MethodPluginSchema)
}

export interface CreateMethodPluginPayload {
  method_name: string
  method_type?: string
  description?: string | null
  input_schema_json?: Record<string, unknown>
  output_schema_json?: Record<string, unknown>
  parameter_schema_json?: Record<string, unknown>
  compatible_model_types?: string[]
  compatible_workflow_nodes?: string[]
  default_parameters_json?: Record<string, unknown>
  version?: string
  status?: 'active' | 'experimental' | 'disabled'
}

export function createMethodPlugin(payload: CreateMethodPluginPayload): Promise<MethodPlugin> {
  return apiRequest<MethodPlugin>(
    '/method-plugins',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    MethodPluginSchema,
  )
}

export function listComputeNodes(): Promise<ComputeNode[]> {
  return fetchPaginatedList('/compute-nodes', ComputeNodeSchema)
}

export interface ComputeNodeQueue {
  compute_node: ComputeNode
  jobs: Array<Record<string, unknown>>
  active_jobs: Array<Record<string, unknown>>
  accepting_jobs: boolean
}

export function getComputeNodeQueue(computeNodeId: string): Promise<ComputeNodeQueue> {
  return apiRequest<ComputeNodeQueue>(`/compute-nodes/${computeNodeId}/queue`)
}

export function drainComputeNode(computeNodeId: string) {
  return apiRequest<{ compute_node: ComputeNode; accepting_jobs: boolean; message: string }>(
    `/compute-nodes/${computeNodeId}/drain`,
    { method: 'POST' },
  )
}

export interface ClusterHealth {
  mode: string
  connected: boolean
  host?: string
  remote_root?: string
  queues: string[]
  all_queues?: string[]
  reason?: string | null
}

export function getClusterHealth(): Promise<ClusterHealth> {
  return apiRequest<ClusterHealth>('/compute/cluster-health')
}

export function listServers(): Promise<ServerConnection[]> {
  return fetchPaginatedList('/servers', ServerConnectionSchema)
}

export interface CreateServerPayload {
  server_name: string
  server_type?: string
  base_url?: string | null
  auth_type?: 'none' | 'token' | 'basic' | 'ssh_key' | 'managed_secret'
  credential_ref?: string | null
  health_check_endpoint?: string | null
  capabilities_json?: Record<string, unknown>
  enabled?: boolean
}

export function createServer(payload: CreateServerPayload): Promise<ServerConnection> {
  return apiRequest<ServerConnection>(
    '/servers',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    ServerConnectionSchema,
  )
}

export function updateServer(serverId: string, payload: Partial<CreateServerPayload>): Promise<ServerConnection> {
  return apiRequest<ServerConnection>(
    `/servers/${serverId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
    ServerConnectionSchema,
  )
}

export function testServerConnection(serverId: string) {
  return apiRequest<{ server: ServerConnection; connected: boolean; status: string; reason?: string; url?: string }>(
    `/servers/${serverId}/test-connection`,
    { method: 'POST' },
  )
}

export function checkComputeNodeHealth(computeNodeId: string) {
  return apiRequest<{ compute_node_id: string; status: string; accepting_jobs: boolean }>(
    `/compute-nodes/${computeNodeId}/health-check`,
    { method: 'POST' },
  )
}

export function validateModelPlugin(modelPluginId: string) {
  return apiRequest<{ model_plugin_id: string; valid: boolean; status: string }>(
    `/model-plugins/${modelPluginId}/validate-schema`,
    { method: 'POST' },
  )
}

export function listScriptAssets(modelPluginId?: string): Promise<ScriptAsset[]> {
  const query = modelPluginId ? `?model_plugin_id=${encodeURIComponent(modelPluginId)}` : ''
  return apiRequest<{ items: ScriptAsset[] }>(
    `/script-assets${query}`,
    {},
    undefined,
  ).then((response) => response.items.map((item) => ScriptAssetSchema.parse(item)))
}

export function uploadScriptAsset(
  file: File,
  options: { modelPluginId?: string; relativePath?: string } = {},
): Promise<ScriptUploadResult> {
  const form = new FormData()
  form.append('file', file)
  if (options.modelPluginId) form.append('model_plugin_id', options.modelPluginId)
  if (options.relativePath) form.append('relative_path', options.relativePath)
  return apiRequest<ScriptUploadResult>(
    '/script-assets/upload',
    { method: 'POST', body: form },
    ScriptUploadResultSchema,
  )
}
