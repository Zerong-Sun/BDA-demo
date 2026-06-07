import { Handle, Position, type NodeProps } from '@xyflow/react'
import {
  Activity,
  Database,
  Dna,
  FileJson,
  Filter,
  FlaskConical,
  ScanSearch,
  WandSparkles,
} from 'lucide-react'
import clsx from 'clsx'
import type { WorkflowNodeData } from './workflowTypes'

const iconMap = {
  database: Database,
  'file-json': FileJson,
  'wand-sparkles': WandSparkles,
  dna: Dna,
  'scan-search': ScanSearch,
  activity: Activity,
  filter: Filter,
  'flask-conical': FlaskConical,
}

const statusStyles: Record<string, string> = {
  not_started: 'border-bda-border',
  queued: 'border-bda-amber/50',
  running: 'border-bda-blue shadow-[0_0_0_1px_rgba(53,162,255,0.35)]',
  completed: 'border-bda-green/50',
  failed: 'border-bda-red/50',
  requires_review: 'border-bda-amber/50',
  demo: 'border-bda-border',
  skipped: 'border-bda-border opacity-70',
}

export function WorkflowNodeCard({ data, selected }: NodeProps) {
  const nodeData = data as WorkflowNodeData
  const Icon = iconMap[nodeData.icon as keyof typeof iconMap] ?? Database

  return (
    <article
      className={clsx(
        'w-56 max-w-[14rem] rounded-lg border bg-bda-panel p-3 text-sm shadow-lg',
        statusStyles[nodeData.status] ?? statusStyles.not_started,
        selected && 'ring-2 ring-bda-cyan/60',
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-bda-cyan !w-2 !h-2" />
      <header className="mb-2 flex min-w-0 items-center gap-2 font-medium text-bda-text">
        <Icon className="h-4 w-4 shrink-0 text-bda-cyan" />
        <span className="truncate">{nodeData.label}</span>
      </header>
      <p className="mb-2 line-clamp-3 text-xs leading-relaxed text-bda-muted">{nodeData.description}</p>
      <footer className="flex min-w-0 items-center justify-between gap-2 text-xs text-bda-muted">
        <span className="truncate">{nodeData.footer}</span>
        {nodeData.resource ? (
          <span className="rounded border border-bda-border px-1.5 py-0.5 uppercase">
            {nodeData.resource}
          </span>
        ) : null}
      </footer>
      <Handle type="source" position={Position.Right} className="!bg-bda-cyan !w-2 !h-2" />
    </article>
  )
}
