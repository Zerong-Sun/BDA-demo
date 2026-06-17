import { useCallback, useId, useRef, useState } from 'react'
import { FileUp, Loader2 } from 'lucide-react'
import { uploadArtifact } from '../../lib/api/artifacts'
import type { Artifact } from '../../lib/schemas/artifact'
import { useToastStore } from '../../components/ui/toastStore'

const ACCEPTED = '.pdb,.cif,.mmcif,.fasta,.fa,.faa,.csv,.tsv,.json,.zip'

interface ArtifactUploadDropzoneProps {
  projectId?: string
  onUploaded: (artifact: Artifact, file: File) => void
}

export function ArtifactUploadDropzone({ projectId, onUploaded }: ArtifactUploadDropzoneProps) {
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const showToast = useToastStore((s) => s.show)

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      const file = files?.[0]
      if (!file) return
      setUploading(true)
      try {
        const artifact = await uploadArtifact(file, projectId)
        onUploaded(artifact, file)
        showToast(`Uploaded: ${artifact.display_name}`, 'success')
      } catch (error) {
        showToast(error instanceof Error ? error.message : 'Upload failed', 'error')
      } finally {
        setUploading(false)
        if (inputRef.current) inputRef.current.value = ''
      }
    },
    [onUploaded, projectId, showToast],
  )

  return (
    <label
      htmlFor={inputId}
      className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed px-3 py-6 text-center transition-colors ${
        dragging ? 'border-bda-cyan bg-bda-cyan/5' : 'border-bda-border bg-bda-bg hover:border-bda-cyan/50'
      }`}
      onDragOver={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        void handleFiles(event.dataTransfer.files)
      }}
    >
      {uploading ? (
        <Loader2 className="h-5 w-5 animate-spin text-bda-cyan" />
      ) : (
        <FileUp className="h-5 w-5 text-bda-cyan" />
      )}
      <span className="text-sm text-bda-text">{uploading ? 'Uploading...' : 'Upload artifact'}</span>
      <span className="text-xs leading-relaxed text-bda-muted">PDB, mmCIF, FASTA, CSV, JSON, ZIP</span>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept={ACCEPTED}
        className="hidden"
        onChange={(event) => void handleFiles(event.target.files)}
      />
    </label>
  )
}
