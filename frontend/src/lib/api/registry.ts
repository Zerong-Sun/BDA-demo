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
