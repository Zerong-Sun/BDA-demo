import type { WorkflowEdge, WorkflowNode } from '../../lib/schemas/workflow'
import type { BdaWorkflowEdge, BdaWorkflowNode, WorkflowNodeData, WorkflowNodeStatus } from './workflowTypes'

const NODE_META: Record<
  string,
  { icon: string; resource: WorkflowNodeData['resource']; description?: string; column: number }
> = {
  target_intake: { icon: 'database', resource: 'local', column: 0 },
  backbone_generation: { icon: 'wand-sparkles', resource: 'gpu', column: 1 },
  sequence_generation: { icon: 'dna', resource: 'gpu', column: 2 },
  fold_prediction: { icon: 'scan-search', resource: 'gpu', column: 3 },
  scoring: { icon: 'activity', resource: 'cpu', column: 4 },
  selection: { icon: 'filter', resource: 'cpu', column: 5 },
  experiment: { icon: 'flask-conical', resource: 'manual', column: 6 },
}

const COLUMN_WIDTH = 220
const ROW_HEIGHT = 140

function mapStatus(status: string): WorkflowNodeStatus {
  switch (status) {
    case 'completed':
      return 'completed'
    case 'running':
    case 'staging':
    case 'collecting_outputs':
      return 'running'
    case 'failed':
      return 'failed'
    case 'queued':
      return 'queued'
    case 'requires_review':
      return 'requires_review'
    case 'skipped':
      return 'skipped'
    case 'demo':
      return 'demo'
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

function parsePosition(node: WorkflowNode, index: number): { x: number; y: number } {
  if (node.position_json) {
    try {
      const parsed = JSON.parse(node.position_json) as { x?: number; y?: number }
      if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
        return { x: parsed.x, y: parsed.y }
      }
    } catch {
      /* fall through */
    }
  }
  const meta = NODE_META[node.node_type] ?? { column: index, icon: 'database', resource: 'local' as const }
  return {
    x: 40 + meta.column * COLUMN_WIDTH,
    y: 80 + (index % 2) * ROW_HEIGHT,
  }
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
    const meta = NODE_META[node.node_type] ?? {
      icon: 'database',
      resource: 'local' as const,
      column: index,
    }
    return {
      id: node.node_run_id,
      type: 'workflowNode',
      position: parsePosition(node, index),
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

export function mapApiGraphToGraph(apiNodes: WorkflowNode[], apiEdges: WorkflowEdge[]): {
  nodes: BdaWorkflowNode[]
  edges: BdaWorkflowEdge[]
} {
  const mapped = mapApiNodesToGraph(apiNodes)
  if (apiEdges.length === 0) return { ...mapped, edges: [] }
  return {
    nodes: mapped.nodes,
    edges: apiEdges.map((edge) => ({
      id: edge.edge_id,
      source: edge.source_node_run_id,
      target: edge.target_node_run_id,
      sourceHandle: edge.source_port,
      targetHandle: edge.target_port,
      type: 'workflowEdge',
      animated: edge.edge_type === 'data',
      label: edge.edge_type === 'feedback' ? 'feedback' : undefined,
      data: {
        edgeType: edge.edge_type,
        sourcePort: edge.source_port,
        targetPort: edge.target_port,
      },
    })),
  }
}

export function mapStatusForTest(status: string): WorkflowNodeStatus {
  return mapStatus(status)
}
