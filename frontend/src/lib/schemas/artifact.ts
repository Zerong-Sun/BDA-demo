import { z } from 'zod'

export const ArtifactSchema = z.object({
  artifact_id: z.string(),
  project_id: z.string().nullable().optional(),
  workflow_run_id: z.string().nullable().optional(),
  node_run_id: z.string().nullable().optional(),
  artifact_type: z.string(),
  format: z.string(),
  display_name: z.string(),
  size_bytes: z.number().optional(),
  storage_uri: z.string().optional(),
  checksum: z.string().nullable().optional(),
  source: z.enum(['uploaded', 'generated', 'demo']).optional(),
  preview_url: z.string().optional(),
  download_url: z.string().optional(),
  metadata_json: z.record(z.string(), z.unknown()).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  created_by: z.string().nullable().optional(),
  created_at: z.string().optional(),
}).transform((artifact) => ({
  ...artifact,
  source: artifact.source ?? (artifact.node_run_id ? 'generated' : 'uploaded'),
  metadata: artifact.metadata ?? artifact.metadata_json ?? {},
}))

export type Artifact = z.infer<typeof ArtifactSchema>

export function formatBytes(bytes?: number): string {
  if (!bytes || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / 1024 ** index
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`
}
