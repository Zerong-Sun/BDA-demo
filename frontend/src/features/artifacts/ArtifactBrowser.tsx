import { Database, Download, FileText } from 'lucide-react'
import clsx from 'clsx'
import type { Artifact } from '../../lib/schemas/artifact'
import { formatBytes } from '../../lib/schemas/artifact'
import { API_BASE } from '../../lib/api/client'

interface ArtifactBrowserProps {
  artifacts: Artifact[]
  selectedArtifactId?: string
  onSelect: (artifact: Artifact) => void
}

function artifactDownloadHref(artifact: Artifact): string | undefined {
  const url = artifact.download_url ?? artifact.preview_url
  if (url) {
    if (url.startsWith('/api/')) return url
    return `${API_BASE}${url.startsWith('/') ? url : `/${url}`}`
  }
  return undefined
}

export function ArtifactBrowser({ artifacts, selectedArtifactId, onSelect }: ArtifactBrowserProps) {
  return (
    <div className="space-y-2">
      {artifacts.length === 0 ? (
        <div className="rounded-md border border-dashed border-bda-border bg-bda-bg px-3 py-5 text-center text-xs text-bda-muted">
          Upload target structures, FASTA files, score tables, or constraints to use them as workflow inputs.
        </div>
      ) : (
        artifacts.map((artifact) => {
          const href = artifactDownloadHref(artifact)
          return (
            <button
              key={artifact.artifact_id}
              type="button"
              className={clsx(
                'w-full rounded-md border p-3 text-left transition-colors',
                selectedArtifactId === artifact.artifact_id
                  ? 'border-bda-cyan bg-bda-cyan/10'
                  : 'border-bda-border bg-bda-bg hover:border-bda-cyan/40',
              )}
              onClick={() => onSelect(artifact)}
            >
              <div className="flex min-w-0 items-start gap-2">
                {artifact.source === 'generated' ? (
                  <Database className="mt-0.5 h-4 w-4 shrink-0 text-bda-green" />
                ) : (
                  <FileText className="mt-0.5 h-4 w-4 shrink-0 text-bda-cyan" />
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex min-w-0 items-center justify-between gap-2">
                    <strong className="truncate text-xs text-bda-text">{artifact.display_name}</strong>
                    <span className="shrink-0 rounded border border-bda-border px-1.5 py-0.5 text-[10px] uppercase text-bda-muted">
                      {artifact.format}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-xs text-bda-muted">
                    {artifact.artifact_type} · {formatBytes(artifact.size_bytes)}
                  </p>
                  {href ? (
                    <a
                      className="mt-2 inline-flex items-center gap-1 text-xs text-bda-cyan hover:underline"
                      href={href}
                      onClick={(event) => event.stopPropagation()}
                    >
                      <Download className="h-3 w-3" />
                      Download / preview
                    </a>
                  ) : null}
                </div>
              </div>
            </button>
          )
        })
      )}
    </div>
  )
}
