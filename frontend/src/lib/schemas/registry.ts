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
  resource_requirement_json: z.union([z.string(), z.record(z.string(), z.unknown())]).optional(),
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
  node_name: z.string(),
  node_type: z.string(),
  gpu_type: z.string().nullable().optional(),
  gpu_count: z.number().optional(),
  status: z.string(),
})

export type ComputeNode = z.infer<typeof ComputeNodeSchema>

export const ServerConnectionSchema = z.object({
  server_id: z.string(),
  server_name: z.string(),
  network_status: z.string(),
})

export type ServerConnection = z.infer<typeof ServerConnectionSchema>
