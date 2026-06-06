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

export function listModelPlugins() {
  return apiRequest<ModelPlugin[]>('/model-plugins', {}, z.array(ModelPluginSchema))
}

export function listMethodPlugins() {
  return apiRequest<MethodPlugin[]>('/method-plugins', {}, z.array(MethodPluginSchema))
}

export function listComputeNodes() {
  return apiRequest<ComputeNode[]>('/compute-nodes', {}, z.array(ComputeNodeSchema))
}

export function listServers() {
  return apiRequest<ServerConnection[]>('/servers', {}, z.array(ServerConnectionSchema))
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
