import { useState } from 'react'
import { Upload } from 'lucide-react'
import { uploadExperimentResults } from '../../lib/api/experiments'
import { useToastStore } from '../../components/ui/Toast'

interface ExperimentUploadProps {
  projectId: string
  onUploaded?: () => void
}

export function ExperimentUpload({ projectId, onUploaded }: ExperimentUploadProps) {
  const [uploading, setUploading] = useState(false)
  const showToast = useToastStore((s) => s.show)

  const handleFile = async (file: File | undefined) => {
    if (!file) return
    setUploading(true)
    try {
      const result = await uploadExperimentResults(file, projectId)
      showToast(`Imported ${result.imported} experiment results`, 'success')
      onUploaded?.()
    } catch {
      showToast('Failed to upload experiment data', 'error')
    } finally {
      setUploading(false)
    }
  }

  return (
    <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-bda-border bg-bda-panel px-4 py-3 hover:border-bda-cyan/50">
      <Upload className="h-5 w-5 text-bda-cyan" />
      <div>
        <p className="text-sm text-bda-text">
          {uploading ? 'Uploading experiment data...' : 'Upload experiment CSV / JSON'}
        </p>
        <p className="text-xs text-bda-muted">Bind BLI, SEC, expression readouts to candidate IDs</p>
      </div>
      <input
        type="file"
        accept=".csv,.json"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
    </label>
  )
}
