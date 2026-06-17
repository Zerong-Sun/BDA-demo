import { useCallback, useId, useRef, useState } from 'react'
import { FileText, Upload } from 'lucide-react'
import { uploadPdb } from '../../lib/api/targets'
import { useToastStore } from '../../components/ui/toastStore'
import { useI18n } from '../../lib/i18n'

interface PDBFileUploadProps {
  projectId?: string
  selectedFile?: File | null
  onFileSelected: (file: File) => void
  onUploaded?: (previewUrl: string) => void
}

export function PDBFileUpload({
  projectId,
  selectedFile = null,
  onFileSelected,
  onUploaded,
}: PDBFileUploadProps) {
  const { t } = useI18n()
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const showToast = useToastStore((s) => s.show)

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      const file = files?.[0]
      if (!file) return
      const lower = file.name.toLowerCase()
      if (!lower.endsWith('.pdb') && !lower.endsWith('.cif') && !lower.endsWith('.mmcif')) {
        showToast(t.pdbUpload.invalidFile, 'error')
        return
      }
      onFileSelected(file)
      setUploading(true)
      try {
        const result = await uploadPdb(file, projectId)
        onUploaded?.(result.preview_url)
        showToast(
          t.pdbUpload.uploadSuccess
            .replace('{filename}', result.filename)
            .replace('{atomCount}', String(result.atom_count)),
          'success',
        )
      } catch {
        showToast(t.pdbUpload.uploadFallback, 'info')
      } finally {
        setUploading(false)
        if (inputRef.current) inputRef.current.value = ''
      }
    },
    [onFileSelected, onUploaded, projectId, showToast, t],
  )

  if (selectedFile) {
    return (
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-md border border-bda-border bg-bda-panel px-3 py-1.5 text-sm text-bda-text transition-colors hover:border-bda-cyan/50 hover:bg-bda-panel-hover disabled:opacity-50"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          title={t.pdbUpload.replaceHint}
        >
          <FileText className="h-4 w-4 shrink-0 text-bda-cyan" />
          <span className="max-w-[240px] truncate">{selectedFile.name}</span>
          <span className="text-xs text-bda-muted">
            {uploading ? t.pdbUpload.uploading : t.pdbUpload.replace}
          </span>
        </button>
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept=".pdb,.cif,.mmcif"
          className="hidden"
          onChange={(e) => void handleFiles(e.target.files)}
        />
      </div>
    )
  }

  return (
    <label
      htmlFor={inputId}
      className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-4 py-10 text-center transition-colors ${
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
        void handleFiles(e.dataTransfer.files)
      }}
    >
      <Upload className="h-6 w-6 text-bda-cyan" />
      <span className="text-sm text-bda-text">
        {uploading ? t.pdbUpload.uploading : t.pdbUpload.dropzone}
      </span>
      <span className="text-xs text-bda-muted">{t.pdbUpload.hint}</span>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept=".pdb,.cif,.mmcif"
        className="hidden"
        onChange={(e) => void handleFiles(e.target.files)}
      />
    </label>
  )
}
