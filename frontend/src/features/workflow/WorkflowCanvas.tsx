import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef } from 'react'
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
  addNodeFromTemplate: (template: NodeTemplate, methods: string[]) => Promise<void>
}

interface WorkflowCanvasProps {
  initialNodes?: BdaWorkflowNode[]
  initialEdges?: BdaWorkflowEdge[]
  workflowRunId?: string
  readOnly?: boolean
  onNodeAdded?: () => void
}

export const WorkflowCanvas = forwardRef<WorkflowCanvasHandle, WorkflowCanvasProps>(
  function WorkflowCanvas(
    { initialNodes, initialEdges, workflowRunId, readOnly = false, onNodeAdded },
    ref,
  ) {
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes ?? defaultWorkflowNodes)
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges ?? defaultWorkflowEdges)
    const saveTimer = useRef<number | null>(null)
    const isInitialMount = useRef(true)
    const nodesRef = useRef(nodes)
    const edgesRef = useRef(edges)
    nodesRef.current = nodes
    edgesRef.current = edges

    useEffect(() => {
      if (!initialNodes || initialNodes.length === 0) return

      if (isInitialMount.current) {
        isInitialMount.current = false
        setNodes(initialNodes)
        if (initialEdges && initialEdges.length > 0) {
          setEdges(initialEdges)
        }
        return
      }

      // Merge: preserve positions of existing nodes, add new ones from polling
      const existingPositions = new Map(
        nodesRef.current.map((n) => [n.id, n.position]),
      )
      const incomingIds = new Set(initialNodes.map((n) => n.id))
      const hasChange =
        incomingIds.size !== nodesRef.current.length ||
        initialNodes.some((n) => !nodesRef.current.find((e) => e.id === n.id))

      if (!hasChange) return

      setNodes((current) => {
        const currentIds = new Set(current.map((n) => n.id))
        const merged = [
          ...current.filter((n) => incomingIds.has(n.id)),
          ...initialNodes
            .filter((n) => !currentIds.has(n.id))
            .map((n) => ({
              ...n,
              position: existingPositions.get(n.id) ?? n.position,
            })),
        ]
        return merged
      })

      if (initialEdges && initialEdges.length > 0) {
        setEdges((current) => {
          const currentIds = new Set(current.map((e) => e.id))
          const newEdges = initialEdges!.filter((e) => !currentIds.has(e.id))
          return newEdges.length > 0 ? [...current, ...newEdges] : current
        })
      }
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
              source: edge.source,
              target: edge.target,
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
      async (template: NodeTemplate, methods: string[]) => {
        if (readOnly || !workflowRunId) {
          const currentLen = nodesRef.current.length
          const id = `custom-${template.id}-${Date.now()}`
          const newNode = {
            id,
            type: 'workflowNode',
            position: { x: 280 + (currentLen % 3) * 40, y: 80 + (currentLen % 4) * 60 },
            data: {
              label: template.title,
              description: template.body,
              icon: template.icon,
              status: 'demo',
              footer: methods.join(', '),
              resource: template.resource,
              methods,
            } satisfies WorkflowNodeData,
          }
          setNodes((nds) => [...nds, newNode])
          return
        }

        const currentLen = nodesRef.current.length
        const created = await addWorkflowNode(workflowRunId, {
          node_type: template.nodeType,
          node_name: template.title,
          model_name: template.modelName,
          model_version: template.modelVersion,
          model_plugin_id: template.pluginId,
          parameters_json: { methods },
          position: { x: 280 + (currentLen % 3) * 40, y: 80 + (currentLen % 4) * 60 },
        })
        const newNode: BdaWorkflowNode = {
          id: created.node_run_id,
          type: 'workflowNode',
          position: { x: 280 + (currentLen % 3) * 40, y: 80 + (currentLen % 4) * 60 },
          data: {
            label: created.node_name,
            description: template.body,
            icon: template.icon,
            status: 'not_started',
            footer: methods.join(', '),
            resource: template.resource,
            methods,
          },
        }
        setNodes((nds) => [...nds, newNode])
        onNodeAdded?.()
      },
      [readOnly, workflowRunId, setNodes, onNodeAdded],
    )

    useImperativeHandle(ref, () => ({ addNodeFromTemplate }), [addNodeFromTemplate])

    const proOptions = useMemo(() => ({ hideAttribution: true }), [])

    return (
      <div className="h-[640px] rounded-lg border border-bda-border bg-bda-bg-elevated">
        {readOnly ? (
          <p className="border-b border-bda-border px-3 py-2 text-xs text-bda-muted">
            Completed run — nodes can be repositioned; adding or rewiring steps is locked.
          </p>
        ) : null}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
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
