const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

export interface ApiEnvelope<T> {
  data: T
  trace_id: string
}

export class ApiError extends Error {
  status: number
  payload?: unknown

  constructor(message: string, status: number, payload?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData)) {
    headers.set('content-type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let payload: unknown
    try {
      payload = await response.json()
    } catch {
      payload = null
    }
    const message =
      (payload as { message?: string })?.message ??
      (payload as { detail?: string })?.detail ??
      `Request failed (${response.status})`
    throw new ApiError(message, response.status, payload)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const payload = (await response.json()) as ApiEnvelope<T>
  return payload.data
}

export function structureFileUrl(candidateId: string): string {
  return `${API_BASE}/candidates/${candidateId}/structure-file`
}
