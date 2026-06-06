import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo } from 'react'
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

const nodeTypes: NodeTypes = { workflowNode: WorkflowNodeCard }
const edgeTypes: EdgeTypes = { workflowEdge: WorkflowEdge }

export interface WorkflowCanvasHandle {
  addNodeFromTemplate: (template: NodeTemplate, methods: string[]) => void
}

interface WorkflowCanvasProps {
  initialNodes?: BdaWorkflowNode[]
  initialEdges?: BdaWorkflowEdge[]
}

export const WorkflowCanvas = forwardRef<WorkflowCanvasHandle, WorkflowCanvasProps>(
  function WorkflowCanvas({ initialNodes, initialEdges }, ref) {
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes ?? defaultWorkflowNodes)
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges ?? defaultWorkflowEdges)

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

    const onConnect = useCallback(
      (connection: Connection) => {
        setEdges((eds) =>
          addEdge(
            {
              ...connection,
              type: 'workflowEdge',
              animated: true,
            },
            eds,
          ),
        )
      },
      [setEdges],
    )

    const addNodeFromTemplate = useCallback(
      (template: NodeTemplate, methods: string[]) => {
        const id = `custom-${template.id}-${Date.now()}`
        const newNode = {
          id,
          type: 'workflowNode',
          position: { x: 280 + (nodes.length % 3) * 40, y: 80 + (nodes.length % 4) * 60 },
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
      },
      [nodes.length, setNodes],
    )

    useImperativeHandle(ref, () => ({ addNodeFromTemplate }), [addNodeFromTemplate])

    const proOptions = useMemo(() => ({ hideAttribution: true }), [])

    return (
      <div className="h-[640px] rounded-lg border border-bda-border bg-bda-bg-elevated">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          proOptions={proOptions}
          nodesDraggable
          nodesConnectable
          edgesReconnectable
          panOnScroll
          selectionOnDrag
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
