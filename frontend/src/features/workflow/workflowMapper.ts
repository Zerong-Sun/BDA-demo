import type { WorkflowNode } from '../../lib/schemas/candidate'
import type { BdaWorkflowEdge, BdaWorkflowNode, WorkflowNodeData, WorkflowNodeStatus } from './workflowTypes'

const NODE_META: Record<
  string,
  { icon: string; resource: WorkflowNodeData['resource']; description?: string }
> = {
  target_intake: { icon: 'database', resource: 'local' },
  backbone_generation: { icon: 'wand-sparkles', resource: 'gpu' },
  sequence_generation: { icon: 'dna', resource: 'gpu' },
  fold_prediction: { icon: 'scan-search', resource: 'gpu' },
  scoring: { icon: 'activity', resource: 'cpu' },
  selection: { icon: 'filter', resource: 'cpu' },
  experiment: { icon: 'flask-conical', resource: 'manual' },
}

function mapStatus(status: string): WorkflowNodeStatus {
  switch (status) {
    case 'completed':
      return 'completed'
    case 'running':
      return 'running'
    case 'failed':
      return 'failed'
    case 'queued':
      return 'queued'
    case 'requires_review':
      return 'requires_review'
    case 'skipped':
      return 'skipped'
    default:
      return 'not_started'
  }
}

function parseMetrics(metrics: WorkflowNode['metrics_json']): Record<string, unknown> {
  if (!metrics) return {}
  if (typeof metrics === 'string') {
    try {
      return JSON.parse(metrics) as Record<string, unknown>
    } catch {
      return {}
    }
  }
  return metrics as Record<string, unknown>
}

export function footerFromMetrics(node: WorkflowNode): string {
  const metrics = parseMetrics(node.metrics_json)
  const parts: string[] = []
  if (metrics.generated != null) parts.push(`${metrics.generated} generated`)
  if (metrics.designed != null) parts.push(`${metrics.designed} designed`)
  if (metrics.folded != null) parts.push(`${metrics.folded} folded`)
  if (metrics.scored != null) parts.push(`${metrics.scored} scored`)
  if (metrics.ordered != null) parts.push(`${metrics.ordered} ordered`)
  if (metrics.bli_positive != null) parts.push(`${metrics.bli_positive} BLI hits`)
  if (metrics.inputs_confirmed != null) parts.push(`${metrics.inputs_confirmed} inputs confirmed`)
  if (parts.length > 0) return parts[0]
  return node.logs?.split('.')[0] ?? node.status
}

export function mapApiNodesToGraph(apiNodes: WorkflowNode[]): {
  nodes: BdaWorkflowNode[]
  edges: BdaWorkflowEdge[]
} {
  const nodes: BdaWorkflowNode[] = apiNodes.map((node, index) => {
    const meta = NODE_META[node.node_type] ?? { icon: 'database', resource: 'local' as const }
    return {
      id: node.node_run_id,
      type: 'workflowNode',
      position: { x: 40 + index * 220, y: 120 + (index % 2) * 140 },
      data: {
        label: node.node_name,
        description: meta.description ?? node.node_name,
        icon: meta.icon,
        status: mapStatus(node.status),
        footer: footerFromMetrics(node),
        resource: meta.resource,
      },
    }
  })

  const edges: BdaWorkflowEdge[] = apiNodes.slice(0, -1).map((node, index) => ({
    id: `e-${node.node_run_id}-${apiNodes[index + 1].node_run_id}`,
    source: node.node_run_id,
    target: apiNodes[index + 1].node_run_id,
    type: 'workflowEdge',
    animated: apiNodes[index + 1].status === 'running',
  }))

  return { nodes, edges }
}
