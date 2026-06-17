import type { Node, Edge } from '@xyflow/react'

export type WorkflowNodeStatus =
  | 'not_started'
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped'
  | 'requires_review'
  | 'demo'

export interface WorkflowNodeData extends Record<string, unknown> {
  label: string
  description: string
  icon: string
  status: WorkflowNodeStatus
  footer: string
  resource?: 'cpu' | 'gpu' | 'local' | 'manual'
  methods?: string[]
  parameters?: Record<string, unknown>
}

export type BdaWorkflowNode = Node<WorkflowNodeData>
export type BdaWorkflowEdge = Edge

export interface NodeTemplate {
  id: string
  icon: string
  title: string
  body: string
  resource: WorkflowNodeData['resource']
  nodeType: string
  modelName?: string
  modelVersion?: string
  pluginId?: string
  parameterSchema?: unknown
}

export const nodeTemplates: Record<string, NodeTemplate> = {
  rf: {
    id: 'rf',
    icon: 'wand-sparkles',
    title: 'Backbone generation',
    body: 'Explore binder geometry with RFdiffusion',
    resource: 'gpu',
    nodeType: 'backbone_generation',
    modelName: 'RFdiffusion',
    modelVersion: 'demo-1.0',
    pluginId: 'plugin_rfdiffusion',
  },
  mpnn: {
    id: 'mpnn',
    icon: 'dna',
    title: 'Sequence design',
    body: 'ProteinMPNN sequence search with diversity constraints',
    resource: 'gpu',
    nodeType: 'sequence_generation',
    modelName: 'ProteinMPNN',
    modelVersion: 'demo-1.0',
    pluginId: 'plugin_proteinmpnn',
  },
  af2: {
    id: 'af2',
    icon: 'scan-search',
    title: 'Fold prediction',
    body: 'AlphaFold2 evaluates complex confidence and interface pAE',
    resource: 'gpu',
    nodeType: 'fold_prediction',
    modelName: 'AlphaFold2',
    modelVersion: 'demo-2.3',
    pluginId: 'plugin_alphafold2',
  },
  rosetta: {
    id: 'rosetta',
    icon: 'activity',
    title: 'Rosetta scoring',
    body: 'Relax and interface scoring for energy and clashes',
    resource: 'cpu',
    nodeType: 'scoring',
    modelName: 'Rosetta',
    modelVersion: 'demo-2026.06',
    pluginId: 'plugin_rosetta',
  },
  filter: {
    id: 'filter',
    icon: 'filter',
    title: 'BDA filters',
    body: 'Rank by interface, solubility, aggregation, expression risk',
    resource: 'cpu',
    nodeType: 'selection',
    modelName: 'BDA filters',
    modelVersion: 'demo-1.0',
  },
  lab: {
    id: 'lab',
    icon: 'flask-conical',
    title: 'Wet-lab validation',
    body: 'Expression, purification, BLI, SEC, thermal shift',
    resource: 'manual',
    nodeType: 'experiment',
  },
}

export const defaultWorkflowNodes: BdaWorkflowNode[] = [
  {
    id: 'target',
    type: 'workflowNode',
    position: { x: 40, y: 60 },
    data: {
      label: 'Target protein',
      description: 'PD-1 structure, interface residues, assay constraints',
      icon: 'database',
      status: 'completed',
      footer: '3/3 inputs confirmed',
      resource: 'local',
    },
  },
  {
    id: 'requirements',
    type: 'workflowNode',
    position: { x: 40, y: 420 },
    data: {
      label: 'Task requirements',
      description: 'Design high-affinity PD-1 binders with developability constraints',
      icon: 'file-json',
      status: 'completed',
      footer: '5/5 constraints parsed',
      resource: 'local',
    },
  },
  {
    id: 'rfdiffusion',
    type: 'workflowNode',
    position: { x: 280, y: 240 },
    data: {
      label: 'Backbone generation',
      description: 'Explore binder geometry with RFdiffusion',
      icon: 'wand-sparkles',
      status: 'running',
      footer: '1,248/18,000 generated',
      resource: 'gpu',
    },
  },
  {
    id: 'mpnn',
    type: 'workflowNode',
    position: { x: 500, y: 240 },
    data: {
      label: 'Sequence design',
      description: 'ProteinMPNN sequence search with diversity constraints',
      icon: 'dna',
      status: 'queued',
      footer: '384/1,248 designed',
      resource: 'gpu',
    },
  },
  {
    id: 'af2',
    type: 'workflowNode',
    position: { x: 720, y: 60 },
    data: {
      label: 'Fold prediction',
      description: 'AlphaFold2 evaluates complex structure and local confidence',
      icon: 'scan-search',
      status: 'not_started',
      footer: '312/384 folded',
      resource: 'gpu',
    },
  },
  {
    id: 'rosetta',
    type: 'workflowNode',
    position: { x: 720, y: 240 },
    data: {
      label: 'Rosetta scoring',
      description: 'Rosetta relax estimates interface energy and clashes',
      icon: 'activity',
      status: 'not_started',
      footer: '120/312 scored',
      resource: 'cpu',
    },
  },
  {
    id: 'filters',
    type: 'workflowNode',
    position: { x: 720, y: 420 },
    data: {
      label: 'BDA filters',
      description: 'Affinity, solubility, aggregation risk, expression risk',
      icon: 'filter',
      status: 'completed',
      footer: '96/384 passed filters',
      resource: 'cpu',
    },
  },
  {
    id: 'wetlab',
    type: 'workflowNode',
    position: { x: 500, y: 420 },
    data: {
      label: 'Wet-lab validation',
      description: 'Expression, purification, BLI, SEC, thermal shift',
      icon: 'flask-conical',
      status: 'completed',
      footer: '9/48 hits confirmed',
      resource: 'manual',
    },
  },
]

export const defaultWorkflowEdges: BdaWorkflowEdge[] = [
  { id: 'e-target-rf', source: 'target', target: 'rfdiffusion', type: 'workflowEdge', animated: true },
  { id: 'e-req-rf', source: 'requirements', target: 'rfdiffusion', type: 'workflowEdge' },
  { id: 'e-rf-mpnn', source: 'rfdiffusion', target: 'mpnn', type: 'workflowEdge', animated: true },
  { id: 'e-mpnn-af2', source: 'mpnn', target: 'af2', type: 'workflowEdge' },
  { id: 'e-af2-rosetta', source: 'af2', target: 'rosetta', type: 'workflowEdge' },
  { id: 'e-rosetta-filters', source: 'rosetta', target: 'filters', type: 'workflowEdge' },
  { id: 'e-filters-wetlab', source: 'filters', target: 'wetlab', type: 'workflowEdge' },
  { id: 'e-wetlab-req', source: 'wetlab', target: 'requirements', type: 'workflowEdge', label: 'feedback' },
]
