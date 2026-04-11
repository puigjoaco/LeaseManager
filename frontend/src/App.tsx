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
  contratos_futuros: number
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
type Arrendatario = {
  id: number
  tipo_arrendatario: string
  nombre_razon_social: string
  rut: string
  email: string
  telefono: string
  domicilio_notificaciones: string
  estado_contacto: string
  whatsapp_bloqueado: boolean
}
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
  propiedad_id: number
  propiedad_codigo: string
  propietario_display: string
  administrador_operativo_display: string
  recaudador_display: string
  entidad_facturadora_display: string | null
  cuenta_recaudadora_display: string
  tipo_relacion_operativa: string
  estado: string
}

type Contrato = {
  id: number
  codigo_contrato: string
  mandato_operacion: number
  arrendatario: number
  fecha_inicio: string
  fecha_fin_vigente: string
  fecha_entrega: string | null
  dia_pago_mensual: number
  plazo_notificacion_termino_dias: number
  dias_prealerta_admin: number
  estado: string
  contrato_propiedades_detail: Array<{
    propiedad: number
    propiedad_codigo: string
    propiedad_direccion: string
    rol_en_contrato: string
  }>
  periodos_contractuales_detail: Array<{
    numero_periodo: number
    fecha_inicio: string
    fecha_fin: string
    monto_base: string
    moneda_base: string
  }>
}

type AvisoTermino = {
  id: number
  contrato: number
  fecha_efectiva: string
  causal: string
  estado: string
}

type ViewKey = 'overview' | 'patrimonio' | 'operacion' | 'contratos'
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

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function effectiveCodeFromPropertyCode(value: string) {
  const digits = value.replace(/\D/g, '')
  if (!digits) return ''
  return digits.slice(-3).padStart(3, '0')
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
  const [arrendatarios, setArrendatarios] = useState<Arrendatario[]>([])
  const [comunidades, setComunidades] = useState<Comunidad[]>([])
  const [propiedades, setPropiedades] = useState<Propiedad[]>([])
  const [cuentas, setCuentas] = useState<Cuenta[]>([])
  const [identidades, setIdentidades] = useState<Identidad[]>([])
  const [mandatos, setMandatos] = useState<Mandato[]>([])
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [avisos, setAvisos] = useState<AvisoTermino[]>([])
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [workspaceError, setWorkspaceError] = useState<string | null>(null)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastLoadedAt, setLastLoadedAt] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<ViewKey>('overview')
  const [searchText, setSearchText] = useState('')
  const [formMessage, setFormMessage] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [socioDraft, setSocioDraft] = useState({
    nombre: '',
    rut: '',
    email: '',
    telefono: '',
    domicilio: '',
    activo: true,
  })
  const [propiedadDraft, setPropiedadDraft] = useState({
    codigo_propiedad: '',
    direccion: '',
    comuna: 'Temuco',
    region: 'La Araucania',
    rol_avaluo: '',
    tipo_inmueble: 'otro',
    estado: 'borrador',
    owner_tipo: 'empresa',
    owner_id: '',
  })
  const [cuentaDraft, setCuentaDraft] = useState({
    institucion: 'Banco de Chile',
    numero_cuenta: '',
    tipo_cuenta: 'corriente',
    titular_nombre: '',
    titular_rut: '',
    moneda_operativa: 'CLP',
    estado_operativo: 'activa',
    owner_tipo: 'empresa',
    owner_id: '',
  })
  const [mandatoDraft, setMandatoDraft] = useState({
    propiedad_id: '',
    propietario_tipo: 'empresa',
    propietario_id: '',
    administrador_operativo_tipo: 'empresa',
    administrador_operativo_id: '',
    recaudador_tipo: 'empresa',
    recaudador_id: '',
    entidad_facturadora_id: '',
    cuenta_recaudadora_id: '',
    tipo_relacion_operativa: 'operacion_directa',
    autoriza_recaudacion: true,
    autoriza_facturacion: true,
    autoriza_comunicacion: true,
    vigencia_desde: todayIso(),
    vigencia_hasta: '',
    estado: 'activa',
  })
  const [arrendatarioDraft, setArrendatarioDraft] = useState({
    tipo_arrendatario: 'persona_natural',
    nombre_razon_social: '',
    rut: '',
    email: '',
    telefono: '',
    domicilio_notificaciones: '',
    estado_contacto: 'activo',
    whatsapp_bloqueado: false,
  })
  const [contratoDraft, setContratoDraft] = useState({
    codigo_contrato: '',
    mandato_operacion: '',
    arrendatario: '',
    fecha_inicio: todayIso(),
    fecha_fin_vigente: todayIso(),
    fecha_entrega: todayIso(),
    dia_pago_mensual: '5',
    plazo_notificacion_termino_dias: '60',
    dias_prealerta_admin: '90',
    estado: 'vigente',
    tiene_tramos: false,
    tiene_gastos_comunes: false,
    monto_base: '',
    moneda_base: 'CLP',
    tipo_periodo: 'base',
    origen_periodo: 'backoffice',
  })
  const [avisoDraft, setAvisoDraft] = useState({
    contrato: '',
    fecha_efectiva: todayIso(),
    causal: '',
    estado: 'registrado',
  })

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
        arrendatariosPayload,
        comunidadesPayload,
        propiedadesPayload,
        cuentasPayload,
        identidadesPayload,
        mandatosPayload,
        contratosPayload,
        avisosPayload,
      ] = await Promise.all([
        apiRequest<CurrentUser>('/api/v1/auth/me/', { token: activeToken }),
        apiRequest<Dashboard>('/api/v1/reporting/dashboard/operativo/', { token: activeToken }),
        apiRequest<ManualSummary>('/api/v1/reporting/migracion/resoluciones-manuales/?status=open', {
          token: activeToken,
        }),
        apiRequest<Socio[]>('/api/v1/patrimonio/socios/', { token: activeToken }),
        apiRequest<Empresa[]>('/api/v1/patrimonio/empresas/', { token: activeToken }),
        apiRequest<Arrendatario[]>('/api/v1/contratos/arrendatarios/', { token: activeToken }),
        apiRequest<Comunidad[]>('/api/v1/patrimonio/comunidades/', { token: activeToken }),
        apiRequest<Propiedad[]>('/api/v1/patrimonio/propiedades/', { token: activeToken }),
        apiRequest<Cuenta[]>('/api/v1/operacion/cuentas-recaudadoras/', { token: activeToken }),
        apiRequest<Identidad[]>('/api/v1/operacion/identidades-envio/', { token: activeToken }),
        apiRequest<Mandato[]>('/api/v1/operacion/mandatos/', { token: activeToken }),
        apiRequest<Contrato[]>('/api/v1/contratos/contratos/', { token: activeToken }),
        apiRequest<AvisoTermino[]>('/api/v1/contratos/avisos-termino/', { token: activeToken }),
      ])
      setCurrentUser(me)
      setDashboard(dashboardPayload)
      setManualSummary(manualPayload)
      setSocios(sociosPayload)
      setEmpresas(empresasPayload)
      setArrendatarios(arrendatariosPayload)
      setComunidades(comunidadesPayload)
      setPropiedades(propiedadesPayload)
      setCuentas(cuentasPayload)
      setIdentidades(identidadesPayload)
      setMandatos(mandatosPayload)
      setContratos(contratosPayload)
      setAvisos(avisosPayload)
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
    setArrendatarios([])
    setComunidades([])
    setPropiedades([])
    setCuentas([])
    setIdentidades([])
    setMandatos([])
    setContratos([])
    setAvisos([])
  }

  async function submitCreate(path: string, body: unknown, successMessage: string) {
    if (!token) return
    setIsSubmitting(true)
    setFormMessage(null)
    setFormError(null)
    try {
      await apiRequest(path, { method: 'POST', token, body })
      await loadWorkspace(token)
      setFormMessage(successMessage)
      return true
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'No se pudo guardar el registro.')
      return false
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleCreateSocio(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/patrimonio/socios/', socioDraft, 'Socio creado correctamente.')
    if (ok) setSocioDraft({ nombre: '', rut: '', email: '', telefono: '', domicilio: '', activo: true })
  }

  async function handleCreatePropiedad(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/patrimonio/propiedades/', {
      ...propiedadDraft,
      owner_id: Number(propiedadDraft.owner_id),
    }, 'Propiedad creada correctamente.')
    if (ok) {
      setPropiedadDraft({
        codigo_propiedad: '',
        direccion: '',
        comuna: 'Temuco',
        region: 'La Araucania',
        rol_avaluo: '',
        tipo_inmueble: 'otro',
        estado: 'borrador',
        owner_tipo: 'empresa',
        owner_id: '',
      })
    }
  }

  async function handleCreateCuenta(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/operacion/cuentas-recaudadoras/', {
      ...cuentaDraft,
      owner_id: Number(cuentaDraft.owner_id),
    }, 'Cuenta recaudadora creada correctamente.')
    if (ok) {
      setCuentaDraft({
        institucion: 'Banco de Chile',
        numero_cuenta: '',
        tipo_cuenta: 'corriente',
        titular_nombre: '',
        titular_rut: '',
        moneda_operativa: 'CLP',
        estado_operativo: 'activa',
        owner_tipo: 'empresa',
        owner_id: '',
      })
    }
  }

  async function handleCreateMandato(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/operacion/mandatos/', {
      ...mandatoDraft,
      propiedad_id: Number(mandatoDraft.propiedad_id),
      propietario_id: Number(mandatoDraft.propietario_id),
      administrador_operativo_id: Number(mandatoDraft.administrador_operativo_id),
      recaudador_id: Number(mandatoDraft.recaudador_id),
      entidad_facturadora_id: mandatoDraft.entidad_facturadora_id ? Number(mandatoDraft.entidad_facturadora_id) : null,
      cuenta_recaudadora_id: Number(mandatoDraft.cuenta_recaudadora_id),
      vigencia_hasta: mandatoDraft.vigencia_hasta || null,
    }, 'Mandato operativo creado correctamente.')
    if (ok) {
      setMandatoDraft({
        propiedad_id: '',
        propietario_tipo: 'empresa',
        propietario_id: '',
        administrador_operativo_tipo: 'empresa',
        administrador_operativo_id: '',
        recaudador_tipo: 'empresa',
        recaudador_id: '',
        entidad_facturadora_id: '',
        cuenta_recaudadora_id: '',
        tipo_relacion_operativa: 'operacion_directa',
        autoriza_recaudacion: true,
        autoriza_facturacion: true,
        autoriza_comunicacion: true,
        vigencia_desde: todayIso(),
        vigencia_hasta: '',
        estado: 'activa',
      })
    }
  }

  async function handleCreateArrendatario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/contratos/arrendatarios/', arrendatarioDraft, 'Arrendatario creado correctamente.')
    if (ok) {
      setArrendatarioDraft({
        tipo_arrendatario: 'persona_natural',
        nombre_razon_social: '',
        rut: '',
        email: '',
        telefono: '',
        domicilio_notificaciones: '',
        estado_contacto: 'activo',
        whatsapp_bloqueado: false,
      })
    }
  }

  async function handleCreateContrato(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const selectedMandate = mandatos.find((item) => item.id === Number(contratoDraft.mandato_operacion))
    if (!selectedMandate) {
      setFormError('Debes seleccionar un mandato operativo válido.')
      return
    }
    const code = effectiveCodeFromPropertyCode(selectedMandate.propiedad_codigo)
    const ok = await submitCreate('/api/v1/contratos/contratos/', {
      codigo_contrato: contratoDraft.codigo_contrato,
      mandato_operacion: Number(contratoDraft.mandato_operacion),
      arrendatario: Number(contratoDraft.arrendatario),
      fecha_inicio: contratoDraft.fecha_inicio,
      fecha_fin_vigente: contratoDraft.fecha_fin_vigente,
      fecha_entrega: contratoDraft.fecha_entrega || null,
      dia_pago_mensual: Number(contratoDraft.dia_pago_mensual),
      plazo_notificacion_termino_dias: Number(contratoDraft.plazo_notificacion_termino_dias),
      dias_prealerta_admin: Number(contratoDraft.dias_prealerta_admin),
      estado: contratoDraft.estado,
      tiene_tramos: contratoDraft.tiene_tramos,
      tiene_gastos_comunes: contratoDraft.tiene_gastos_comunes,
      snapshot_representante_legal: { source: 'frontend_backoffice' },
      contrato_propiedades: [
        {
          propiedad_id: selectedMandate.propiedad_id,
          rol_en_contrato: 'principal',
          porcentaje_distribucion_interna: '100.00',
          codigo_conciliacion_efectivo_snapshot: code,
        },
      ],
      periodos_contractuales: [
        {
          numero_periodo: 1,
          fecha_inicio: contratoDraft.fecha_inicio,
          fecha_fin: contratoDraft.fecha_fin_vigente,
          monto_base: contratoDraft.monto_base,
          moneda_base: contratoDraft.moneda_base,
          tipo_periodo: contratoDraft.tipo_periodo,
          origen_periodo: contratoDraft.origen_periodo,
        },
      ],
      codeudores_solidarios: [],
    }, 'Contrato creado correctamente.')
    if (ok) {
      setContratoDraft({
        codigo_contrato: '',
        mandato_operacion: '',
        arrendatario: '',
        fecha_inicio: todayIso(),
        fecha_fin_vigente: todayIso(),
        fecha_entrega: todayIso(),
        dia_pago_mensual: '5',
        plazo_notificacion_termino_dias: '60',
        dias_prealerta_admin: '90',
        estado: 'vigente',
        tiene_tramos: false,
        tiene_gastos_comunes: false,
        monto_base: '',
        moneda_base: 'CLP',
        tipo_periodo: 'base',
        origen_periodo: 'backoffice',
      })
    }
  }

  async function handleCreateAviso(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/contratos/avisos-termino/', {
      contrato: Number(avisoDraft.contrato),
      fecha_efectiva: avisoDraft.fecha_efectiva,
      causal: avisoDraft.causal,
      estado: avisoDraft.estado,
    }, 'Aviso de término creado correctamente.')
    if (ok) {
      setAvisoDraft({
        contrato: '',
        fecha_efectiva: todayIso(),
        causal: '',
        estado: 'registrado',
      })
    }
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
  const filteredArrendatarios = useMemo(
    () =>
      arrendatarios.filter((item) =>
        matches(normalizedSearch, [
          item.nombre_razon_social,
          item.rut,
          item.email,
          item.telefono,
          item.estado_contacto,
        ]),
      ),
    [arrendatarios, normalizedSearch],
  )
  const filteredContratos = useMemo(
    () =>
      contratos.filter((item) =>
        matches(normalizedSearch, [
          item.codigo_contrato,
          item.estado,
          item.fecha_inicio,
          item.fecha_fin_vigente,
          item.contrato_propiedades_detail.map((detail) => `${detail.propiedad_codigo} ${detail.propiedad_direccion}`).join(' '),
        ]),
      ),
    [contratos, normalizedSearch],
  )
  const filteredAvisos = useMemo(
    () =>
      avisos.filter((item) =>
        matches(normalizedSearch, [item.causal, item.estado, item.fecha_efectiva, item.contrato]),
      ),
    [avisos, normalizedSearch],
  )
  const patrimonioOwners = useMemo(
    () => [
      ...empresas.map((item) => ({ tipo: 'empresa', id: item.id, label: item.razon_social })),
      ...comunidades.map((item) => ({ tipo: 'comunidad', id: item.id, label: item.nombre })),
      ...socios.map((item) => ({ tipo: 'socio', id: item.id, label: item.nombre })),
    ],
    [empresas, comunidades, socios],
  )
  const simpleOwners = useMemo(
    () => [
      ...empresas.map((item) => ({ tipo: 'empresa', id: item.id, label: item.razon_social })),
      ...socios.map((item) => ({ tipo: 'socio', id: item.id, label: item.nombre })),
    ],
    [empresas, socios],
  )
  const arrendatarioById = useMemo(() => new Map(arrendatarios.map((item) => [item.id, item])), [arrendatarios])
  const mandatoById = useMemo(() => new Map(mandatos.map((item) => [item.id, item])), [mandatos])
  const contratoById = useMemo(() => new Map(contratos.map((item) => [item.id, item])), [contratos])

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
        {(['overview', 'patrimonio', 'operacion', 'contratos'] as ViewKey[]).map((view) => (
          <button
            key={view}
            type="button"
            className={activeView === view ? 'tab-button is-active' : 'tab-button'}
            onClick={() => setActiveView(view)}
          >
            {view === 'overview'
              ? 'Resumen'
              : view === 'patrimonio'
                ? 'Patrimonio'
                : view === 'operacion'
                  ? 'Operación'
                  : 'Contratos'}
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
            <p className="section-tag">
              {activeView === 'patrimonio' ? 'Patrimonio' : activeView === 'operacion' ? 'Operación' : 'Contratos'}
            </p>
            <h2>
              {activeView === 'patrimonio'
                ? 'Owners, comunidades y propiedades'
                : activeView === 'operacion'
                  ? 'Cuentas, identidades y mandatos'
                  : 'Arrendatarios, contratos y avisos'}
            </h2>
          </div>
          <label className="search-field">
            <span>Buscar</span>
            <input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder={
                activeView === 'patrimonio'
                  ? 'Nombre, RUT, dirección u owner'
                  : activeView === 'operacion'
                    ? 'Cuenta, owner, canal o mandato'
                    : 'Código, arrendatario, propiedad o causal'
              }
            />
          </label>
        </section>
      ) : null}

      {activeView !== 'overview' && formMessage ? <div className="banner-success">{formMessage}</div> : null}
      {activeView !== 'overview' && formError ? <div className="banner-error">{formError}</div> : null}

      {activeView === 'patrimonio' ? (
        <>
          <section className="form-grid">
            <section className="panel">
              <div className="section-heading"><div><h2>Alta rápida de socio</h2><p>Ingreso mínimo para participantes activos.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateSocio}>
                <input placeholder="Nombre completo" value={socioDraft.nombre} onChange={(event) => setSocioDraft((current) => ({ ...current, nombre: event.target.value }))} />
                <input placeholder="RUT" value={socioDraft.rut} onChange={(event) => setSocioDraft((current) => ({ ...current, rut: event.target.value }))} />
                <input placeholder="Email" value={socioDraft.email} onChange={(event) => setSocioDraft((current) => ({ ...current, email: event.target.value }))} />
                <input placeholder="Teléfono" value={socioDraft.telefono} onChange={(event) => setSocioDraft((current) => ({ ...current, telefono: event.target.value }))} />
                <input placeholder="Domicilio" value={socioDraft.domicilio} onChange={(event) => setSocioDraft((current) => ({ ...current, domicilio: event.target.value }))} />
                <label className="checkbox-row"><input type="checkbox" checked={socioDraft.activo} onChange={(event) => setSocioDraft((current) => ({ ...current, activo: event.target.checked }))} />Activo</label>
                <button type="submit" className="button-primary" disabled={isSubmitting}>Guardar socio</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Alta rápida de propiedad</h2><p>Owner explícito y código operativo desde el inicio.</p></div></div>
              <form className="entity-form" onSubmit={handleCreatePropiedad}>
                <input placeholder="Código propiedad" value={propiedadDraft.codigo_propiedad} onChange={(event) => setPropiedadDraft((current) => ({ ...current, codigo_propiedad: event.target.value }))} />
                <input placeholder="Dirección" value={propiedadDraft.direccion} onChange={(event) => setPropiedadDraft((current) => ({ ...current, direccion: event.target.value }))} />
                <input placeholder="Comuna" value={propiedadDraft.comuna} onChange={(event) => setPropiedadDraft((current) => ({ ...current, comuna: event.target.value }))} />
                <input placeholder="Región" value={propiedadDraft.region} onChange={(event) => setPropiedadDraft((current) => ({ ...current, region: event.target.value }))} />
                <input placeholder="Rol avalúo" value={propiedadDraft.rol_avaluo} onChange={(event) => setPropiedadDraft((current) => ({ ...current, rol_avaluo: event.target.value }))} />
                <select value={propiedadDraft.tipo_inmueble} onChange={(event) => setPropiedadDraft((current) => ({ ...current, tipo_inmueble: event.target.value }))}>
                  <option value="otro">Otro</option>
                  <option value="departamento">Departamento</option>
                  <option value="casa">Casa</option>
                  <option value="local">Local</option>
                  <option value="oficina">Oficina</option>
                  <option value="bodega">Bodega</option>
                  <option value="estacionamiento">Estacionamiento</option>
                </select>
                <select value={propiedadDraft.estado} onChange={(event) => setPropiedadDraft((current) => ({ ...current, estado: event.target.value }))}>
                  <option value="borrador">Borrador</option>
                  <option value="activa">Activa</option>
                  <option value="inactiva">Inactiva</option>
                </select>
                <select value={`${propiedadDraft.owner_tipo}:${propiedadDraft.owner_id}`} onChange={(event) => {
                  const [tipo, id] = event.target.value.split(':')
                  setPropiedadDraft((current) => ({ ...current, owner_tipo: tipo, owner_id: id || '' }))
                }}>
                  <option value="">Selecciona owner</option>
                  {patrimonioOwners.map((owner) => (
                    <option key={`${owner.tipo}:${owner.id}`} value={`${owner.tipo}:${owner.id}`}>{owner.label} · {owner.tipo}</option>
                  ))}
                </select>
                <button type="submit" className="button-primary" disabled={isSubmitting || !propiedadDraft.owner_id}>Guardar propiedad</button>
              </form>
            </section>
          </section>

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
          <section className="form-grid">
            <section className="panel">
              <div className="section-heading"><div><h2>Alta rápida de cuenta</h2><p>Cuenta recaudadora con owner bancario explícito.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateCuenta}>
                <input placeholder="Institución" value={cuentaDraft.institucion} onChange={(event) => setCuentaDraft((current) => ({ ...current, institucion: event.target.value }))} />
                <input placeholder="Número de cuenta" value={cuentaDraft.numero_cuenta} onChange={(event) => setCuentaDraft((current) => ({ ...current, numero_cuenta: event.target.value }))} />
                <input placeholder="Titular" value={cuentaDraft.titular_nombre} onChange={(event) => setCuentaDraft((current) => ({ ...current, titular_nombre: event.target.value }))} />
                <input placeholder="RUT titular" value={cuentaDraft.titular_rut} onChange={(event) => setCuentaDraft((current) => ({ ...current, titular_rut: event.target.value }))} />
                <select value={cuentaDraft.tipo_cuenta} onChange={(event) => setCuentaDraft((current) => ({ ...current, tipo_cuenta: event.target.value }))}>
                  <option value="corriente">Corriente</option>
                  <option value="vista">Vista</option>
                  <option value="ahorro">Ahorro</option>
                </select>
                <select value={cuentaDraft.moneda_operativa} onChange={(event) => setCuentaDraft((current) => ({ ...current, moneda_operativa: event.target.value }))}>
                  <option value="CLP">CLP</option>
                  <option value="UF">UF</option>
                </select>
                <select value={cuentaDraft.estado_operativo} onChange={(event) => setCuentaDraft((current) => ({ ...current, estado_operativo: event.target.value }))}>
                  <option value="activa">Activa</option>
                  <option value="inactiva">Inactiva</option>
                </select>
                <select value={`${cuentaDraft.owner_tipo}:${cuentaDraft.owner_id}`} onChange={(event) => {
                  const [tipo, id] = event.target.value.split(':')
                  setCuentaDraft((current) => ({ ...current, owner_tipo: tipo, owner_id: id || '' }))
                }}>
                  <option value="">Selecciona owner</option>
                  {simpleOwners.map((owner) => (
                    <option key={`${owner.tipo}:${owner.id}`} value={`${owner.tipo}:${owner.id}`}>{owner.label} · {owner.tipo}</option>
                  ))}
                </select>
                <button type="submit" className="button-primary" disabled={isSubmitting || !cuentaDraft.owner_id}>Guardar cuenta</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Alta rápida de mandato</h2><p>Separación explícita entre propietario, administrador, recaudador y facturadora.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateMandato}>
                <select value={mandatoDraft.propiedad_id} onChange={(event) => setMandatoDraft((current) => ({ ...current, propiedad_id: event.target.value }))}>
                  <option value="">Selecciona propiedad</option>
                  {propiedades.map((item) => (
                    <option key={item.id} value={item.id}>{item.codigo_propiedad} · {item.direccion}</option>
                  ))}
                </select>
                <select value={`${mandatoDraft.propietario_tipo}:${mandatoDraft.propietario_id}`} onChange={(event) => {
                  const [tipo, id] = event.target.value.split(':')
                  setMandatoDraft((current) => ({ ...current, propietario_tipo: tipo, propietario_id: id || '' }))
                }}>
                  <option value="">Selecciona propietario</option>
                  {patrimonioOwners.map((owner) => (
                    <option key={`prop-${owner.tipo}:${owner.id}`} value={`${owner.tipo}:${owner.id}`}>{owner.label} · {owner.tipo}</option>
                  ))}
                </select>
                <select value={`${mandatoDraft.administrador_operativo_tipo}:${mandatoDraft.administrador_operativo_id}`} onChange={(event) => {
                  const [tipo, id] = event.target.value.split(':')
                  setMandatoDraft((current) => ({ ...current, administrador_operativo_tipo: tipo, administrador_operativo_id: id || '' }))
                }}>
                  <option value="">Selecciona administrador</option>
                  {simpleOwners.map((owner) => (
                    <option key={`admin-${owner.tipo}:${owner.id}`} value={`${owner.tipo}:${owner.id}`}>{owner.label} · {owner.tipo}</option>
                  ))}
                </select>
                <select value={`${mandatoDraft.recaudador_tipo}:${mandatoDraft.recaudador_id}`} onChange={(event) => {
                  const [tipo, id] = event.target.value.split(':')
                  setMandatoDraft((current) => ({ ...current, recaudador_tipo: tipo, recaudador_id: id || '' }))
                }}>
                  <option value="">Selecciona recaudador</option>
                  {simpleOwners.map((owner) => (
                    <option key={`rec-${owner.tipo}:${owner.id}`} value={`${owner.tipo}:${owner.id}`}>{owner.label} · {owner.tipo}</option>
                  ))}
                </select>
                <select value={mandatoDraft.entidad_facturadora_id} onChange={(event) => setMandatoDraft((current) => ({ ...current, entidad_facturadora_id: event.target.value }))}>
                  <option value="">Sin facturadora</option>
                  {empresas.map((item) => (
                    <option key={item.id} value={item.id}>{item.razon_social}</option>
                  ))}
                </select>
                <select value={mandatoDraft.cuenta_recaudadora_id} onChange={(event) => setMandatoDraft((current) => ({ ...current, cuenta_recaudadora_id: event.target.value }))}>
                  <option value="">Selecciona cuenta</option>
                  {cuentas.map((item) => (
                    <option key={item.id} value={item.id}>{item.numero_cuenta} · {item.owner_display}</option>
                  ))}
                </select>
                <input placeholder="Tipo relación operativa" value={mandatoDraft.tipo_relacion_operativa} onChange={(event) => setMandatoDraft((current) => ({ ...current, tipo_relacion_operativa: event.target.value }))} />
                <input type="date" value={mandatoDraft.vigencia_desde} onChange={(event) => setMandatoDraft((current) => ({ ...current, vigencia_desde: event.target.value }))} />
                <select value={mandatoDraft.estado} onChange={(event) => setMandatoDraft((current) => ({ ...current, estado: event.target.value }))}>
                  <option value="activa">Activa</option>
                  <option value="inactiva">Inactiva</option>
                  <option value="borrador">Borrador</option>
                </select>
                <label className="checkbox-row"><input type="checkbox" checked={mandatoDraft.autoriza_recaudacion} onChange={(event) => setMandatoDraft((current) => ({ ...current, autoriza_recaudacion: event.target.checked }))} />Autoriza recaudación</label>
                <label className="checkbox-row"><input type="checkbox" checked={mandatoDraft.autoriza_facturacion} onChange={(event) => setMandatoDraft((current) => ({ ...current, autoriza_facturacion: event.target.checked }))} />Autoriza facturación</label>
                <label className="checkbox-row"><input type="checkbox" checked={mandatoDraft.autoriza_comunicacion} onChange={(event) => setMandatoDraft((current) => ({ ...current, autoriza_comunicacion: event.target.checked }))} />Autoriza comunicación</label>
                <button type="submit" className="button-primary" disabled={isSubmitting || !mandatoDraft.propiedad_id || !mandatoDraft.propietario_id || !mandatoDraft.administrador_operativo_id || !mandatoDraft.recaudador_id || !mandatoDraft.cuenta_recaudadora_id}>Guardar mandato</button>
              </form>
            </section>
          </section>

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

      {activeView === 'contratos' ? (
        <>
          <section className="form-grid">
            <section className="panel">
              <div className="section-heading"><div><h2>Alta rápida de arrendatario</h2><p>Base mínima para contratar sobre mandatos ya activos.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateArrendatario}>
                <select value={arrendatarioDraft.tipo_arrendatario} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, tipo_arrendatario: event.target.value }))}>
                  <option value="persona_natural">Persona natural</option>
                  <option value="empresa">Empresa</option>
                </select>
                <input placeholder="Nombre o razón social" value={arrendatarioDraft.nombre_razon_social} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, nombre_razon_social: event.target.value }))} />
                <input placeholder="RUT" value={arrendatarioDraft.rut} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, rut: event.target.value }))} />
                <input placeholder="Email" value={arrendatarioDraft.email} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, email: event.target.value }))} />
                <input placeholder="Teléfono" value={arrendatarioDraft.telefono} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, telefono: event.target.value }))} />
                <input placeholder="Domicilio de notificaciones" value={arrendatarioDraft.domicilio_notificaciones} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, domicilio_notificaciones: event.target.value }))} />
                <select value={arrendatarioDraft.estado_contacto} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, estado_contacto: event.target.value }))}>
                  <option value="pendiente">Pendiente</option>
                  <option value="activo">Activo</option>
                  <option value="inactivo">Inactivo</option>
                </select>
                <label className="checkbox-row"><input type="checkbox" checked={arrendatarioDraft.whatsapp_bloqueado} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, whatsapp_bloqueado: event.target.checked }))} />WhatsApp bloqueado</label>
                <button type="submit" className="button-primary" disabled={isSubmitting}>Guardar arrendatario</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Alta rápida de contrato</h2><p>Contrato simple con una propiedad principal y un primer período.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateContrato}>
                <input placeholder="Código contrato" value={contratoDraft.codigo_contrato} onChange={(event) => setContratoDraft((current) => ({ ...current, codigo_contrato: event.target.value }))} />
                <select value={contratoDraft.mandato_operacion} onChange={(event) => setContratoDraft((current) => ({ ...current, mandato_operacion: event.target.value }))}>
                  <option value="">Selecciona mandato</option>
                  {mandatos.map((item) => (
                    <option key={item.id} value={item.id}>{item.propiedad_codigo} · {item.propietario_display}</option>
                  ))}
                </select>
                <select value={contratoDraft.arrendatario} onChange={(event) => setContratoDraft((current) => ({ ...current, arrendatario: event.target.value }))}>
                  <option value="">Selecciona arrendatario</option>
                  {arrendatarios.map((item) => (
                    <option key={item.id} value={item.id}>{item.nombre_razon_social}</option>
                  ))}
                </select>
                <input type="date" value={contratoDraft.fecha_inicio} onChange={(event) => setContratoDraft((current) => ({ ...current, fecha_inicio: event.target.value }))} />
                <input type="date" value={contratoDraft.fecha_fin_vigente} onChange={(event) => setContratoDraft((current) => ({ ...current, fecha_fin_vigente: event.target.value }))} />
                <input type="date" value={contratoDraft.fecha_entrega} onChange={(event) => setContratoDraft((current) => ({ ...current, fecha_entrega: event.target.value }))} />
                <input placeholder="Monto base" value={contratoDraft.monto_base} onChange={(event) => setContratoDraft((current) => ({ ...current, monto_base: event.target.value }))} />
                <select value={contratoDraft.moneda_base} onChange={(event) => setContratoDraft((current) => ({ ...current, moneda_base: event.target.value }))}>
                  <option value="CLP">CLP</option>
                  <option value="UF">UF</option>
                </select>
                <select value={contratoDraft.estado} onChange={(event) => setContratoDraft((current) => ({ ...current, estado: event.target.value }))}>
                  <option value="vigente">Vigente</option>
                  <option value="pendiente_activacion">Pendiente activación</option>
                  <option value="futuro">Futuro</option>
                </select>
                <input placeholder="Día pago mensual" value={contratoDraft.dia_pago_mensual} onChange={(event) => setContratoDraft((current) => ({ ...current, dia_pago_mensual: event.target.value }))} />
                <input placeholder="Plazo aviso término" value={contratoDraft.plazo_notificacion_termino_dias} onChange={(event) => setContratoDraft((current) => ({ ...current, plazo_notificacion_termino_dias: event.target.value }))} />
                <input placeholder="Prealerta admin" value={contratoDraft.dias_prealerta_admin} onChange={(event) => setContratoDraft((current) => ({ ...current, dias_prealerta_admin: event.target.value }))} />
                <label className="checkbox-row"><input type="checkbox" checked={contratoDraft.tiene_tramos} onChange={(event) => setContratoDraft((current) => ({ ...current, tiene_tramos: event.target.checked }))} />Tiene tramos</label>
                <label className="checkbox-row"><input type="checkbox" checked={contratoDraft.tiene_gastos_comunes} onChange={(event) => setContratoDraft((current) => ({ ...current, tiene_gastos_comunes: event.target.checked }))} />Tiene gastos comunes</label>
                <button type="submit" className="button-primary" disabled={isSubmitting || !contratoDraft.codigo_contrato || !contratoDraft.mandato_operacion || !contratoDraft.arrendatario || !contratoDraft.monto_base}>Guardar contrato</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Alta rápida de aviso de término</h2><p>Base para contratos futuros y no renovación.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateAviso}>
                <select value={avisoDraft.contrato} onChange={(event) => setAvisoDraft((current) => ({ ...current, contrato: event.target.value }))}>
                  <option value="">Selecciona contrato</option>
                  {contratos.map((item) => (
                    <option key={item.id} value={item.id}>{item.codigo_contrato}</option>
                  ))}
                </select>
                <input type="date" value={avisoDraft.fecha_efectiva} onChange={(event) => setAvisoDraft((current) => ({ ...current, fecha_efectiva: event.target.value }))} />
                <input placeholder="Causal" value={avisoDraft.causal} onChange={(event) => setAvisoDraft((current) => ({ ...current, causal: event.target.value }))} />
                <select value={avisoDraft.estado} onChange={(event) => setAvisoDraft((current) => ({ ...current, estado: event.target.value }))}>
                  <option value="registrado">Registrado</option>
                  <option value="borrador">Borrador</option>
                </select>
                <button type="submit" className="button-primary" disabled={isSubmitting || !avisoDraft.contrato || !avisoDraft.causal}>Guardar aviso</button>
              </form>
            </section>
          </section>

          <TableBlock title="Arrendatarios" subtitle="Base actual de contraparte contractual." rows={filteredArrendatarios} empty="No hay arrendatarios para este filtro." columns={[
            { label: 'Nombre', render: (row) => row.nombre_razon_social },
            { label: 'RUT', render: (row) => row.rut },
            { label: 'Tipo', render: (row) => row.tipo_arrendatario.replaceAll('_', ' ') },
            { label: 'Contacto', render: (row) => row.email || row.telefono || 'Sin dato' },
            { label: 'Estado', render: (row) => <Badge label={row.estado_contacto} tone={toneFor(row.estado_contacto)} /> },
          ]} />

          <TableBlock title="Contratos" subtitle="Contratos cargados sobre mandatos ya vigentes." rows={filteredContratos} empty="No hay contratos para este filtro." columns={[
            { label: 'Código', render: (row) => row.codigo_contrato },
            { label: 'Arrendatario', render: (row) => arrendatarioById.get(row.arrendatario)?.nombre_razon_social || row.arrendatario },
            { label: 'Mandato', render: (row) => mandatoById.get(row.mandato_operacion)?.propiedad_codigo || row.mandato_operacion },
            { label: 'Propiedad', render: (row) => row.contrato_propiedades_detail[0] ? `${row.contrato_propiedades_detail[0].propiedad_codigo} · ${row.contrato_propiedades_detail[0].propiedad_direccion}` : 'Sin propiedad' },
            { label: 'Periodo', render: (row) => `${row.fecha_inicio} → ${row.fecha_fin_vigente}` },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          ]} />

          <TableBlock title="Avisos de término" subtitle="Base para no renovación y contratos futuros." rows={filteredAvisos} empty="No hay avisos para este filtro." columns={[
            { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
            { label: 'Fecha efectiva', render: (row) => row.fecha_efectiva },
            { label: 'Causal', render: (row) => row.causal },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          ]} />
        </>
      ) : null}
    </main>
  )
}

export default App
