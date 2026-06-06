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
    const nodesRef = useRef(nodes)
    const edgesRef = useRef(edges)
    nodesRef.current = nodes
    edgesRef.current = edges

    useEffect(() => {
      if (initialNodes && initialNodes.length > 0) {
        setNodes(initialNodes)
      }
    }, [initialNodes, setNodes])

    useEffect(() => {
      if (initialEdges && initialEdges.length > 0) {
        setEdges(initialEdges)
      }
    }, [initialEdges, setEdges])

    const persistLayout = useCallback(
      (currentNodes: Node[], currentEdges: BdaWorkflowEdge[]) => {
        if (!workflowRunId || readOnly) return
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
      [workflowRunId, readOnly],
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
            Completed workflow run is read-only.
          </p>
        ) : null}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={(changes) => {
            onNodesChange(changes)
            if (!readOnly) persistLayout(nodesRef.current, edgesRef.current)
          }}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          proOptions={proOptions}
          nodesDraggable={!readOnly}
          nodesConnectable={!readOnly}
          edgesReconnectable={!readOnly}
          panOnScroll
          selectionOnDrag={!readOnly}
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
