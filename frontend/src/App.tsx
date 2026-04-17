import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'

import heroImage from './assets/hero.png'
import { apiRequest, API_BASE_URL, fallbackHealth, TOKEN_STORAGE_KEY } from './backoffice/api'
import { Metric, toneFor } from './backoffice/shared'
import './App.css'

const AuthenticatedApp = lazy(() => import('./AuthenticatedApp'))

const USER_STORAGE_KEY = 'leasemanager.auth.user'
const OVERVIEW_STORAGE_KEY_PREFIX = 'leasemanager.overview'
const CONTROL_STORAGE_KEY_PREFIX = 'leasemanager.control'
const HEALTH_STORAGE_KEY = 'leasemanager.health'

type HealthPayload = {
  service: string
  status: string
  environment: string
  services: Record<string, { status: string }>
}

type CurrentUser = {
  id: number
  username: string
  display_name: string
  default_role_code: string
}

type LoginBootstrap = {
  overview?: {
    dashboard?: unknown
    manual_summary?: unknown
  } | null
  control?: {
    empresas?: unknown[]
    regimenes_tributarios?: unknown[]
    configuraciones_fiscales?: unknown[]
    cuentas_contables?: unknown[]
    reglas_contables?: unknown[]
    matrices_reglas?: unknown[]
    eventos_contables?: unknown[]
    asientos_contables?: unknown[]
    obligaciones_mensuales?: unknown[]
    cierres_mensuales?: unknown[]
  } | null
} | null

type LoginResponse = {
  token: string
  user: CurrentUser
  bootstrap?: LoginBootstrap
}

const unknownHealth: HealthPayload = {
  service: 'leasemanager-api',
  status: 'unknown',
  environment: 'unknown',
  services: {
    database: { status: 'unknown' },
    redis: { status: 'unknown' },
  },
}

function storeCurrentUser(user: CurrentUser | null) {
  if (typeof window === 'undefined') return
  if (!user) {
    localStorage.removeItem(USER_STORAGE_KEY)
    return
  }
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
}

function readStoredHealth(): HealthPayload | null {
  if (typeof window === 'undefined') return null
  const rawHealth = localStorage.getItem(HEALTH_STORAGE_KEY)
  if (!rawHealth) return null
  try {
    return JSON.parse(rawHealth) as HealthPayload
  } catch {
    localStorage.removeItem(HEALTH_STORAGE_KEY)
    return null
  }
}

function storeHealthSnapshot(health: HealthPayload | null) {
  if (typeof window === 'undefined') return
  if (!health) {
    localStorage.removeItem(HEALTH_STORAGE_KEY)
    return
  }
  localStorage.setItem(HEALTH_STORAGE_KEY, JSON.stringify(health))
}

function overviewStorageKey(user: Pick<CurrentUser, 'id' | 'username' | 'default_role_code'> | null) {
  if (!user) return null
  return `${OVERVIEW_STORAGE_KEY_PREFIX}:${user.id}:${user.username}:${user.default_role_code}`
}

function readStoredOverviewSnapshot(
  user: Pick<CurrentUser, 'id' | 'username' | 'default_role_code'> | null,
): { dashboard: unknown; manualSummary: unknown; lastLoadedAt: string } | null {
  if (typeof window === 'undefined') return null
  const key = overviewStorageKey(user)
  if (!key) return null
  const rawSnapshot = localStorage.getItem(key)
  if (!rawSnapshot) return null
  try {
    return JSON.parse(rawSnapshot) as { dashboard: unknown; manualSummary: unknown; lastLoadedAt: string }
  } catch {
    localStorage.removeItem(key)
    return null
  }
}

function storeOverviewSnapshot(
  user: Pick<CurrentUser, 'id' | 'username' | 'default_role_code'> | null,
  snapshot: { dashboard: unknown; manualSummary: unknown; lastLoadedAt: string },
) {
  if (typeof window === 'undefined') return
  const key = overviewStorageKey(user)
  if (!key) return
  localStorage.setItem(key, JSON.stringify(snapshot))
}

function controlStorageKey(user: Pick<CurrentUser, 'id' | 'username' | 'default_role_code'> | null) {
  if (!user) return null
  return `${CONTROL_STORAGE_KEY_PREFIX}:${user.id}:${user.username}:${user.default_role_code}`
}

function storeControlSnapshot(
  user: Pick<CurrentUser, 'id' | 'username' | 'default_role_code'> | null,
  snapshot: NonNullable<LoginBootstrap>['control'],
  lastLoadedAt: string,
) {
  if (typeof window === 'undefined' || !snapshot) return
  const key = controlStorageKey(user)
  if (!key) return
  localStorage.setItem(
    key,
    JSON.stringify({
      empresas: snapshot.empresas || [],
      regimenesTributarios: snapshot.regimenes_tributarios || [],
      configuracionesFiscales: snapshot.configuraciones_fiscales || [],
      cuentasContables: snapshot.cuentas_contables || [],
      reglasContables: snapshot.reglas_contables || [],
      matricesReglas: snapshot.matrices_reglas || [],
      eventosContables: snapshot.eventos_contables || [],
      asientosContables: snapshot.asientos_contables || [],
      obligacionesMensuales: snapshot.obligaciones_mensuales || [],
      cierresMensuales: snapshot.cierres_mensuales || [],
      lastLoadedAt,
    }),
  )
}

export default function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY))
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [health, setHealth] = useState<HealthPayload>(() => readStoredHealth() || unknownHealth)
  const healthLoadTimeoutRef = useRef<number | null>(null)
  const loginChunkPrefetchRef = useRef(false)
  const demoWarmupRequestedRef = useRef(false)

  useEffect(() => {
    if (!API_BASE_URL || typeof window === 'undefined') {
      return
    }

    let apiOrigin = ''
    try {
      apiOrigin = new URL(API_BASE_URL, window.location.origin).origin
    } catch {
      return
    }

    if (!apiOrigin || apiOrigin === window.location.origin) {
      return
    }

    const head = document.head
    const preconnect = document.createElement('link')
    preconnect.rel = 'preconnect'
    preconnect.href = apiOrigin
    preconnect.crossOrigin = 'anonymous'

    const dnsPrefetch = document.createElement('link')
    dnsPrefetch.rel = 'dns-prefetch'
    dnsPrefetch.href = apiOrigin

    head.appendChild(preconnect)
    head.appendChild(dnsPrefetch)

    return () => {
      preconnect.remove()
      dnsPrefetch.remove()
    }
  }, [])

  useEffect(() => {
    if (token || isLoggingIn || loginChunkPrefetchRef.current) {
      return
    }

    const runPrefetch = () => {
      loginChunkPrefetchRef.current = true
      void import('./backoffice/workspaces/OverviewWorkspace')
      void import('./backoffice/workspaces/ContabilidadWorkspace')
      void import('./AuthenticatedApp')
    }

    const idleCallbackId =
      typeof window.requestIdleCallback === 'function'
        ? window.requestIdleCallback(() => runPrefetch())
        : null
    const timeoutId =
      idleCallbackId === null
        ? window.setTimeout(() => runPrefetch(), 0)
        : null

    return () => {
      if (idleCallbackId !== null && typeof window.cancelIdleCallback === 'function') {
        window.cancelIdleCallback(idleCallbackId)
      }
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId)
      }
    }
  }, [token, isLoggingIn])

  useEffect(() => {
    if (!API_BASE_URL || token || isLoggingIn || demoWarmupRequestedRef.current) {
      return
    }

    const timeoutId = window.setTimeout(() => {
      demoWarmupRequestedRef.current = true
      void apiRequest<void>('/api/v1/auth/demo-warmup/', { method: 'POST' }).catch(() => {
        demoWarmupRequestedRef.current = false
      })
    }, 250)

    return () => window.clearTimeout(timeoutId)
  }, [token, isLoggingIn])

  useEffect(() => {
    if (token || isLoggingIn) {
      return
    }

    const timeoutId = window.setTimeout(async () => {
      try {
        const nextHealth = await apiRequest<HealthPayload>('/api/v1/health/')
        setHealth(nextHealth)
        storeHealthSnapshot(nextHealth)
      } catch {
        setHealth((current) => current || fallbackHealth)
      }
      healthLoadTimeoutRef.current = null
    }, 1500)

    healthLoadTimeoutRef.current = timeoutId
    return () => {
      if (healthLoadTimeoutRef.current !== null) {
        window.clearTimeout(healthLoadTimeoutRef.current)
        healthLoadTimeoutRef.current = null
      }
    }
  }, [token, isLoggingIn])

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (healthLoadTimeoutRef.current !== null) {
      window.clearTimeout(healthLoadTimeoutRef.current)
      healthLoadTimeoutRef.current = null
    }
    loginChunkPrefetchRef.current = true
    void import('./backoffice/workspaces/OverviewWorkspace')
    void import('./backoffice/workspaces/ContabilidadWorkspace')
    void import('./AuthenticatedApp')
    setIsLoggingIn(true)
    setLoginError(null)
    try {
      const response = await apiRequest<LoginResponse>('/api/v1/auth/login/', {
        method: 'POST',
        body: { username, password },
      })
      const loadedAt = new Date().toISOString()
      localStorage.setItem(TOKEN_STORAGE_KEY, response.token)
      storeCurrentUser(response.user)

      if (response.bootstrap?.overview) {
        const storedOverviewSnapshot = readStoredOverviewSnapshot(response.user)
        storeOverviewSnapshot(response.user, {
          dashboard: response.bootstrap.overview.dashboard ?? null,
          manualSummary: response.bootstrap.overview.manual_summary ?? storedOverviewSnapshot?.manualSummary ?? null,
          lastLoadedAt: loadedAt,
        })
      }

      if (response.bootstrap?.control) {
        storeControlSnapshot(response.user, response.bootstrap.control, loadedAt)
      }

      if (readStoredHealth()) {
        setHealth(readStoredHealth() || unknownHealth)
      }

      setToken(response.token)
      setPassword('')
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'No se pudo autenticar.')
    } finally {
      setIsLoggingIn(false)
    }
  }

  if (!token) {
    return (
      <main className="login-page">
        <section className="login-visual">
          <img
            src={heroImage}
            alt="Universo LeaseManager"
            className="login-image"
            loading="eager"
            decoding="async"
            fetchPriority="low"
          />
          <div className="login-copy">
            <p className="section-tag">LeaseManager</p>
            <h1>Patrimonio y operación sobre la base viva del greenfield.</h1>
            <p>Ingresa para seguir la cartera sin volver al legacy.</p>
          </div>
        </section>
        <section className="login-panel">
          <div className="section-heading">
            <div>
              <h2>Continuar sesión</h2>
              <p>{!API_BASE_URL ? 'El frontend ya está arriba, pero todavía no tiene un backend configurado para este entorno.' : 'Usa las credenciales del backend canónico.'}</p>
            </div>
          </div>
          <form className="login-form" onSubmit={handleLogin}>
            <label>
              <span>Usuario</span>
              <input value={username} onChange={(event) => setUsername(event.target.value)} disabled={!API_BASE_URL} />
            </label>
            <label>
              <span>Contraseña</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={!API_BASE_URL}
              />
            </label>
            <button type="submit" className="button-primary" disabled={isLoggingIn || !API_BASE_URL}>
              {isLoggingIn ? 'Ingresando...' : 'Ingresar'}
            </button>
          </form>
          {!API_BASE_URL ? <p className="form-message error-text">Falta conectar el backend canónico para este entorno. Configura VITE_API_BASE_URL para habilitar el acceso.</p> : null}
          {loginError ? <p className="form-message error-text">{loginError}</p> : null}
          <div className="metric-grid compact-grid">
            <Metric label="API" value={health.status} tone={toneFor(health.status)} />
            <Metric label="Base de datos" value={health.services.database.status} tone={toneFor(health.services.database.status)} />
            <Metric label="Redis" value={health.services.redis.status} tone={toneFor(health.services.redis.status)} />
          </div>
        </section>
      </main>
    )
  }

  return (
    <Suspense fallback={<main className="workspace-shell"><div className="empty-state">Cargando backoffice...</div></main>}>
      <AuthenticatedApp />
    </Suspense>
  )
}
