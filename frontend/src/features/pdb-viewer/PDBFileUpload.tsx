import { useCallback, useState } from 'react'
import { Upload } from 'lucide-react'
import { uploadPdb } from '../../lib/api/targets'
import { useToastStore } from '../../components/ui/toastStore'

interface PDBFileUploadProps {
  projectId?: string
  onFileSelected: (file: File) => void
  onUploaded?: (previewUrl: string) => void
}

export function PDBFileUpload({ projectId, onFileSelected, onUploaded }: PDBFileUploadProps) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const showToast = useToastStore((s) => s.show)

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      const file = files?.[0]
      if (!file) return
      const lower = file.name.toLowerCase()
      if (!lower.endsWith('.pdb') && !lower.endsWith('.cif') && !lower.endsWith('.mmcif')) {
        showToast('Please upload a PDB or mmCIF file', 'error')
        return
      }
      onFileSelected(file)
      setUploading(true)
      try {
        const result = await uploadPdb(file, projectId)
        onUploaded?.(result.preview_url)
        showToast(`Loaded ${result.filename} (${result.atom_count} atoms)`, 'success')
      } catch {
        showToast('Uploaded locally; backend preview unavailable in demo mode', 'info')
      } finally {
        setUploading(false)
      }
    },
    [onFileSelected, onUploaded, projectId, showToast],
  )

  return (
    <label
      className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-4 py-6 text-center transition-colors ${
        dragging ? 'border-bda-cyan bg-bda-cyan/5' : 'border-bda-border bg-bda-panel hover:border-bda-cyan/50'
      }`}
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        handleFiles(e.dataTransfer.files)
      }}
    >
      <Upload className="h-5 w-5 text-bda-cyan" />
      <span className="text-sm text-bda-text">
        {uploading ? 'Uploading...' : 'Drop PDB / mmCIF here or click to browse'}
      </span>
      <span className="text-xs text-bda-muted">Structures render immediately in the 3D viewer</span>
      <input
        type="file"
        accept=".pdb,.cif,.mmcif"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </label>
  )
}
