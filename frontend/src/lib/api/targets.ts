import { apiRequest } from './client'

export interface PdbUploadResponse {
  file_id: string
  filename: string
  atom_count: number
  chain_count: number
  preview_url: string
}

export function uploadPdb(file: File, projectId?: string) {
  const form = new FormData()
  form.append('file', file)
  if (projectId) form.append('project_id', projectId)
  return apiRequest<PdbUploadResponse>('/targets/upload-pdb', {
    method: 'POST',
    body: form,
  })
}
