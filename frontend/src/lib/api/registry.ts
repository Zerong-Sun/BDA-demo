import { apiRequest } from './client'
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
import { z } from 'zod'

const paginated = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.object({
    items: z.array(itemSchema),
    total: z.number(),
    limit: z.number(),
    offset: z.number(),
  })

export function listModelPlugins(): Promise<ModelPlugin[]> {
  return apiRequest('/model-plugins', {}, paginated(ModelPluginSchema)).then((page) => page.items)
}

export function listMethodPlugins(): Promise<MethodPlugin[]> {
  return apiRequest('/method-plugins', {}, paginated(MethodPluginSchema)).then((page) => page.items)
}

export function listComputeNodes(): Promise<ComputeNode[]> {
  return apiRequest('/compute-nodes', {}, paginated(ComputeNodeSchema)).then((page) => page.items)
}

export function listServers(): Promise<ServerConnection[]> {
  return apiRequest('/servers', {}, paginated(ServerConnectionSchema)).then((page) => page.items)
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
