export type RequestMethod = 'GET' | 'POST' | 'PATCH'

export type HealthPayloadLike = {
  service: string
  status: string
  environment: string
  services: Record<string, { status: string }>
}

export function resolveApiBaseUrl() {
  const configured = (import.meta.env.VITE_API_BASE_URL || '').trim()
  if (configured) return configured
  if (typeof window !== 'undefined' && ['localhost', '127.0.0.1'].includes(window.location.hostname)) {
    return 'http://localhost:8000'
  }
  return ''
}

export const API_BASE_URL = resolveApiBaseUrl()
export const TOKEN_STORAGE_KEY = 'leasemanager.auth.token'

export const fallbackHealth: HealthPayloadLike = {
  service: 'leasemanager-api',
  status: 'unreachable',
  environment: 'unknown',
  services: { database: { status: 'down' }, redis: { status: 'down' } },
}

const PUBLIC_SAFE_DETAIL_STATUSES = new Set([400, 401, 403, 429])
const SENSITIVE_PUBLIC_ERROR_PATTERN =
  /(:\/\/|@|stack|traceback|password|passwd|pwd|secret|token|bearer|api[_-]?key|credential|credencial|database|relation|column|settings|vite[_-]?)/i

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function publicSafeApiErrorMessage(error: unknown, fallback: string) {
  if (
    error instanceof ApiError
    && PUBLIC_SAFE_DETAIL_STATUSES.has(error.status)
    && !SENSITIVE_PUBLIC_ERROR_PATTERN.test(error.message)
  ) {
    return error.message
  }
  return fallback
}

export async function apiRequest<T>(
  path: string,
  options: { method?: RequestMethod; token?: string | null; body?: unknown } = {},
) {
  if (!API_BASE_URL) {
    throw new ApiError(503, 'Servicio no disponible para este entorno.')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || 'GET',
    headers: {
      ...(options.token ? { Authorization: `Token ${options.token}` } : {}),
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  })

  let payload: unknown = null
  if (response.status !== 204) {
    payload = await response.json()
  }

  if (!response.ok) {
    const detail =
      payload && typeof payload === 'object' && 'detail' in payload && typeof payload.detail === 'string'
        ? payload.detail
        : 'No se pudo completar la operación.'
    throw new ApiError(response.status, detail)
  }

  return payload as T
}
