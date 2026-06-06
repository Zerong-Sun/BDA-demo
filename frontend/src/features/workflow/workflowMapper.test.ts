import { describe, expect, it } from 'vitest'
import { mapApiNodesToGraph, mapStatusForTest } from './workflowMapper'

describe('workflowMapper', () => {
  it('maps node statuses', () => {
    expect(mapStatusForTest('completed')).toBe('completed')
    expect(mapStatusForTest('running')).toBe('running')
    expect(mapStatusForTest('unknown')).toBe('not_started')
  })

  it('creates layered graph edges', () => {
    const graph = mapApiNodesToGraph([
      {
        node_run_id: 'n1',
        workflow_run_id: 'r1',
        node_type: 'target_intake',
        node_name: 'Target protein',
        status: 'completed',
      },
      {
        node_run_id: 'n2',
        workflow_run_id: 'r1',
        node_type: 'backbone_generation',
        node_name: 'RFdiffusion',
        status: 'running',
      },
    ])

    expect(graph.nodes).toHaveLength(2)
    expect(graph.edges).toHaveLength(1)
    expect(graph.edges[0]?.animated).toBe(true)
  })
})
