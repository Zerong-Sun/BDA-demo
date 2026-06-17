import { apiRequest } from './client'
import { fetchPaginatedList } from './pagination'
import {
  ComputeNodeSchema,
  MethodPluginSchema,
  ModelPluginSchema,
  ServerConnectionSchema,
  type ComputeNode,
  type MethodPlugin,
  type ModelPlugin,
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
