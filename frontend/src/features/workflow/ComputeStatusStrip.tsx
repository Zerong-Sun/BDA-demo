import { useQuery } from '@tanstack/react-query'
import { Server, ServerOff } from 'lucide-react'
import { getClusterHealth, listComputeNodes } from '../../lib/api/registry'
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
  const { data: clusterHealth } = useQuery({
    queryKey: ['cluster-health'],
    queryFn: getClusterHealth,
    refetchInterval: 30_000,
  })

  const gpuNodes = nodes.filter((node) => node.node_type === 'GPU')
  const cpuNodes = nodes.filter((node) => node.node_type === 'CPU')
  const gpuAvailable = gpuNodes.some((node) => node.status === 'available')
  const cpuAvailable = cpuNodes.some((node) => node.status === 'available')

  return (
    <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-bda-border bg-bda-panel px-4 py-3 text-sm">
      <span className="inline-flex items-center gap-2 text-bda-muted">
        {clusterHealth?.connected ? (
          <Server className="h-4 w-4 text-bda-green" aria-hidden="true" />
        ) : (
          <ServerOff className="h-4 w-4 text-bda-amber" aria-hidden="true" />
        )}
        Compute access
      </span>
      {clusterHealth?.mode === 'remote_lsf' ? (
        <>
          <span className={clusterHealth.connected ? 'text-bda-green' : 'text-bda-amber'}>
            SUSTech LSF: {clusterHealth.connected ? 'connected' : 'unreachable'}
          </span>
          {clusterHealth.connected && clusterHealth.queues.length > 0 ? (
            <span className="max-w-full truncate text-xs text-bda-muted" title={clusterHealth.queues.join('\n')}>
              Queues: {clusterHealth.queues.slice(0, 3).join(' · ')}
            </span>
          ) : null}
          {clusterHealth.connected && clusterHealth.all_queues?.length ? (
            <span
              className="max-w-full truncate text-xs text-bda-muted"
              title={clusterHealth.all_queues.join('\n')}
            >
              More queues: {clusterHealth.all_queues.slice(0, 6).join(' · ')}
            </span>
          ) : null}
        </>
      ) : null}
      <span className={gpuAvailable ? 'text-bda-green' : 'text-bda-amber'}>
        GPU worker: {gpuAvailable ? 'available' : 'unavailable'}
      </span>
      <span className={cpuAvailable ? 'text-bda-green' : 'text-bda-amber'}>
        CPU worker: {cpuAvailable ? 'available' : 'unavailable'}
      </span>
      {!gpuAvailable && !cpuAvailable && clusterHealth?.mode !== 'remote_lsf' ? (
        <span className="text-xs text-bda-muted">
          Compute mode: {health?.compute ?? 'demo'} · use local mode for built-in stub runners or docker mode for containers.
        </span>
      ) : null}
    </div>
  )
}
