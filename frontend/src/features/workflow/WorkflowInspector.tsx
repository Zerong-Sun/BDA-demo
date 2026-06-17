import type { ReactNode } from 'react'
import { Download, Info, Network, Settings2 } from 'lucide-react'
import type { WorkflowNode } from '../../lib/schemas/workflow'
import type { Artifact } from '../../lib/schemas/artifact'
import { formatBytes } from '../../lib/schemas/artifact'
import { API_BASE } from '../../lib/api/client'
import { StatusPill } from '../../components/ui/StatusPill'
import { statusTone } from '../../components/ui/statusTone'
import { JobStatusDrawer } from '../jobs'

interface WorkflowInspectorProps {
  workflowRunId?: string
  selectedNode?: WorkflowNode | null
  selectedArtifact?: Artifact | null
}

function parseJsonObject(value: unknown): Record<string, unknown> {
  if (!value) return {}
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : {}
    } catch {
      return {}
    }
  }
  return typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function previewHref(artifact: Artifact): string | undefined {
  const url = artifact.download_url ?? artifact.preview_url
  if (!url) return undefined
  if (url.startsWith('/api/')) return url
  return `${API_BASE}${url.startsWith('/') ? url : `/${url}`}`
}

export function WorkflowInspector({ workflowRunId, selectedNode, selectedArtifact }: WorkflowInspectorProps) {
  const parameters = parseJsonObject(selectedNode?.parameters_json)
  const metrics = parseJsonObject(selectedNode?.metrics_json)
  const href = selectedArtifact ? previewHref(selectedArtifact) : undefined

  return (
    <aside className="space-y-4">
      <section className="rounded-lg border border-bda-border bg-bda-panel p-3">
        <div className="mb-3 flex items-center gap-2">
          <Info className="h-4 w-4 text-bda-cyan" />
          <div>
            <p className="text-xs uppercase tracking-wide text-bda-cyan">Inspector</p>
            <h2 className="text-sm font-semibold">
              {selectedNode ? 'Node details' : selectedArtifact ? 'Artifact details' : 'Workflow summary'}
            </h2>
          </div>
        </div>

        {selectedNode ? (
          <div className="space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate text-sm font-semibold">{selectedNode.node_name}</h3>
                <p className="mt-1 text-xs text-bda-muted">
                  {selectedNode.model_name ?? selectedNode.node_type}
                  {selectedNode.model_version ? ` · v${selectedNode.model_version}` : ''}
                </p>
              </div>
              <StatusPill label={selectedNode.status} tone={statusTone(selectedNode.status)} />
            </div>

            <InspectorBlock icon={<Settings2 className="h-3.5 w-3.5" />} title="Parameters">
              <KeyValueGrid data={parameters} empty="No parameters saved yet." />
            </InspectorBlock>

            <InspectorBlock icon={<Network className="h-3.5 w-3.5" />} title="Metrics">
              <KeyValueGrid data={metrics} empty="No metrics reported yet." />
            </InspectorBlock>

            {selectedNode.logs ? (
              <pre className="max-h-32 overflow-auto rounded-md border border-bda-border bg-bda-bg p-2 text-xs text-bda-muted">
                {selectedNode.logs}
              </pre>
            ) : null}
          </div>
        ) : selectedArtifact ? (
          <div className="space-y-3">
            <div>
              <h3 className="break-words text-sm font-semibold">{selectedArtifact.display_name}</h3>
              <p className="mt-1 text-xs text-bda-muted">
                {selectedArtifact.artifact_type} · {selectedArtifact.format} · {formatBytes(selectedArtifact.size_bytes)}
              </p>
            </div>
            <KeyValueGrid data={selectedArtifact.metadata} empty="No metadata parsed yet." />
            {href ? (
              <a
                href={href}
                className="inline-flex items-center gap-2 rounded-md border border-bda-border px-3 py-2 text-sm text-bda-text hover:border-bda-cyan/50"
              >
                <Download className="h-4 w-4" />
                Open artifact
              </a>
            ) : (
              <p className="rounded border border-dashed border-bda-border p-3 text-xs text-bda-muted">
                No download URL is available for this artifact yet.
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-2 text-xs leading-relaxed text-bda-muted">
            <p>Select a node to edit parameters, inspect logs, and review outputs.</p>
            <p>Select an artifact to preview metadata or download the source file.</p>
          </div>
        )}
      </section>

      <JobStatusDrawer workflowRunId={workflowRunId} selectedNodeId={selectedNode?.node_run_id ?? null} />
    </aside>
  )
}

function InspectorBlock({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <div>
      <h4 className="mb-2 flex items-center gap-1.5 text-xs font-medium text-bda-muted">
        {icon}
        {title}
      </h4>
      {children}
    </div>
  )
}

function KeyValueGrid({ data, empty }: { data: Record<string, unknown>; empty: string }) {
  const entries = Object.entries(data).filter(([, value]) => value !== undefined && value !== null && value !== '')
  if (entries.length === 0) {
    return <p className="rounded border border-dashed border-bda-border p-3 text-xs text-bda-muted">{empty}</p>
  }
  return (
    <dl className="grid gap-2">
      {entries.map(([key, value]) => (
        <div key={key} className="rounded-md border border-bda-border bg-bda-bg p-2">
          <dt className="text-[10px] uppercase tracking-wide text-bda-muted">{key}</dt>
          <dd className="mt-1 break-words text-xs text-bda-text">
            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
          </dd>
        </div>
      ))}
    </dl>
  )
}
