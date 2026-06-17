import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type EdgeTypes,
  type Node,
  type NodeTypes,
} from '@xyflow/react'
import { Loader2 } from 'lucide-react'
import { WorkflowNodeCard } from './WorkflowNode'
import { WorkflowEdge } from './WorkflowEdge'
import {
  defaultWorkflowEdges,
  defaultWorkflowNodes,
  type BdaWorkflowEdge,
  type BdaWorkflowNode,
  type NodeTemplate,
  type WorkflowNodeData,
} from './workflowTypes'
import { saveWorkflowLayout, addWorkflowNode } from '../../lib/api/workflow'

const nodeTypes: NodeTypes = { workflowNode: WorkflowNodeCard }
const edgeTypes: EdgeTypes = { workflowEdge: WorkflowEdge }

export interface WorkflowCanvasHandle {
  addNodeFromTemplate: (
    template: NodeTemplate,
    nodeName: string,
    methods: string[],
    parameters: Record<string, unknown>,
  ) => Promise<void>
}

interface WorkflowCanvasProps {
  initialNodes?: BdaWorkflowNode[]
  initialEdges?: BdaWorkflowEdge[]
  workflowRunId?: string
  readOnly?: boolean
  onNodeAdded?: () => void
  onNodeSelected?: (nodeId: string | null) => void
}

export const WorkflowCanvas = forwardRef<WorkflowCanvasHandle, WorkflowCanvasProps>(
  function WorkflowCanvas(
    { initialNodes, initialEdges, workflowRunId, readOnly = false, onNodeAdded, onNodeSelected },
    ref,
  ) {
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes ?? defaultWorkflowNodes)
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges ?? defaultWorkflowEdges)
    const [addingNode, setAddingNode] = useState(false)
    const saveTimer = useRef<number | null>(null)
    const isInitialMount = useRef(true)
    const nodesRef = useRef(nodes)
    const edgesRef = useRef(edges)
    nodesRef.current = nodes
    edgesRef.current = edges

    useEffect(() => {
      if (!initialNodes) return

      if (isInitialMount.current) {
        isInitialMount.current = false
        setNodes(initialNodes)
        setEdges(initialEdges ?? [])
        return
      }

      if (initialNodes.length === 0) {
        setNodes([])
        setEdges(initialEdges ?? [])
        return
      }

      // Merge: preserve positions of existing nodes, add new ones from polling
      const existingPositions = new Map(
        nodesRef.current.map((n) => [n.id, n.position]),
      )

      setNodes((current) => {
        const currentById = new Map(current.map((node) => [node.id, node]))
        return initialNodes.map((node) => {
          const existing = currentById.get(node.id)
          return {
            ...node,
            position: existingPositions.get(node.id) ?? node.position,
            selected: existing?.selected,
          }
        })
      })

      setEdges((current) => {
        const incoming = initialEdges ?? []
        const incomingIds = new Set(incoming.map((e) => e.id))
        const retained = current.filter((edge) => incomingIds.has(edge.id))
        const retainedIds = new Set(retained.map((e) => e.id))
        const added = incoming.filter((edge) => !retainedIds.has(edge.id))
        return [...retained, ...added]
      })
    }, [initialNodes, initialEdges, setNodes, setEdges])

    const persistLayout = useCallback(
      (currentNodes: Node[], currentEdges: BdaWorkflowEdge[]) => {
        if (!workflowRunId) return
        if (saveTimer.current) window.clearTimeout(saveTimer.current)
        saveTimer.current = window.setTimeout(() => {
          void saveWorkflowLayout(workflowRunId, {
            nodes: currentNodes.map((node) => ({
              node_run_id: node.id,
              position: node.position,
            })),
            edges: currentEdges.map((edge) => ({
              id: edge.id,
              source_node_run_id: edge.source,
              target_node_run_id: edge.target,
              source_port: typeof edge.sourceHandle === 'string' ? edge.sourceHandle : 'output',
              target_port: typeof edge.targetHandle === 'string' ? edge.targetHandle : 'input',
              edge_type: edge.label === 'feedback' ? 'feedback' : 'data',
            })),
          }).catch(() => undefined)
        }, 500)
      },
      [workflowRunId],
    )

    const onConnect = useCallback(
      (connection: Connection) => {
        if (readOnly) return
        setEdges((eds) => {
          const next = addEdge({ ...connection, type: 'workflowEdge', animated: true }, eds)
          persistLayout(nodesRef.current, next)
          return next
        })
      },
      [readOnly, setEdges, persistLayout],
    )

    const onNodeDragStop = useCallback(() => {
      persistLayout(nodesRef.current, edgesRef.current)
    }, [persistLayout])

    const addNodeFromTemplate = useCallback(
      async (template: NodeTemplate, nodeName: string, methods: string[], parameters: Record<string, unknown>) => {
        if (addingNode) return
        setAddingNode(true)

        try {
          const currentLen = nodesRef.current.length

          // Calculate position with staggering to avoid overlap
          const col = currentLen % 3
          const row = Math.floor(currentLen / 3) % 4
          const x = 280 + col * 40
          const y = 80 + row * 60 + col * 20

          if (!workflowRunId || readOnly) {
            // Demo / local-only mode
            const id = `custom-${template.id}-${Date.now()}`
            const newNode: Node = {
              id,
              type: 'workflowNode',
              position: { x, y },
              data: {
                label: nodeName,
                description: template.body,
              icon: template.icon,
              status: 'demo' as const,
              footer: methods.join(' · '),
                resource: template.resource,
                methods,
                parameters,
              } satisfies WorkflowNodeData,
            }
            setNodes((nds) => [...nds, newNode] as BdaWorkflowNode[])
            return
          }

          const created = await addWorkflowNode(workflowRunId, {
            node_type: template.nodeType,
            node_name: nodeName,
            model_name: template.modelName,
            model_version: template.modelVersion,
            model_plugin_id: template.pluginId,
            parameters_json: { methods, ...parameters },
            position: { x, y },
          })
          const newNode: BdaWorkflowNode = {
            id: created.node_run_id,
            type: 'workflowNode',
            position: { x, y },
            data: {
              label: created.node_name,
              description: template.body,
              icon: template.icon,
              status: 'not_started',
              footer: methods.join(' · '),
              resource: template.resource,
              methods,
              parameters,
            },
          }
          setNodes((nds) => [...nds, newNode])
          onNodeAdded?.()
        } finally {
          setAddingNode(false)
        }
      },
      [addingNode, readOnly, workflowRunId, setNodes, onNodeAdded],
    )

    useImperativeHandle(ref, () => ({ addNodeFromTemplate }), [addNodeFromTemplate])

    const proOptions = useMemo(() => ({ hideAttribution: true }), [])

    return (
      <div className="relative h-[640px] rounded-lg border border-bda-border bg-bda-bg-elevated">
        {readOnly ? (
          <p className="border-b border-bda-border px-3 py-2 text-xs text-bda-muted">
            Completed run — nodes can be repositioned; adding or rewiring steps is locked.
          </p>
        ) : null}
        {addingNode ? (
          <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-bda-bg/60 backdrop-blur-sm">
            <div className="flex items-center gap-2 rounded-lg border border-bda-border bg-bda-panel px-4 py-3 text-sm text-bda-text shadow-lg">
              <Loader2 className="h-4 w-4 animate-spin text-bda-cyan" />
              Adding node to workflow...
            </div>
          </div>
        ) : null}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={(_, node) => onNodeSelected?.(node.id)}
          onPaneClick={() => onNodeSelected?.(null)}
          onNodeDragStop={onNodeDragStop}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          proOptions={proOptions}
          nodesDraggable
          nodesConnectable={!readOnly}
          edgesReconnectable={!readOnly}
          panOnScroll
          selectionOnDrag={false}
        >
          <Background gap={20} color="#2c323d" />
          <MiniMap
            nodeColor="#39d2d8"
            maskColor="rgba(5,6,8,0.75)"
            className="!bg-bda-panel !border-bda-border"
          />
          <Controls className="!bg-bda-panel !border-bda-border !shadow-none [&>button]:!bg-bda-panel [&>button]:!border-bda-border [&>button]:!text-bda-text" />
        </ReactFlow>
      </div>
    )
  },
)
