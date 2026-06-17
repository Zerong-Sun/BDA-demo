import { useQuery } from '@tanstack/react-query'
import { ServerOff } from 'lucide-react'
import { listComputeNodes } from '../../lib/api/registry'
import { getHealth } from '../../lib/api/client'

export function ComputeStatusStrip() {
  const { data: nodes = [] } = useQuery({
    queryKey: ['compute-nodes'],
    queryFn: listComputeNodes,
  })
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
  })

  const gpuNodes = nodes.filter((node) => node.node_type === 'GPU')
  const cpuNodes = nodes.filter((node) => node.node_type === 'CPU')
  const gpuAvailable = gpuNodes.some((node) => node.status === 'available')
  const cpuAvailable = cpuNodes.some((node) => node.status === 'available')

  return (
    <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-bda-border bg-bda-panel px-4 py-3 text-sm">
      <span className="inline-flex items-center gap-2 text-bda-muted">
        <ServerOff className="h-4 w-4 text-bda-amber" aria-hidden="true" />
        Compute access
      </span>
      <span className={gpuAvailable ? 'text-bda-green' : 'text-bda-amber'}>
        GPU worker: {gpuAvailable ? 'available' : 'unavailable'}
      </span>
      <span className={cpuAvailable ? 'text-bda-green' : 'text-bda-amber'}>
        CPU worker: {cpuAvailable ? 'available' : 'unavailable'}
      </span>
      {!gpuAvailable && !cpuAvailable ? (
        <span className="text-xs text-bda-muted">
          Compute mode: {health?.compute ?? 'demo'} · use local mode for built-in stub runners or docker mode for containers.
        </span>
      ) : null}
    </div>
  )
}
