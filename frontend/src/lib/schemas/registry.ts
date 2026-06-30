import { z } from 'zod'

export const ModelPluginSchema = z.object({
  model_plugin_id: z.string(),
  model_name: z.string(),
  model_type: z.string(),
  provider: z.string(),
  version: z.string(),
  description: z.string().nullable().optional(),
  input_schema_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  output_schema_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  parameter_schema_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  artifact_schema_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  supported_task_types: z.union([z.string(), z.array(z.string())]).optional(),
  supported_file_types: z.union([z.string(), z.array(z.string())]).optional(),
  resource_requirement_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  default_compute_node_id: z.string().nullable().optional(),
  container_image: z.string().nullable().optional(),
  command_template: z.string().nullable().optional(),
  api_endpoint: z.string().nullable().optional(),
  license: z.string().nullable().optional(),
  citation: z.string().nullable().optional(),
  status: z.string(),
})

export type ModelPlugin = z.infer<typeof ModelPluginSchema>

export const MethodPluginSchema = z.object({
  method_plugin_id: z.string(),
  method_name: z.string(),
  method_type: z.string(),
  description: z.string().nullable().optional(),
  input_schema_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  output_schema_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  parameter_schema_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  compatible_model_types: z.union([z.string(), z.array(z.string())]).optional(),
  compatible_workflow_nodes: z.union([z.string(), z.array(z.string())]).optional(),
  default_parameters_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  version: z.string().optional(),
  status: z.string(),
})

export type MethodPlugin = z.infer<typeof MethodPluginSchema>

export const ComputeNodeSchema = z.object({
  compute_node_id: z.string(),
  server_id: z.string().nullable().optional(),
  node_name: z.string(),
  node_type: z.string(),
  scheduler_type: z.string().optional(),
  queue_name: z.string().nullable().optional(),
  gpu_type: z.string().nullable().optional(),
  gpu_count: z.number().optional(),
  cpu_count: z.number().optional(),
  memory_gb: z.number().optional(),
  current_jobs_json: z.union([z.string(), z.array(z.unknown())]).optional(),
  resource_limits_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  status: z.string(),
})

export type ComputeNode = z.infer<typeof ComputeNodeSchema>

export const ServerConnectionSchema = z.object({
  server_id: z.string(),
  server_name: z.string(),
  server_type: z.string().optional(),
  base_url: z.string().nullable().optional(),
  auth_type: z.string().optional(),
  network_status: z.string(),
  health_check_endpoint: z.string().nullable().optional(),
  capabilities_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  enabled: z.boolean().optional(),
  last_health_check_at: z.string().nullable().optional(),
})

export type ServerConnection = z.infer<typeof ServerConnectionSchema>

export const ScriptAssetSchema = z.object({
  script_asset_id: z.string(),
  source_id: z.string().optional(),
  model_plugin_id: z.string().nullable().optional(),
  relative_path: z.string(),
  language: z.string(),
  scheduler: z.string().nullable().optional(),
  content_hash: z.string(),
  resource_config_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  environment_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
  parse_warnings_json: z.union([z.string(), z.array(z.string())]).optional(),
  status: z.string().optional(),
  updated_at: z.string().optional(),
})

export type ScriptAsset = z.infer<typeof ScriptAssetSchema>

export const ScriptUploadResultSchema = z.object({
  success: z.boolean(),
  item: z.object({
    script_asset_id: z.string(),
    source_id: z.string(),
    relative_path: z.string(),
    model_plugin_id: z.string().nullable().optional(),
    content_hash: z.string(),
    language: z.string(),
    scheduler: z.string().nullable().optional(),
    parameter_observations: z.number(),
    parse_warnings: z.number(),
    warnings: z.array(z.string()),
  }),
})

export type ScriptUploadResult = z.infer<typeof ScriptUploadResultSchema>
