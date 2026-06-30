import { z } from 'zod'
import { apiRequest } from './client'

const RegistryListSchema = <T extends z.ZodTypeAny>(item: T) =>
  z.object({ items: z.array(item), total: z.number() })

export const DatasetSchema = z.object({
  dataset_id: z.string(),
  project_id: z.string().nullable().optional(),
  name: z.string(),
  dataset_type: z.string(),
  description: z.string().nullable().optional(),
  artifact_ids_json: z.union([z.string(), z.array(z.string())]).optional(),
  metadata_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  status: z.string(),
})
export type Dataset = z.infer<typeof DatasetSchema>

export const BenchmarkRunSchema = z.object({
  benchmark_run_id: z.string(),
  model_plugin_id: z.string().nullable().optional(),
  dataset_id: z.string().nullable().optional(),
  name: z.string(),
  metrics_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  context_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  status: z.string(),
})
export type BenchmarkRun = z.infer<typeof BenchmarkRunSchema>

export const ParameterPresetSchema = z.object({
  preset_id: z.string(),
  model_plugin_id: z.string().nullable().optional(),
  method_plugin_id: z.string().nullable().optional(),
  name: z.string(),
  description: z.string().nullable().optional(),
  parameters_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  scope: z.string(),
  status: z.string(),
})
export type ParameterPreset = z.infer<typeof ParameterPresetSchema>

export const WorkflowTemplateSchema = z.object({
  workflow_template_id: z.string(),
  name: z.string(),
  template_type: z.string(),
  description: z.string().nullable().optional(),
  nodes_json: z.union([z.string(), z.array(z.record(z.string(), z.unknown()))]).optional(),
  edges_json: z.union([z.string(), z.array(z.record(z.string(), z.unknown()))]).optional(),
  tags_json: z.union([z.string(), z.array(z.string())]).optional(),
  status: z.string(),
})
export type WorkflowTemplate = z.infer<typeof WorkflowTemplateSchema>

export function listDatasets() {
  return apiRequest('/platform-registry/datasets', {}, RegistryListSchema(DatasetSchema))
}

export function createDataset(payload: {
  name: string
  dataset_type?: string
  description?: string | null
  artifact_ids_json?: string[]
  metadata_json?: Record<string, unknown>
  project_id?: string | null
  status?: string
}) {
  return apiRequest('/platform-registry/datasets', { method: 'POST', body: JSON.stringify(payload) }, DatasetSchema)
}

export function listBenchmarkRuns() {
  return apiRequest('/platform-registry/benchmark-runs', {}, RegistryListSchema(BenchmarkRunSchema))
}

export function createBenchmarkRun(payload: {
  name: string
  model_plugin_id?: string | null
  dataset_id?: string | null
  metrics_json?: Record<string, unknown>
  context_json?: Record<string, unknown>
  status?: string
}) {
  return apiRequest('/platform-registry/benchmark-runs', { method: 'POST', body: JSON.stringify(payload) }, BenchmarkRunSchema)
}

export function listParameterPresets() {
  return apiRequest('/platform-registry/parameter-presets', {}, RegistryListSchema(ParameterPresetSchema))
}

export function createParameterPreset(payload: {
  name: string
  parameters_json?: Record<string, unknown>
  model_plugin_id?: string | null
  description?: string | null
  scope?: string
  status?: string
}) {
  return apiRequest('/platform-registry/parameter-presets', { method: 'POST', body: JSON.stringify(payload) }, ParameterPresetSchema)
}

export function listWorkflowTemplates() {
  return apiRequest('/platform-registry/workflow-templates', {}, RegistryListSchema(WorkflowTemplateSchema))
}

export function createWorkflowTemplate(payload: {
  name: string
  template_type?: string
  description?: string | null
  nodes_json?: Record<string, unknown>[]
  edges_json?: Record<string, unknown>[]
  default_parameters_json?: Record<string, unknown>
  tags_json?: string[]
  status?: string
}) {
  return apiRequest('/platform-registry/workflow-templates', { method: 'POST', body: JSON.stringify(payload) }, WorkflowTemplateSchema)
}
