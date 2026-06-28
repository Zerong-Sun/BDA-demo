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
