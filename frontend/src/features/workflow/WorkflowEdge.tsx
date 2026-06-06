import { BaseEdge, getBezierPath, type EdgeProps } from '@xyflow/react'

export function WorkflowEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  label,
  markerEnd,
  style,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  })

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: label === 'feedback' ? '#f7b84b' : '#39d2d8',
          strokeWidth: 2,
          ...style,
        }}
      />
      {label ? (
        <text
          x={labelX}
          y={labelY}
          className="fill-bda-amber text-[10px]"
          textAnchor="middle"
          dominantBaseline="middle"
        >
          {label}
        </text>
      ) : null}
    </>
  )
}
