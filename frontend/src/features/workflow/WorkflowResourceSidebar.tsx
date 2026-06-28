import { useQuery } from '@tanstack/react-query'
import { Cpu, Layers3, Plus } from 'lucide-react'
import { ArtifactBrowser, ArtifactUploadDropzone } from '../artifacts'
import { listModelPlugins } from '../../lib/api/registry'
import type { Artifact } from '../../lib/schemas/artifact'
import type { ModelPlugin } from '../../lib/schemas/registry'
import { StatusPill } from '../../components/ui/StatusPill'
import { statusTone } from '../../components/ui/statusTone'
import { ScriptAssetManager } from './ScriptAssetManager'
import type { WorkflowNode } from '../../lib/schemas/workflow'

interface WorkflowResourceSidebarProps {
  projectId?: string
  artifacts: Artifact[]
  selectedNode?: WorkflowNode | null
  selectedArtifactId?: string
  onArtifactUploaded: (artifact: Artifact, file: File) => void
  onArtifactSelected: (artifact: Artifact) => void
  onPluginAdd?: (plugin: ModelPlugin) => void
  readOnly?: boolean
}

export function WorkflowResourceSidebar({
  projectId,
  artifacts,
  selectedNode,
  selectedArtifactId,
  onArtifactUploaded,
  onArtifactSelected,
  onPluginAdd,
  readOnly = false,
}: WorkflowResourceSidebarProps) {
  const { data: plugins = [] } = useQuery({
    queryKey: ['model-plugins'],
    queryFn: listModelPlugins,
  })
  const nodeArtifacts = selectedNode
    ? artifacts.filter((artifact) => artifact.node_run_id === selectedNode.node_run_id)
    : artifacts
  const visibleArtifacts = selectedNode ? nodeArtifacts : artifacts

  return (
    <aside className="space-y-4">
      <section className="rounded-lg border border-bda-border bg-bda-panel p-3">
        <div className="mb-3 flex items-center gap-2">
          <Layers3 className="h-4 w-4 text-bda-cyan" />
          <div>
            <p className="text-xs uppercase tracking-wide text-bda-cyan">Artifacts</p>
            <h2 className="text-sm font-semibold">
              {selectedNode ? 'Selected node outputs' : 'Inputs and outputs'}
            </h2>
          </div>
        </div>
        {selectedNode ? (
          <div className="mb-3 rounded-md border border-bda-border bg-bda-bg px-3 py-2">
            <p className="truncate text-xs font-medium text-bda-text">{selectedNode.node_name}</p>
            <p className="mt-1 text-[11px] text-bda-muted">
              {visibleArtifacts.length} linked artifact{visibleArtifacts.length === 1 ? '' : 's'}
            </p>
          </div>
        ) : null}
        <ArtifactUploadDropzone projectId={projectId} onUploaded={onArtifactUploaded} />
        <div className="mt-3">
          <ArtifactBrowser artifacts={visibleArtifacts} selectedArtifactId={selectedArtifactId} onSelect={onArtifactSelected} />
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
                {onPluginAdd ? (
                  <button
                    type="button"
                    className="mt-2 inline-flex w-full items-center justify-center gap-1.5 rounded border border-bda-border px-2 py-1.5 text-xs text-bda-text hover:border-bda-cyan/50 disabled:opacity-50"
                    disabled={readOnly || plugin.status !== 'active'}
                    onClick={() => onPluginAdd(plugin)}
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Add to workflow graph
                  </button>
                ) : null}
              </article>
            ))
          )}
        </div>
      </section>

      <ScriptAssetManager />
    </aside>
  )
}
