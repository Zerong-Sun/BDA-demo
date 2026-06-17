import { useQuery } from '@tanstack/react-query'
import { Cpu, Layers3 } from 'lucide-react'
import { ArtifactBrowser, ArtifactUploadDropzone } from '../artifacts'
import { listModelPlugins } from '../../lib/api/registry'
import type { Artifact } from '../../lib/schemas/artifact'
import { StatusPill } from '../../components/ui/StatusPill'
import { statusTone } from '../../components/ui/statusTone'

interface WorkflowResourceSidebarProps {
  projectId?: string
  artifacts: Artifact[]
  selectedArtifactId?: string
  onArtifactUploaded: (artifact: Artifact, file: File) => void
  onArtifactSelected: (artifact: Artifact) => void
}

export function WorkflowResourceSidebar({
  projectId,
  artifacts,
  selectedArtifactId,
  onArtifactUploaded,
  onArtifactSelected,
}: WorkflowResourceSidebarProps) {
  const { data: plugins = [] } = useQuery({
    queryKey: ['model-plugins'],
    queryFn: listModelPlugins,
  })

  return (
    <aside className="space-y-4">
      <section className="rounded-lg border border-bda-border bg-bda-panel p-3">
        <div className="mb-3 flex items-center gap-2">
          <Layers3 className="h-4 w-4 text-bda-cyan" />
          <div>
            <p className="text-xs uppercase tracking-wide text-bda-cyan">Artifacts</p>
            <h2 className="text-sm font-semibold">Inputs and outputs</h2>
          </div>
        </div>
        <ArtifactUploadDropzone projectId={projectId} onUploaded={onArtifactUploaded} />
        <div className="mt-3">
          <ArtifactBrowser artifacts={artifacts} selectedArtifactId={selectedArtifactId} onSelect={onArtifactSelected} />
        </div>
      </section>

      <section className="rounded-lg border border-bda-border bg-bda-panel p-3">
        <div className="mb-3 flex items-center gap-2">
          <Cpu className="h-4 w-4 text-bda-cyan" />
          <div>
            <p className="text-xs uppercase tracking-wide text-bda-cyan">Plugins</p>
            <h2 className="text-sm font-semibold">Model catalog</h2>
          </div>
        </div>
        <div className="space-y-2">
          {plugins.length === 0 ? (
            <p className="rounded border border-dashed border-bda-border px-3 py-4 text-center text-xs text-bda-muted">
              Loading or no plugins registered.
            </p>
          ) : (
            plugins.map((plugin) => (
              <article key={plugin.model_plugin_id} className="rounded-md border border-bda-border bg-bda-bg p-2">
                <div className="flex items-center justify-between gap-2">
                  <strong className="truncate text-xs">{plugin.model_name}</strong>
                  <StatusPill label={plugin.status} tone={statusTone(plugin.status)} />
                </div>
                <p className="mt-1 truncate text-xs text-bda-muted">
                  v{plugin.version} · {plugin.model_type}
                </p>
              </article>
            ))
          )}
        </div>
      </section>
    </aside>
  )
}
