import type { ZodType } from 'zod'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

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

let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

function authToken(): string | null {
  return sessionStorage.getItem('bda_token')
}

const MAX_RETRIES = 2
const RETRYABLE_STATUS = new Set([429, 502, 503, 504])

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  schema?: ZodType<T>,
): Promise<T> {
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData)) {
    headers.set('content-type', 'application/json')
  }
  const token = authToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  // Only idempotent requests are safe to auto-retry on transient failures.
  const method = (options.method ?? 'GET').toUpperCase()
  const isIdempotent = method === 'GET' || method === 'HEAD'

  let response: Response
  let attempt = 0
  // Retry loop: handles transient network errors and retryable status codes
  // with exponential backoff for idempotent requests.
  for (;;) {
    try {
      response = await fetch(`${API_BASE}${path}`, { ...options, headers })
    } catch (networkError) {
      if (isIdempotent && attempt < MAX_RETRIES) {
        await sleep(300 * 2 ** attempt)
        attempt += 1
        continue
      }
      throw new ApiError(
        networkError instanceof Error ? networkError.message : 'Network request failed',
        0,
        networkError,
      )
    }

    if (isIdempotent && RETRYABLE_STATUS.has(response.status) && attempt < MAX_RETRIES) {
      await sleep(300 * 2 ** attempt)
      attempt += 1
      continue
    }
    break
  }

  if (response.status === 401) {
    onUnauthorized?.()
  }

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
  const data = payload.data
  if (schema) {
    return schema.parse(data)
  }
  return data
}

export function structureFileUrl(candidateId: string): string {
  return `${API_BASE}/candidates/${candidateId}/structure-file`
}

export function artifactUrl(relativePath: string): string {
  const normalized = relativePath.replace(/^\/+/, '').replace(/^artifacts\//, '')
  return `${API_BASE}/artifacts/${normalized}`
}

export function deliveryPackageDownloadUrl(projectId: string): string {
  return `${API_BASE}/projects/${projectId}/delivery-package/download`
}

export function getHealth() {
  return apiRequest<{ status: string; service: string; compute: string; database: string }>('/health')
}

export { API_BASE }
