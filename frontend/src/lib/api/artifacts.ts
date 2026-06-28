import { API_BASE, apiRequest } from './client'
import { ArtifactSchema, type Artifact } from '../schemas/artifact'

function inferFormat(filename: string): string {
  const suffix = filename.toLowerCase().split('.').pop()
  if (suffix === 'cif') return 'mmcif'
  return suffix || 'file'
}

function inferArtifactType(format: string): string {
  if (['pdb', 'mmcif', 'cif'].includes(format)) return 'structure'
  if (['fasta', 'fa', 'faa'].includes(format)) return 'sequence'
  if (['csv', 'tsv', 'xlsx'].includes(format)) return 'score_table'
  if (format === 'json') return 'constraints'
  if (format === 'zip') return 'bundle'
  return 'file'
}

export async function uploadArtifact(file: File, projectId?: string): Promise<Artifact> {
  const format = inferFormat(file.name)
  const artifactType = inferArtifactType(format)
  const form = new FormData()
  form.append('file', file)
  form.append('artifact_type', artifactType === 'structure' ? 'target_structure' : artifactType)
  if (projectId) form.append('project_id', projectId)

  if (artifactType === 'structure') {
    const uploaded = await apiRequest<{
      file_id: string
      filename: string
      atom_count: number
      chain_count: number
      chains?: string[]
      residue_count?: number
      preview_url: string
      artifact?: unknown
    }>('/targets/upload-pdb', { method: 'POST', body: form })

    if (uploaded.artifact) {
      return ArtifactSchema.parse(uploaded.artifact)
    }

    return ArtifactSchema.parse({
      artifact_id: uploaded.file_id,
      project_id: projectId,
      artifact_type: 'target_structure',
      format,
      display_name: uploaded.filename,
      size_bytes: file.size,
      source: 'uploaded',
      preview_url: uploaded.preview_url,
      metadata: {
        atom_count: uploaded.atom_count,
        chain_count: uploaded.chain_count,
        chains: uploaded.chains ?? [],
        residue_count: uploaded.residue_count,
      },
      created_at: new Date().toISOString(),
    })
  }

  return apiRequest<Artifact>('/artifacts/upload', { method: 'POST', body: form }, ArtifactSchema)
}

export function listProjectArtifacts(projectId: string): Promise<Artifact[]> {
  const limit = 200
  const loadPage = async (offset: number, collected: Artifact[]): Promise<Artifact[]> => {
    const payload = await apiRequest<{ items: Artifact[]; total: number; limit: number; offset: number }>(
      `/projects/${projectId}/artifacts?limit=${limit}&offset=${offset}`,
    )
    const items = payload.items.map((item) => ArtifactSchema.parse(item))
    const next = [...collected, ...items]
    return next.length >= payload.total || items.length === 0 ? next : loadPage(offset + items.length, next)
  }
  return loadPage(0, [])
}

export async function downloadArtifact(artifact: Artifact): Promise<void> {
  const url = artifact.download_url ?? artifact.preview_url
  if (!url) throw new Error('No download URL is available for this artifact.')
  const token = sessionStorage.getItem('bda_token')
  const baseOrigin = API_BASE.startsWith('http') ? new URL(API_BASE).origin : ''
  const downloadUrl = url.startsWith('/api/')
    ? `${baseOrigin}${url}`
    : `${API_BASE}${url.startsWith('/') ? url : `/${url}`}`
  const response = await fetch(downloadUrl, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    throw new Error(`Artifact download failed (${response.status})`)
  }
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = artifact.display_name || artifact.artifact_id
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}
