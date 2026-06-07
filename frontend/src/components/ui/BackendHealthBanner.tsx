import { useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import { apiRequest } from '../../lib/api/client'

interface HealthData {
  status: string
}

function checkHealth() {
  return apiRequest<HealthData>('/health')
}

export function BackendHealthBanner() {
  const { isError, isFetched } = useQuery({
    queryKey: ['backend-health'],
    queryFn: checkHealth,
    retry: false,
    refetchInterval: 15_000,
    staleTime: 10_000,
  })

  if (!isFetched || !isError) return null

  return (
    <div
      role="alert"
      className="flex items-center gap-2 border-b border-bda-amber/40 bg-bda-amber/10 px-6 py-2 text-sm text-bda-amber"
    >
      <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span>
        API not reachable on port 8100. Run{' '}
        <code className="rounded bg-bda-panel px-1 py-0.5 text-xs text-bda-text">./scripts/dev.sh</code>{' '}
        or start uvicorn, then refresh.
      </span>
    </div>
  )
}
