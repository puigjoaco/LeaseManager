import { useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import heroImage from './assets/hero.png'
import './App.css'

type HealthPayload = {
  service: string
  status: string
  environment: string
  services: Record<string, { status: string }>
}

type CurrentUser = {
  id: number
  username: string
  email: string
  display_name: string
  default_role_code: string
  assignments: Array<{ role: string; scope: string | null; is_primary: boolean }>
}

type LoginResponse = { token: string; user: CurrentUser }

type Dashboard = {
  propiedades_activas: number
  contratos_vigentes: number
  pagos_pendientes: number
  pagos_atrasados: number
  resoluciones_manuales_abiertas: number
  dtes_borrador: number
  mensajes_preparados: number
}

type ManualSummary = {
  total: number
  categorias: Array<{ category: string; total: number }>
}

type Socio = { id: number; nombre: string; rut: string; email: string; telefono: string; activo: boolean }
type Empresa = { id: number; razon_social: string; rut: string; estado: string; participaciones_detail: unknown[] }
type Comunidad = {
  id: number
  nombre: string
  estado: string
  participaciones_detail: unknown[]
  representacion_vigente: { modo_representacion: string; socio_representante_nombre: string } | null
}
type Propiedad = {
  id: number
  codigo_propiedad: string
  direccion: string
  comuna: string
  region: string
  owner_tipo: string
  owner_display: string
  estado: string
}
type Cuenta = {
  id: number
  institucion: string
  numero_cuenta: string
  owner_tipo: string
  owner_display: string
  moneda_operativa: string
  estado_operativo: string
}
type Identidad = {
  id: number
  canal: string
  remitente_visible: string
  direccion_o_numero: string
  owner_tipo: string
  owner_display: string
  estado: string
}
type Mandato = {
  id: number
  propiedad_codigo: string
  propietario_display: string
  administrador_operativo_display: string
  recaudador_display: string
  entidad_facturadora_display: string | null
  cuenta_recaudadora_display: string
  tipo_relacion_operativa: string
  estado: string
}

type ViewKey = 'overview' | 'patrimonio' | 'operacion'
type Tone = 'neutral' | 'positive' | 'warning' | 'danger'
type Column<T> = { label: string; render: (row: T) => ReactNode }

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const TOKEN_STORAGE_KEY = 'leasemanager.auth.token'
const fallbackHealth: HealthPayload = {
  service: 'leasemanager-api',
  status: 'unreachable',
  environment: 'unknown',
  services: { database: { status: 'down' }, redis: { status: 'down' } },
}

class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function apiRequest<T>(
  path: string,
  options: { method?: 'GET' | 'POST'; token?: string | null; body?: unknown } = {},
) {
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

function toneFor(value: string): Tone {
  const normalized = value.toLowerCase()
  if (['activa', 'activo', 'aprobado', 'up', 'ok'].some((item) => normalized.includes(item))) return 'positive'
  if (['pendiente', 'preparado', 'borrador', 'futuro'].some((item) => normalized.includes(item))) return 'warning'
  if (['atrasado', 'bloqueado', 'down', 'unreachable'].some((item) => normalized.includes(item))) return 'danger'
  return 'neutral'
}

function matches(search: string, values: Array<string | number | boolean | null | undefined>) {
  if (!search) return true
  return values.some((value) => String(value ?? '').toLowerCase().includes(search))
}

function count(value: number | undefined) {
  return new Intl.NumberFormat('es-CL').format(value ?? 0)
}

function stamp(value: string | null) {
  if (!value) return 'Sin refresco reciente'
  return new Intl.DateTimeFormat('es-CL', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

function Badge({ label, tone = 'neutral' }: { label: string; tone?: Tone }) {
  return <span className={`status-badge tone-${tone}`}>{label}</span>
}

function Metric({ label, value, tone = 'neutral' }: { label: string; value: string; tone?: Tone }) {
  return (
    <article className={`metric-tile metric-${tone}`}>
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value}</strong>
    </article>
  )
}

function TableBlock<T extends { id: number }>({
  title,
  subtitle,
  rows,
  columns,
  empty,
}: {
  title: string
  subtitle: string
  rows: T[]
  columns: Column<T>[]
  empty: string
}) {
  return (
    <section className="data-block">
      <div className="section-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        <Badge label={`${count(rows.length)} registros`} />
      </div>
      {rows.length === 0 ? (
        <div className="empty-state">{empty}</div>
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>{columns.map((column) => <th key={column.label}>{column.label}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  {columns.map((column) => (
                    <td key={column.label}>{column.render(row)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY))
  const [health, setHealth] = useState<HealthPayload>(fallbackHealth)
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [manualSummary, setManualSummary] = useState<ManualSummary | null>(null)
  const [socios, setSocios] = useState<Socio[]>([])
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [comunidades, setComunidades] = useState<Comunidad[]>([])
  const [propiedades, setPropiedades] = useState<Propiedad[]>([])
  const [cuentas, setCuentas] = useState<Cuenta[]>([])
  const [identidades, setIdentidades] = useState<Identidad[]>([])
  const [mandatos, setMandatos] = useState<Mandato[]>([])
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [workspaceError, setWorkspaceError] = useState<string | null>(null)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastLoadedAt, setLastLoadedAt] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<ViewKey>('overview')
  const [searchText, setSearchText] = useState('')

  async function loadHealth() {
    try {
      setHealth(await apiRequest<HealthPayload>('/api/v1/health/'))
    } catch {
      setHealth(fallbackHealth)
    }
  }

  async function loadWorkspace(activeToken: string) {
    setIsRefreshing(true)
    setWorkspaceError(null)
    try {
      const [
        me,
        dashboardPayload,
        manualPayload,
        sociosPayload,
        empresasPayload,
        comunidadesPayload,
        propiedadesPayload,
        cuentasPayload,
        identidadesPayload,
        mandatosPayload,
      ] = await Promise.all([
        apiRequest<CurrentUser>('/api/v1/auth/me/', { token: activeToken }),
        apiRequest<Dashboard>('/api/v1/reporting/dashboard/operativo/', { token: activeToken }),
        apiRequest<ManualSummary>('/api/v1/reporting/migracion/resoluciones-manuales/?status=open', {
          token: activeToken,
        }),
        apiRequest<Socio[]>('/api/v1/patrimonio/socios/', { token: activeToken }),
        apiRequest<Empresa[]>('/api/v1/patrimonio/empresas/', { token: activeToken }),
        apiRequest<Comunidad[]>('/api/v1/patrimonio/comunidades/', { token: activeToken }),
        apiRequest<Propiedad[]>('/api/v1/patrimonio/propiedades/', { token: activeToken }),
        apiRequest<Cuenta[]>('/api/v1/operacion/cuentas-recaudadoras/', { token: activeToken }),
        apiRequest<Identidad[]>('/api/v1/operacion/identidades-envio/', { token: activeToken }),
        apiRequest<Mandato[]>('/api/v1/operacion/mandatos/', { token: activeToken }),
      ])
      setCurrentUser(me)
      setDashboard(dashboardPayload)
      setManualSummary(manualPayload)
      setSocios(sociosPayload)
      setEmpresas(empresasPayload)
      setComunidades(comunidadesPayload)
      setPropiedades(propiedadesPayload)
      setCuentas(cuentasPayload)
      setIdentidades(identidadesPayload)
      setMandatos(mandatosPayload)
      setLastLoadedAt(new Date().toISOString())
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        localStorage.removeItem(TOKEN_STORAGE_KEY)
        setToken(null)
        setCurrentUser(null)
        setWorkspaceError('La sesión expiró. Ingresa nuevamente.')
        return
      }
      setWorkspaceError(error instanceof Error ? error.message : 'No se pudo cargar el workspace.')
    } finally {
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    void loadHealth()
  }, [])

  useEffect(() => {
    if (!token) {
      setCurrentUser(null)
      return
    }
    void loadWorkspace(token)
  }, [token])

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsLoggingIn(true)
    setLoginError(null)
    try {
      const response = await apiRequest<LoginResponse>('/api/v1/auth/login/', {
        method: 'POST',
        body: { username, password },
      })
      localStorage.setItem(TOKEN_STORAGE_KEY, response.token)
      setToken(response.token)
      setCurrentUser(response.user)
      setPassword('')
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'No se pudo autenticar.')
    } finally {
      setIsLoggingIn(false)
    }
  }

  async function handleLogout() {
    if (token) {
      try {
        await apiRequest<void>('/api/v1/auth/logout/', { method: 'POST', token })
      } catch {
        // Ignore logout errors and clear local state anyway.
      }
    }
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    setToken(null)
    setCurrentUser(null)
    setDashboard(null)
    setManualSummary(null)
    setSocios([])
    setEmpresas([])
    setComunidades([])
    setPropiedades([])
    setCuentas([])
    setIdentidades([])
    setMandatos([])
  }

  const normalizedSearch = searchText.trim().toLowerCase()
  const filteredSocios = useMemo(
    () => socios.filter((item) => matches(normalizedSearch, [item.nombre, item.rut, item.email, item.telefono])),
    [socios, normalizedSearch],
  )
  const filteredEmpresas = useMemo(
    () => empresas.filter((item) => matches(normalizedSearch, [item.razon_social, item.rut, item.estado])),
    [empresas, normalizedSearch],
  )
  const filteredComunidades = useMemo(
    () =>
      comunidades.filter((item) =>
        matches(normalizedSearch, [item.nombre, item.estado, item.representacion_vigente?.socio_representante_nombre]),
      ),
    [comunidades, normalizedSearch],
  )
  const filteredPropiedades = useMemo(
    () =>
      propiedades.filter((item) =>
        matches(normalizedSearch, [
          item.codigo_propiedad,
          item.direccion,
          item.comuna,
          item.region,
          item.owner_display,
          item.estado,
        ]),
      ),
    [propiedades, normalizedSearch],
  )
  const filteredCuentas = useMemo(
    () =>
      cuentas.filter((item) =>
        matches(normalizedSearch, [
          item.numero_cuenta,
          item.institucion,
          item.owner_display,
          item.owner_tipo,
          item.estado_operativo,
        ]),
      ),
    [cuentas, normalizedSearch],
  )
  const filteredIdentidades = useMemo(
    () =>
      identidades.filter((item) =>
        matches(normalizedSearch, [
          item.remitente_visible,
          item.canal,
          item.owner_display,
          item.direccion_o_numero,
          item.estado,
        ]),
      ),
    [identidades, normalizedSearch],
  )
  const filteredMandatos = useMemo(
    () =>
      mandatos.filter((item) =>
        matches(normalizedSearch, [
          item.propiedad_codigo,
          item.propietario_display,
          item.administrador_operativo_display,
          item.recaudador_display,
          item.entidad_facturadora_display,
          item.cuenta_recaudadora_display,
          item.tipo_relacion_operativa,
          item.estado,
        ]),
      ),
    [mandatos, normalizedSearch],
  )

  if (!token) {
    return (
      <main className="login-page">
        <section className="login-visual">
          <img src={heroImage} alt="Universo LeaseManager" className="login-image" />
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
              <p>Usa las credenciales del backend canónico.</p>
            </div>
          </div>
          <form className="login-form" onSubmit={handleLogin}>
            <label>
              <span>Usuario</span>
              <input value={username} onChange={(event) => setUsername(event.target.value)} />
            </label>
            <label>
              <span>Contraseña</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <button type="submit" className="button-primary" disabled={isLoggingIn}>
              {isLoggingIn ? 'Ingresando...' : 'Ingresar'}
            </button>
          </form>
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
    <main className="workspace-shell">
      <header className="workspace-header">
        <div>
          <p className="section-tag">Backoffice</p>
          <h1>LeaseManager</h1>
          <p className="header-copy">
            {currentUser ? `${currentUser.display_name || currentUser.username} · ${currentUser.default_role_code}` : 'Cargando sesión...'}
          </p>
        </div>
        <div className="header-actions">
          <span className="refresh-label">{stamp(lastLoadedAt)}</span>
          <button type="button" className="button-secondary" onClick={() => token && void loadWorkspace(token)} disabled={isRefreshing}>
            {isRefreshing ? 'Actualizando...' : 'Actualizar'}
          </button>
          <button type="button" className="button-ghost" onClick={() => void handleLogout()}>
            Salir
          </button>
        </div>
      </header>

      <section className="tab-strip">
        {(['overview', 'patrimonio', 'operacion'] as ViewKey[]).map((view) => (
          <button
            key={view}
            type="button"
            className={activeView === view ? 'tab-button is-active' : 'tab-button'}
            onClick={() => setActiveView(view)}
          >
            {view === 'overview' ? 'Resumen' : view === 'patrimonio' ? 'Patrimonio' : 'Operación'}
          </button>
        ))}
      </section>

      {workspaceError ? <div className="banner-error">{workspaceError}</div> : null}

      {activeView === 'overview' ? (
        <>
          <section className="metric-grid">
            <Metric label="Propiedades activas" value={count(dashboard?.propiedades_activas)} tone="positive" />
            <Metric label="Contratos vigentes" value={count(dashboard?.contratos_vigentes)} tone="positive" />
            <Metric label="Pagos pendientes" value={count(dashboard?.pagos_pendientes)} tone="warning" />
            <Metric label="Pagos atrasados" value={count(dashboard?.pagos_atrasados)} tone="danger" />
            <Metric label="Resoluciones abiertas" value={count(manualSummary?.total)} tone={manualSummary?.total ? 'warning' : 'positive'} />
            <Metric label="DTE borrador" value={count(dashboard?.dtes_borrador)} tone="neutral" />
          </section>

          <section className="panel-grid">
            <section className="panel">
              <div className="section-heading"><div><h2>Patrimonio</h2><p>Owners, comunidades y propiedades activas.</p></div></div>
              <div className="list-stack">
                <div className="list-row"><span>Socios</span><strong>{count(socios.length)}</strong></div>
                <div className="list-row"><span>Empresas</span><strong>{count(empresas.length)}</strong></div>
                <div className="list-row"><span>Comunidades</span><strong>{count(comunidades.length)}</strong></div>
                <div className="list-row"><span>Propiedades</span><strong>{count(propiedades.length)}</strong></div>
              </div>
            </section>
            <section className="panel">
              <div className="section-heading"><div><h2>Operación</h2><p>Cuentas, identidades y mandatos vigentes.</p></div></div>
              <div className="list-stack">
                <div className="list-row"><span>Cuentas recaudadoras</span><strong>{count(cuentas.length)}</strong></div>
                <div className="list-row"><span>Identidades de envío</span><strong>{count(identidades.length)}</strong></div>
                <div className="list-row"><span>Mandatos</span><strong>{count(mandatos.length)}</strong></div>
                <div className="list-row"><span>Mensajes preparados</span><strong>{count(dashboard?.mensajes_preparados)}</strong></div>
              </div>
            </section>
            <section className="panel">
              <div className="section-heading"><div><h2>Salud técnica</h2><p>Estado inmediato de los servicios base.</p></div></div>
              <div className="list-stack">
                <div className="list-row"><span>API</span><Badge label={health.status} tone={toneFor(health.status)} /></div>
                <div className="list-row"><span>Base de datos</span><Badge label={health.services.database.status} tone={toneFor(health.services.database.status)} /></div>
                <div className="list-row"><span>Redis</span><Badge label={health.services.redis.status} tone={toneFor(health.services.redis.status)} /></div>
              </div>
            </section>
            <section className="panel">
              <div className="section-heading"><div><h2>Cola manual</h2><p>Resumen rápido del backlog asistido.</p></div></div>
              <div className="list-stack">
                {(manualSummary?.categorias || []).slice(0, 4).map((item) => (
                  <div className="list-row" key={item.category}><span>{item.category.replaceAll('_', ' ')}</span><strong>{count(item.total)}</strong></div>
                ))}
                {!manualSummary?.categorias.length ? <div className="empty-state compact">No hay categorías abiertas.</div> : null}
              </div>
            </section>
          </section>
        </>
      ) : null}

      {activeView !== 'overview' ? (
        <section className="section-toolbar">
          <div>
            <p className="section-tag">{activeView === 'patrimonio' ? 'Patrimonio' : 'Operación'}</p>
            <h2>{activeView === 'patrimonio' ? 'Owners, comunidades y propiedades' : 'Cuentas, identidades y mandatos'}</h2>
          </div>
          <label className="search-field">
            <span>Buscar</span>
            <input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder={activeView === 'patrimonio' ? 'Nombre, RUT, dirección u owner' : 'Cuenta, owner, canal o mandato'}
            />
          </label>
        </section>
      ) : null}

      {activeView === 'patrimonio' ? (
        <>
          <TableBlock title="Socios" subtitle="Participantes y representantes activos." rows={filteredSocios} empty="No hay socios para este filtro." columns={[
            { label: 'Nombre', render: (row) => row.nombre },
            { label: 'RUT', render: (row) => row.rut },
            { label: 'Contacto', render: (row) => row.email || row.telefono || 'Sin dato' },
            { label: 'Estado', render: (row) => <Badge label={row.activo ? 'activo' : 'inactivo'} tone={row.activo ? 'positive' : 'danger'} /> },
          ]} />
          <TableBlock title="Empresas" subtitle="Owners empresariales y participaciones vigentes." rows={filteredEmpresas} empty="No hay empresas para este filtro." columns={[
            { label: 'Razón social', render: (row) => row.razon_social },
            { label: 'RUT', render: (row) => row.rut },
            { label: 'Participaciones', render: (row) => count(row.participaciones_detail.length) },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          ]} />
          <TableBlock title="Comunidades" subtitle="Representación vigente y composición comunitaria." rows={filteredComunidades} empty="No hay comunidades para este filtro." columns={[
            { label: 'Nombre', render: (row) => row.nombre },
            { label: 'Representación', render: (row) => row.representacion_vigente ? `${row.representacion_vigente.socio_representante_nombre} · ${row.representacion_vigente.modo_representacion.replaceAll('_', ' ')}` : 'Sin representación' },
            { label: 'Participaciones', render: (row) => count(row.participaciones_detail.length) },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          ]} />
          <TableBlock title="Propiedades" subtitle="Inventario elegible dentro del greenfield." rows={filteredPropiedades} empty="No hay propiedades para este filtro." columns={[
            { label: 'Código', render: (row) => row.codigo_propiedad },
            { label: 'Dirección', render: (row) => row.direccion },
            { label: 'Owner', render: (row) => `${row.owner_display} · ${row.owner_tipo.replaceAll('_', ' ')}` },
            { label: 'Ubicación', render: (row) => `${row.comuna}, ${row.region}` },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          ]} />
        </>
      ) : null}

      {activeView === 'operacion' ? (
        <>
          <TableBlock title="Cuentas recaudadoras" subtitle="Ownership bancario operativo." rows={filteredCuentas} empty="No hay cuentas para este filtro." columns={[
            { label: 'Cuenta', render: (row) => `${row.institucion} · ${row.numero_cuenta}` },
            { label: 'Owner', render: (row) => `${row.owner_display} · ${row.owner_tipo}` },
            { label: 'Moneda', render: (row) => row.moneda_operativa },
            { label: 'Estado', render: (row) => <Badge label={row.estado_operativo} tone={toneFor(row.estado_operativo)} /> },
          ]} />
          <TableBlock title="Identidades de envío" subtitle="Canales autorizados para salida." rows={filteredIdentidades} empty="No hay identidades para este filtro." columns={[
            { label: 'Remitente', render: (row) => row.remitente_visible },
            { label: 'Canal', render: (row) => row.canal.replaceAll('_', ' ') },
            { label: 'Destino', render: (row) => row.direccion_o_numero },
            { label: 'Owner', render: (row) => `${row.owner_display} · ${row.owner_tipo}` },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          ]} />
          <TableBlock title="Mandatos operativos" subtitle="Separación entre propietario, administrador, recaudador y facturadora." rows={filteredMandatos} empty="No hay mandatos para este filtro." columns={[
            { label: 'Propiedad', render: (row) => row.propiedad_codigo },
            { label: 'Propietario', render: (row) => row.propietario_display },
            { label: 'Administrador', render: (row) => row.administrador_operativo_display },
            { label: 'Recaudador', render: (row) => row.recaudador_display },
            { label: 'Facturadora', render: (row) => row.entidad_facturadora_display || 'Sin facturadora' },
            { label: 'Cuenta', render: (row) => row.cuenta_recaudadora_display },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          ]} />
        </>
      ) : null}
    </main>
  )
}

export default App
