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

type ValorUF = {
  id: number
  fecha: string
  valor: string
  source_key: string
}

type AjusteContrato = {
  id: number
  contrato: number
  tipo_ajuste: string
  monto: string
  moneda: string
  mes_inicio: string
  mes_fin: string
  justificacion: string
  activo: boolean
}

type PagoMensual = {
  id: number
  contrato: number
  periodo_contractual: number
  mes: number
  anio: number
  monto_facturable_clp: string
  monto_calculado_clp: string
  monto_pagado_clp: string
  fecha_vencimiento: string
  fecha_deposito_banco: string | null
  fecha_deteccion_sistema: string | null
  estado_pago: string
  dias_mora: number
  codigo_conciliacion_efectivo: string
  distribuciones_detail: Array<{
    id: number
    beneficiario_tipo: string
    beneficiario_display: string
    monto_devengado_clp: string
    monto_conciliado_clp: string
    monto_facturable_clp: string
    requiere_dte: boolean
  }>
}

type Garantia = {
  id: number
  contrato: number
  monto_pactado: string
  monto_recibido: string
  monto_devuelto: string
  monto_aplicado: string
  saldo_vigente: string
  estado_garantia: string
}

type HistorialGarantia = {
  id: number
  garantia_contractual: number
  contrato_id: number
  tipo_movimiento: string
  monto_clp: string
  fecha: string
  justificacion: string
}

type EstadoCuenta = {
  id: number
  arrendatario: number
  resumen_operativo: {
    pagos_abiertos?: number
    pagos_atrasados?: number
    repactaciones_activas?: number
    cobranzas_residuales_activas?: number
    saldo_total_clp?: string
  }
  score_pago: number | null
  observaciones: string
}

type ConexionBancaria = {
  id: number
  cuenta_recaudadora: number
  provider_key: string
  credencial_ref: string
  scope: string
  expira_en: string | null
  estado_conexion: string
  primaria_movimientos: boolean
  primaria_saldos: boolean
  primaria_conectividad: boolean
}

type MovimientoBancario = {
  id: number
  conexion_bancaria: number
  fecha_movimiento: string
  tipo_movimiento: string
  monto: string
  descripcion_origen: string
  numero_documento: string
  saldo_reportado: string | null
  referencia: string
  transaction_id_banco: string
  estado_conciliacion: string
  pago_mensual: number | null
  codigo_cobro_residual: number | null
  notas_admin: string
}

type IngresoDesconocido = {
  id: number
  movimiento_bancario: number
  cuenta_recaudadora: number
  monto: string
  fecha_movimiento: string
  descripcion_origen: string
  estado: string
  sugerencia_asistida: { payment_candidate_ids?: number[] }
}

type RegimenTributario = {
  id: number
  codigo_regimen: string
  descripcion: string
  estado: string
}

type ConfiguracionFiscal = {
  id: number
  empresa: number
  regimen_tributario: number
  afecta_iva_arriendo: boolean
  tasa_iva: string
  aplica_ppm: boolean
  ddjj_habilitadas: string[]
  inicio_ejercicio: string
  moneda_funcional: string
  estado: string
}

type CuentaContable = {
  id: number
  empresa: number
  plan_cuentas_version: string
  codigo: string
  nombre: string
  naturaleza: string
  nivel: number
  padre: number | null
  estado: string
  es_control_obligatoria: boolean
}

type ReglaContable = {
  id: number
  empresa: number
  evento_tipo: string
  plan_cuentas_version: string
  criterio_cargo: string
  criterio_abono: string
  vigencia_desde: string
  vigencia_hasta: string | null
  estado: string
}

type MatrizRegla = {
  id: number
  regla_contable: number
  cuenta_debe: number
  cuenta_haber: number
  condicion_impuesto: string
  estado: string
}

type EventoContable = {
  id: number
  empresa: number | null
  evento_tipo: string
  entidad_origen_tipo: string
  entidad_origen_id: string
  fecha_operativa: string
  moneda: string
  monto_base: string
  payload_resumen: Record<string, unknown>
  idempotency_key: string
  estado_contable: string
}

type AsientoContable = {
  id: number
  evento_contable: number
  fecha_contable: string
  periodo_contable: string
  estado: string
  debe_total: string
  haber_total: string
  moneda_funcional: string
  hash_integridad: string
  movimientos: Array<{
    id: number
    cuenta_contable: number
    tipo_movimiento: string
    monto: string
    glosa: string
  }>
}

type ObligacionMensual = {
  id: number
  empresa: number
  anio: number
  mes: number
  obligacion_tipo: string
  base_imponible: string
  monto_calculado: string
  estado_preparacion: string
}

type CierreMensual = {
  id: number
  empresa: number
  anio: number
  mes: number
  estado: string
  fecha_preparacion: string | null
  fecha_aprobacion: string | null
  resumen_obligaciones: Record<string, unknown>
}

type ViewKey =
  | 'overview'
  | 'patrimonio'
  | 'operacion'
  | 'contratos'
  | 'cobranza'
  | 'conciliacion'
  | 'contabilidad'
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
  const [valoresUf, setValoresUf] = useState<ValorUF[]>([])
  const [ajustes, setAjustes] = useState<AjusteContrato[]>([])
  const [pagos, setPagos] = useState<PagoMensual[]>([])
  const [garantias, setGarantias] = useState<Garantia[]>([])
  const [historialGarantias, setHistorialGarantias] = useState<HistorialGarantia[]>([])
  const [estadosCuenta, setEstadosCuenta] = useState<EstadoCuenta[]>([])
  const [conexionesBancarias, setConexionesBancarias] = useState<ConexionBancaria[]>([])
  const [movimientosBancarios, setMovimientosBancarios] = useState<MovimientoBancario[]>([])
  const [ingresosDesconocidos, setIngresosDesconocidos] = useState<IngresoDesconocido[]>([])
  const [regimenesTributarios, setRegimenesTributarios] = useState<RegimenTributario[]>([])
  const [configuracionesFiscales, setConfiguracionesFiscales] = useState<ConfiguracionFiscal[]>([])
  const [cuentasContables, setCuentasContables] = useState<CuentaContable[]>([])
  const [reglasContables, setReglasContables] = useState<ReglaContable[]>([])
  const [matricesReglas, setMatricesReglas] = useState<MatrizRegla[]>([])
  const [eventosContables, setEventosContables] = useState<EventoContable[]>([])
  const [asientosContables, setAsientosContables] = useState<AsientoContable[]>([])
  const [obligacionesMensuales, setObligacionesMensuales] = useState<ObligacionMensual[]>([])
  const [cierresMensuales, setCierresMensuales] = useState<CierreMensual[]>([])
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
  const [ufDraft, setUfDraft] = useState({
    fecha: todayIso(),
    valor: '',
    source_key: 'manual',
  })
  const [ajusteDraft, setAjusteDraft] = useState({
    contrato: '',
    tipo_ajuste: 'cargo_extra',
    monto: '',
    moneda: 'CLP',
    mes_inicio: todayIso(),
    mes_fin: todayIso(),
    justificacion: '',
    activo: true,
  })
  const [pagoDraft, setPagoDraft] = useState({
    contrato_id: '',
    anio: '2026',
    mes: '4',
  })
  const [garantiaDraft, setGarantiaDraft] = useState({
    contrato: '',
    monto_pactado: '',
  })
  const [garantiaMovimientoDraft, setGarantiaMovimientoDraft] = useState({
    garantiaId: '',
    tipo_movimiento: 'deposito',
    monto_clp: '',
    fecha: todayIso(),
    justificacion: '',
  })
  const [estadoCuentaDraft, setEstadoCuentaDraft] = useState({
    arrendatario_id: '',
  })
  const [conexionDraft, setConexionDraft] = useState({
    cuenta_recaudadora: '',
    provider_key: 'banco_de_chile',
    credencial_ref: 'local-test',
    scope: 'movimientos',
    expira_en: '',
    estado_conexion: 'activa',
    primaria_movimientos: true,
    primaria_saldos: false,
    primaria_conectividad: false,
  })
  const [movimientoDraft, setMovimientoDraft] = useState({
    conexion_bancaria: '',
    fecha_movimiento: todayIso(),
    tipo_movimiento: 'abono',
    monto: '',
    descripcion_origen: '',
    numero_documento: '',
    saldo_reportado: '',
    referencia: '',
    transaction_id_banco: '',
    notas_admin: '',
  })
  const [configFiscalDraft, setConfigFiscalDraft] = useState({
    empresa: '',
    regimen_tributario: '',
    afecta_iva_arriendo: false,
    tasa_iva: '0.00',
    aplica_ppm: true,
    inicio_ejercicio: '2026-01-01',
    moneda_funcional: 'CLP',
    estado: 'activa',
  })
  const [cuentaContableDraft, setCuentaContableDraft] = useState({
    empresa: '',
    plan_cuentas_version: 'v1',
    codigo: '',
    nombre: '',
    naturaleza: 'deudora',
    nivel: '1',
    padre: '',
    estado: 'activa',
    es_control_obligatoria: false,
  })
  const [reglaContableDraft, setReglaContableDraft] = useState({
    empresa: '',
    evento_tipo: 'PagoConciliadoArriendo',
    plan_cuentas_version: 'v1',
    criterio_cargo: '',
    criterio_abono: '',
    vigencia_desde: todayIso(),
    vigencia_hasta: '',
    estado: 'activa',
  })
  const [matrizDraft, setMatrizDraft] = useState({
    regla_contable: '',
    cuenta_debe: '',
    cuenta_haber: '',
    condicion_impuesto: '',
    estado: 'activa',
  })
  const [eventoContableDraft, setEventoContableDraft] = useState({
    empresa: '',
    evento_tipo: 'PagoConciliadoArriendo',
    entidad_origen_tipo: 'manual',
    entidad_origen_id: '',
    fecha_operativa: todayIso(),
    moneda: 'CLP',
    monto_base: '',
    payload_resumen: '{}',
    idempotency_key: '',
  })
  const [cierreDraft, setCierreDraft] = useState({
    empresa_id: '',
    anio: '2026',
    mes: '5',
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
        valoresUfPayload,
        ajustesPayload,
        pagosPayload,
        garantiasPayload,
        historialGarantiasPayload,
        estadosCuentaPayload,
        conexionesPayload,
        movimientosPayload,
        ingresosPayload,
        regimenesPayload,
        configuracionesPayload,
        cuentasContablesPayload,
        reglasPayload,
        matricesPayload,
        eventosPayload,
        asientosPayload,
        obligacionesPayload,
        cierresPayload,
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
        apiRequest<ValorUF[]>('/api/v1/cobranza/valores-uf/', { token: activeToken }),
        apiRequest<AjusteContrato[]>('/api/v1/cobranza/ajustes-contrato/', { token: activeToken }),
        apiRequest<PagoMensual[]>('/api/v1/cobranza/pagos-mensuales/', { token: activeToken }),
        apiRequest<Garantia[]>('/api/v1/cobranza/garantias/', { token: activeToken }),
        apiRequest<HistorialGarantia[]>('/api/v1/cobranza/historial-garantias/', { token: activeToken }),
        apiRequest<EstadoCuenta[]>('/api/v1/cobranza/estados-cuenta/', { token: activeToken }),
        apiRequest<ConexionBancaria[]>('/api/v1/conciliacion/conexiones-bancarias/', { token: activeToken }),
        apiRequest<MovimientoBancario[]>('/api/v1/conciliacion/movimientos/', { token: activeToken }),
        apiRequest<IngresoDesconocido[]>('/api/v1/conciliacion/ingresos-desconocidos/', { token: activeToken }),
        apiRequest<RegimenTributario[]>('/api/v1/contabilidad/regimenes-tributarios/', { token: activeToken }),
        apiRequest<ConfiguracionFiscal[]>('/api/v1/contabilidad/configuraciones-fiscales/', { token: activeToken }),
        apiRequest<CuentaContable[]>('/api/v1/contabilidad/cuentas-contables/', { token: activeToken }),
        apiRequest<ReglaContable[]>('/api/v1/contabilidad/reglas-contables/', { token: activeToken }),
        apiRequest<MatrizRegla[]>('/api/v1/contabilidad/matriz-reglas/', { token: activeToken }),
        apiRequest<EventoContable[]>('/api/v1/contabilidad/eventos-contables/', { token: activeToken }),
        apiRequest<AsientoContable[]>('/api/v1/contabilidad/asientos-contables/', { token: activeToken }),
        apiRequest<ObligacionMensual[]>('/api/v1/contabilidad/obligaciones-mensuales/', { token: activeToken }),
        apiRequest<CierreMensual[]>('/api/v1/contabilidad/cierres-mensuales/', { token: activeToken }),
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
      setValoresUf(valoresUfPayload)
      setAjustes(ajustesPayload)
      setPagos(pagosPayload)
      setGarantias(garantiasPayload)
      setHistorialGarantias(historialGarantiasPayload)
      setEstadosCuenta(estadosCuentaPayload)
      setConexionesBancarias(conexionesPayload)
      setMovimientosBancarios(movimientosPayload)
      setIngresosDesconocidos(ingresosPayload)
      setRegimenesTributarios(regimenesPayload)
      setConfiguracionesFiscales(configuracionesPayload)
      setCuentasContables(cuentasContablesPayload)
      setReglasContables(reglasPayload)
      setMatricesReglas(matricesPayload)
      setEventosContables(eventosPayload)
      setAsientosContables(asientosPayload)
      setObligacionesMensuales(obligacionesPayload)
      setCierresMensuales(cierresPayload)
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
    setValoresUf([])
    setAjustes([])
    setPagos([])
    setGarantias([])
    setHistorialGarantias([])
    setEstadosCuenta([])
    setConexionesBancarias([])
    setMovimientosBancarios([])
    setIngresosDesconocidos([])
    setRegimenesTributarios([])
    setConfiguracionesFiscales([])
    setCuentasContables([])
    setReglasContables([])
    setMatricesReglas([])
    setEventosContables([])
    setAsientosContables([])
    setObligacionesMensuales([])
    setCierresMensuales([])
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

  async function handleCreateUf(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/cobranza/valores-uf/', ufDraft, 'Valor UF creado correctamente.')
    if (ok) {
      setUfDraft({ fecha: todayIso(), valor: '', source_key: 'manual' })
    }
  }

  async function handleCreateAjuste(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/cobranza/ajustes-contrato/', {
      ...ajusteDraft,
      contrato: Number(ajusteDraft.contrato),
    }, 'Ajuste creado correctamente.')
    if (ok) {
      setAjusteDraft({
        contrato: '',
        tipo_ajuste: 'cargo_extra',
        monto: '',
        moneda: 'CLP',
        mes_inicio: todayIso(),
        mes_fin: todayIso(),
        justificacion: '',
        activo: true,
      })
    }
  }

  async function handleGeneratePago(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/cobranza/pagos-mensuales/generar/', {
      contrato_id: Number(pagoDraft.contrato_id),
      anio: Number(pagoDraft.anio),
      mes: Number(pagoDraft.mes),
    }, 'Pago mensual generado correctamente.')
    if (ok) {
      setPagoDraft({ contrato_id: '', anio: '2026', mes: '4' })
    }
  }

  async function handleCreateGarantia(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/cobranza/garantias/', {
      contrato: Number(garantiaDraft.contrato),
      monto_pactado: garantiaDraft.monto_pactado,
    }, 'Garantía creada correctamente.')
    if (ok) {
      setGarantiaDraft({ contrato: '', monto_pactado: '' })
    }
  }

  async function handleGarantiaMovimiento(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!garantiaMovimientoDraft.garantiaId) {
      setFormError('Debes seleccionar una garantía válida.')
      return
    }
    const ok = await submitCreate(`/api/v1/cobranza/garantias/${Number(garantiaMovimientoDraft.garantiaId)}/movimientos/`, {
      tipo_movimiento: garantiaMovimientoDraft.tipo_movimiento,
      monto_clp: garantiaMovimientoDraft.monto_clp,
      fecha: garantiaMovimientoDraft.fecha,
      justificacion: garantiaMovimientoDraft.justificacion,
    }, 'Movimiento de garantía registrado correctamente.')
    if (ok) {
      setGarantiaMovimientoDraft({
        garantiaId: '',
        tipo_movimiento: 'deposito',
        monto_clp: '',
        fecha: todayIso(),
        justificacion: '',
      })
    }
  }

  async function handleRebuildEstadoCuenta(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/cobranza/estados-cuenta/recalcular/', {
      arrendatario_id: Number(estadoCuentaDraft.arrendatario_id),
    }, 'Estado de cuenta recalculado correctamente.')
    if (ok) {
      setEstadoCuentaDraft({ arrendatario_id: '' })
    }
  }

  async function handleCreateConexion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/conciliacion/conexiones-bancarias/', {
      ...conexionDraft,
      cuenta_recaudadora: Number(conexionDraft.cuenta_recaudadora),
      expira_en: conexionDraft.expira_en || null,
    }, 'Conexión bancaria creada correctamente.')
    if (ok) {
      setConexionDraft({
        cuenta_recaudadora: '',
        provider_key: 'banco_de_chile',
        credencial_ref: 'local-test',
        scope: 'movimientos',
        expira_en: '',
        estado_conexion: 'activa',
        primaria_movimientos: true,
        primaria_saldos: false,
        primaria_conectividad: false,
      })
    }
  }

  async function handleCreateMovimiento(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/conciliacion/movimientos/', {
      ...movimientoDraft,
      conexion_bancaria: Number(movimientoDraft.conexion_bancaria),
      saldo_reportado: movimientoDraft.saldo_reportado || null,
    }, 'Movimiento bancario registrado correctamente.')
    if (ok) {
      setMovimientoDraft({
        conexion_bancaria: '',
        fecha_movimiento: todayIso(),
        tipo_movimiento: 'abono',
        monto: '',
        descripcion_origen: '',
        numero_documento: '',
        saldo_reportado: '',
        referencia: '',
        transaction_id_banco: '',
        notas_admin: '',
      })
    }
  }

  async function handleRetryMatch(movimientoId: number) {
    if (!token) return
    setIsSubmitting(true)
    setFormMessage(null)
    setFormError(null)
    try {
      await apiRequest(`/api/v1/conciliacion/movimientos/${movimientoId}/match-exacto/`, {
        method: 'POST',
        token,
        body: {},
      })
      await loadWorkspace(token)
      setFormMessage('Reintento de match ejecutado correctamente.')
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'No se pudo reintentar el match.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleCreateConfigFiscal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/contabilidad/configuraciones-fiscales/', {
      empresa: Number(configFiscalDraft.empresa),
      regimen_tributario: Number(configFiscalDraft.regimen_tributario),
      afecta_iva_arriendo: configFiscalDraft.afecta_iva_arriendo,
      tasa_iva: configFiscalDraft.tasa_iva,
      aplica_ppm: configFiscalDraft.aplica_ppm,
      ddjj_habilitadas: [],
      inicio_ejercicio: configFiscalDraft.inicio_ejercicio,
      moneda_funcional: configFiscalDraft.moneda_funcional,
      estado: configFiscalDraft.estado,
    }, 'Configuración fiscal creada correctamente.')
    if (ok) {
      setConfigFiscalDraft({
        empresa: '',
        regimen_tributario: '',
        afecta_iva_arriendo: false,
        tasa_iva: '0.00',
        aplica_ppm: true,
        inicio_ejercicio: '2026-01-01',
        moneda_funcional: 'CLP',
        estado: 'activa',
      })
    }
  }

  async function handleCreateCuentaContable(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/contabilidad/cuentas-contables/', {
      empresa: Number(cuentaContableDraft.empresa),
      plan_cuentas_version: cuentaContableDraft.plan_cuentas_version,
      codigo: cuentaContableDraft.codigo,
      nombre: cuentaContableDraft.nombre,
      naturaleza: cuentaContableDraft.naturaleza,
      nivel: Number(cuentaContableDraft.nivel),
      padre: cuentaContableDraft.padre ? Number(cuentaContableDraft.padre) : null,
      estado: cuentaContableDraft.estado,
      es_control_obligatoria: cuentaContableDraft.es_control_obligatoria,
    }, 'Cuenta contable creada correctamente.')
    if (ok) {
      setCuentaContableDraft({
        empresa: '',
        plan_cuentas_version: 'v1',
        codigo: '',
        nombre: '',
        naturaleza: 'deudora',
        nivel: '1',
        padre: '',
        estado: 'activa',
        es_control_obligatoria: false,
      })
    }
  }

  async function handleCreateReglaContable(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/contabilidad/reglas-contables/', {
      empresa: Number(reglaContableDraft.empresa),
      evento_tipo: reglaContableDraft.evento_tipo,
      plan_cuentas_version: reglaContableDraft.plan_cuentas_version,
      criterio_cargo: reglaContableDraft.criterio_cargo,
      criterio_abono: reglaContableDraft.criterio_abono,
      vigencia_desde: reglaContableDraft.vigencia_desde,
      vigencia_hasta: reglaContableDraft.vigencia_hasta || null,
      estado: reglaContableDraft.estado,
    }, 'Regla contable creada correctamente.')
    if (ok) {
      setReglaContableDraft({
        empresa: '',
        evento_tipo: 'PagoConciliadoArriendo',
        plan_cuentas_version: 'v1',
        criterio_cargo: '',
        criterio_abono: '',
        vigencia_desde: todayIso(),
        vigencia_hasta: '',
        estado: 'activa',
      })
    }
  }

  async function handleCreateMatriz(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/contabilidad/matriz-reglas/', {
      regla_contable: Number(matrizDraft.regla_contable),
      cuenta_debe: Number(matrizDraft.cuenta_debe),
      cuenta_haber: Number(matrizDraft.cuenta_haber),
      condicion_impuesto: matrizDraft.condicion_impuesto,
      estado: matrizDraft.estado,
    }, 'Matriz de reglas creada correctamente.')
    if (ok) {
      setMatrizDraft({
        regla_contable: '',
        cuenta_debe: '',
        cuenta_haber: '',
        condicion_impuesto: '',
        estado: 'activa',
      })
    }
  }

  async function handleCreateEventoContable(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    let payloadResumen: Record<string, unknown> = {}
    try {
      payloadResumen = JSON.parse(eventoContableDraft.payload_resumen || '{}')
    } catch {
      setFormError('payload_resumen debe ser un JSON válido.')
      return
    }
    const ok = await submitCreate('/api/v1/contabilidad/eventos-contables/', {
      empresa: Number(eventoContableDraft.empresa),
      evento_tipo: eventoContableDraft.evento_tipo,
      entidad_origen_tipo: eventoContableDraft.entidad_origen_tipo,
      entidad_origen_id: eventoContableDraft.entidad_origen_id,
      fecha_operativa: eventoContableDraft.fecha_operativa,
      moneda: eventoContableDraft.moneda,
      monto_base: eventoContableDraft.monto_base,
      payload_resumen: payloadResumen,
      idempotency_key: eventoContableDraft.idempotency_key,
    }, 'Evento contable creado correctamente.')
    if (ok) {
      setEventoContableDraft({
        empresa: '',
        evento_tipo: 'PagoConciliadoArriendo',
        entidad_origen_tipo: 'manual',
        entidad_origen_id: '',
        fecha_operativa: todayIso(),
        moneda: 'CLP',
        monto_base: '',
        payload_resumen: '{}',
        idempotency_key: '',
      })
    }
  }

  async function handlePrepareCierre(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await submitCreate('/api/v1/contabilidad/cierres-mensuales/preparar/', {
      empresa_id: Number(cierreDraft.empresa_id),
      anio: Number(cierreDraft.anio),
      mes: Number(cierreDraft.mes),
    }, 'Cierre mensual preparado correctamente.')
    if (ok) {
      setCierreDraft({ empresa_id: '', anio: '2026', mes: '5' })
    }
  }

  async function handleAccountingAction(path: string, successMessage: string) {
    if (!token) return
    setIsSubmitting(true)
    setFormMessage(null)
    setFormError(null)
    try {
      await apiRequest(path, { method: 'POST', token, body: {} })
      await loadWorkspace(token)
      setFormMessage(successMessage)
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'No se pudo ejecutar la acción contable.')
    } finally {
      setIsSubmitting(false)
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
  const filteredValoresUf = useMemo(
    () => valoresUf.filter((item) => matches(normalizedSearch, [item.fecha, item.valor, item.source_key])),
    [valoresUf, normalizedSearch],
  )
  const filteredAjustes = useMemo(
    () =>
      ajustes.filter((item) =>
        matches(normalizedSearch, [
          item.tipo_ajuste,
          item.monto,
          item.moneda,
          item.justificacion,
          item.contrato,
        ]),
      ),
    [ajustes, normalizedSearch],
  )
  const filteredPagos = useMemo(
    () =>
      pagos.filter((item) =>
        matches(normalizedSearch, [
          item.contrato,
          item.anio,
          item.mes,
          item.estado_pago,
          item.codigo_conciliacion_efectivo,
          item.monto_calculado_clp,
        ]),
      ),
    [pagos, normalizedSearch],
  )
  const filteredGarantias = useMemo(
    () =>
      garantias.filter((item) =>
        matches(normalizedSearch, [
          item.contrato,
          item.estado_garantia,
          item.monto_pactado,
          item.saldo_vigente,
        ]),
      ),
    [garantias, normalizedSearch],
  )
  const filteredHistorialGarantias = useMemo(
    () =>
      historialGarantias.filter((item) =>
        matches(normalizedSearch, [item.contrato_id, item.tipo_movimiento, item.monto_clp, item.justificacion]),
      ),
    [historialGarantias, normalizedSearch],
  )
  const filteredEstadosCuenta = useMemo(
    () =>
      estadosCuenta.filter((item) =>
        matches(normalizedSearch, [item.arrendatario, item.score_pago, item.resumen_operativo.saldo_total_clp]),
      ),
    [estadosCuenta, normalizedSearch],
  )
  const filteredConexiones = useMemo(
    () =>
      conexionesBancarias.filter((item) =>
        matches(normalizedSearch, [item.provider_key, item.credencial_ref, item.scope, item.estado_conexion, item.cuenta_recaudadora]),
      ),
    [conexionesBancarias, normalizedSearch],
  )
  const filteredMovimientos = useMemo(
    () =>
      movimientosBancarios.filter((item) =>
        matches(normalizedSearch, [
          item.fecha_movimiento,
          item.tipo_movimiento,
          item.monto,
          item.descripcion_origen,
          item.referencia,
          item.estado_conciliacion,
        ]),
      ),
    [movimientosBancarios, normalizedSearch],
  )
  const filteredIngresos = useMemo(
    () =>
      ingresosDesconocidos.filter((item) =>
        matches(normalizedSearch, [
          item.fecha_movimiento,
          item.monto,
          item.descripcion_origen,
          item.estado,
          item.sugerencia_asistida?.payment_candidate_ids?.join(','),
        ]),
      ),
    [ingresosDesconocidos, normalizedSearch],
  )
  const filteredRegimenes = useMemo(
    () => regimenesTributarios.filter((item) => matches(normalizedSearch, [item.codigo_regimen, item.descripcion, item.estado])),
    [regimenesTributarios, normalizedSearch],
  )
  const filteredConfigsFiscales = useMemo(
    () =>
      configuracionesFiscales.filter((item) =>
        matches(normalizedSearch, [item.empresa, item.moneda_funcional, item.estado, item.regimen_tributario]),
      ),
    [configuracionesFiscales, normalizedSearch],
  )
  const filteredCuentasContables = useMemo(
    () =>
      cuentasContables.filter((item) =>
        matches(normalizedSearch, [item.codigo, item.nombre, item.plan_cuentas_version, item.naturaleza, item.estado]),
      ),
    [cuentasContables, normalizedSearch],
  )
  const filteredReglasContables = useMemo(
    () =>
      reglasContables.filter((item) =>
        matches(normalizedSearch, [item.evento_tipo, item.plan_cuentas_version, item.criterio_cargo, item.criterio_abono, item.estado]),
      ),
    [reglasContables, normalizedSearch],
  )
  const filteredMatrices = useMemo(
    () =>
      matricesReglas.filter((item) =>
        matches(normalizedSearch, [item.regla_contable, item.cuenta_debe, item.cuenta_haber, item.condicion_impuesto, item.estado]),
      ),
    [matricesReglas, normalizedSearch],
  )
  const filteredEventosContables = useMemo(
    () =>
      eventosContables.filter((item) =>
        matches(normalizedSearch, [item.evento_tipo, item.entidad_origen_tipo, item.entidad_origen_id, item.monto_base, item.estado_contable]),
      ),
    [eventosContables, normalizedSearch],
  )
  const filteredAsientosContables = useMemo(
    () =>
      asientosContables.filter((item) =>
        matches(normalizedSearch, [item.evento_contable, item.periodo_contable, item.estado, item.debe_total, item.haber_total]),
      ),
    [asientosContables, normalizedSearch],
  )
  const filteredObligaciones = useMemo(
    () =>
      obligacionesMensuales.filter((item) =>
        matches(normalizedSearch, [item.empresa, item.anio, item.mes, item.obligacion_tipo, item.monto_calculado, item.estado_preparacion]),
      ),
    [obligacionesMensuales, normalizedSearch],
  )
  const filteredCierres = useMemo(
    () =>
      cierresMensuales.filter((item) =>
        matches(normalizedSearch, [item.empresa, item.anio, item.mes, item.estado]),
      ),
    [cierresMensuales, normalizedSearch],
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
  const cuentaById = useMemo(() => new Map(cuentas.map((item) => [item.id, item])), [cuentas])
  const empresaById = useMemo(() => new Map(empresas.map((item) => [item.id, item])), [empresas])
  const regimenById = useMemo(() => new Map(regimenesTributarios.map((item) => [item.id, item])), [regimenesTributarios])
  const reglaById = useMemo(() => new Map(reglasContables.map((item) => [item.id, item])), [reglasContables])
  const cuentaContableById = useMemo(() => new Map(cuentasContables.map((item) => [item.id, item])), [cuentasContables])

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
        {(['overview', 'patrimonio', 'operacion', 'contratos', 'cobranza', 'conciliacion', 'contabilidad'] as ViewKey[]).map((view) => (
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
                  : view === 'contratos'
                    ? 'Contratos'
                    : view === 'cobranza'
                      ? 'Cobranza'
                      : view === 'conciliacion'
                        ? 'Conciliación'
                        : 'Contabilidad'}
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
              {activeView === 'patrimonio'
                ? 'Patrimonio'
                : activeView === 'operacion'
                  ? 'Operación'
                  : activeView === 'contratos'
                    ? 'Contratos'
                    : activeView === 'cobranza'
                      ? 'Cobranza'
                      : activeView === 'conciliacion'
                        ? 'Conciliación'
                        : 'Contabilidad'}
            </p>
            <h2>
              {activeView === 'patrimonio'
                ? 'Owners, comunidades y propiedades'
                : activeView === 'operacion'
                  ? 'Cuentas, identidades y mandatos'
                  : activeView === 'contratos'
                    ? 'Arrendatarios, contratos y avisos'
                    : activeView === 'cobranza'
                      ? 'Pagos, UF, ajustes, garantías y estado de cuenta'
                      : activeView === 'conciliacion'
                        ? 'Conexiones, movimientos e ingresos desconocidos'
                        : 'Configuración fiscal, eventos, asientos y cierres'}
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
                    : activeView === 'contratos'
                      ? 'Código, arrendatario, propiedad o causal'
                      : activeView === 'cobranza'
                        ? 'Contrato, monto, estado, UF o garantía'
                        : activeView === 'conciliacion'
                          ? 'Movimiento, referencia, estado o ingreso desconocido'
                          : 'Empresa, evento, cuenta, cierre u obligación'
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

      {activeView === 'cobranza' ? (
        <>
          <section className="form-grid">
            <section className="panel">
              <div className="section-heading"><div><h2>Valor UF</h2><p>Registro diario mínimo para contratos en UF.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateUf}>
                <input type="date" value={ufDraft.fecha} onChange={(event) => setUfDraft((current) => ({ ...current, fecha: event.target.value }))} />
                <input placeholder="Valor UF" value={ufDraft.valor} onChange={(event) => setUfDraft((current) => ({ ...current, valor: event.target.value }))} />
                <input placeholder="Source key" value={ufDraft.source_key} onChange={(event) => setUfDraft((current) => ({ ...current, source_key: event.target.value }))} />
                <button type="submit" className="button-primary" disabled={isSubmitting || !ufDraft.valor}>Guardar UF</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Ajuste de contrato</h2><p>Cargos o descuentos vigentes por rango mensual.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateAjuste}>
                <select value={ajusteDraft.contrato} onChange={(event) => setAjusteDraft((current) => ({ ...current, contrato: event.target.value }))}>
                  <option value="">Selecciona contrato</option>
                  {contratos.map((item) => (
                    <option key={item.id} value={item.id}>{item.codigo_contrato}</option>
                  ))}
                </select>
                <input placeholder="Tipo ajuste" value={ajusteDraft.tipo_ajuste} onChange={(event) => setAjusteDraft((current) => ({ ...current, tipo_ajuste: event.target.value }))} />
                <input placeholder="Monto" value={ajusteDraft.monto} onChange={(event) => setAjusteDraft((current) => ({ ...current, monto: event.target.value }))} />
                <select value={ajusteDraft.moneda} onChange={(event) => setAjusteDraft((current) => ({ ...current, moneda: event.target.value }))}>
                  <option value="CLP">CLP</option>
                  <option value="UF">UF</option>
                </select>
                <input type="date" value={ajusteDraft.mes_inicio} onChange={(event) => setAjusteDraft((current) => ({ ...current, mes_inicio: event.target.value }))} />
                <input type="date" value={ajusteDraft.mes_fin} onChange={(event) => setAjusteDraft((current) => ({ ...current, mes_fin: event.target.value }))} />
                <input placeholder="Justificación" value={ajusteDraft.justificacion} onChange={(event) => setAjusteDraft((current) => ({ ...current, justificacion: event.target.value }))} />
                <label className="checkbox-row"><input type="checkbox" checked={ajusteDraft.activo} onChange={(event) => setAjusteDraft((current) => ({ ...current, activo: event.target.checked }))} />Activo</label>
                <button type="submit" className="button-primary" disabled={isSubmitting || !ajusteDraft.contrato || !ajusteDraft.monto}>Guardar ajuste</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Generar pago mensual</h2><p>Usa el período vigente, UF y ajustes activos del contrato.</p></div></div>
              <form className="entity-form" onSubmit={handleGeneratePago}>
                <select value={pagoDraft.contrato_id} onChange={(event) => setPagoDraft((current) => ({ ...current, contrato_id: event.target.value }))}>
                  <option value="">Selecciona contrato</option>
                  {contratos.map((item) => (
                    <option key={item.id} value={item.id}>{item.codigo_contrato}</option>
                  ))}
                </select>
                <input placeholder="Año" value={pagoDraft.anio} onChange={(event) => setPagoDraft((current) => ({ ...current, anio: event.target.value }))} />
                <input placeholder="Mes" value={pagoDraft.mes} onChange={(event) => setPagoDraft((current) => ({ ...current, mes: event.target.value }))} />
                <button type="submit" className="button-primary" disabled={isSubmitting || !pagoDraft.contrato_id}>Generar pago</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Garantía contractual</h2><p>Alta de garantía y movimientos principales.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateGarantia}>
                <select value={garantiaDraft.contrato} onChange={(event) => setGarantiaDraft((current) => ({ ...current, contrato: event.target.value }))}>
                  <option value="">Selecciona contrato</option>
                  {contratos.map((item) => (
                    <option key={item.id} value={item.id}>{item.codigo_contrato}</option>
                  ))}
                </select>
                <input placeholder="Monto pactado" value={garantiaDraft.monto_pactado} onChange={(event) => setGarantiaDraft((current) => ({ ...current, monto_pactado: event.target.value }))} />
                <button type="submit" className="button-primary" disabled={isSubmitting || !garantiaDraft.contrato || !garantiaDraft.monto_pactado}>Guardar garantía</button>
              </form>
              <form className="entity-form subform" onSubmit={handleGarantiaMovimiento}>
                <select value={garantiaMovimientoDraft.garantiaId} onChange={(event) => setGarantiaMovimientoDraft((current) => ({ ...current, garantiaId: event.target.value }))}>
                  <option value="">Selecciona garantía</option>
                  {garantias.map((item) => (
                    <option key={item.id} value={item.id}>{contratoById.get(item.contrato)?.codigo_contrato || item.contrato}</option>
                  ))}
                </select>
                <select value={garantiaMovimientoDraft.tipo_movimiento} onChange={(event) => setGarantiaMovimientoDraft((current) => ({ ...current, tipo_movimiento: event.target.value }))}>
                  <option value="deposito">Depósito</option>
                  <option value="devolucion_parcial">Devolución parcial</option>
                  <option value="devolucion_total">Devolución total</option>
                  <option value="retencion_parcial">Retención parcial</option>
                  <option value="retencion_total">Retención total</option>
                </select>
                <input placeholder="Monto movimiento" value={garantiaMovimientoDraft.monto_clp} onChange={(event) => setGarantiaMovimientoDraft((current) => ({ ...current, monto_clp: event.target.value }))} />
                <input type="date" value={garantiaMovimientoDraft.fecha} onChange={(event) => setGarantiaMovimientoDraft((current) => ({ ...current, fecha: event.target.value }))} />
                <input placeholder="Justificación" value={garantiaMovimientoDraft.justificacion} onChange={(event) => setGarantiaMovimientoDraft((current) => ({ ...current, justificacion: event.target.value }))} />
                <button type="submit" className="button-secondary" disabled={isSubmitting || !garantiaMovimientoDraft.garantiaId || !garantiaMovimientoDraft.monto_clp}>Registrar movimiento</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Estado de cuenta</h2><p>Reconstrucción del resumen operativo por arrendatario.</p></div></div>
              <form className="entity-form" onSubmit={handleRebuildEstadoCuenta}>
                <select value={estadoCuentaDraft.arrendatario_id} onChange={(event) => setEstadoCuentaDraft({ arrendatario_id: event.target.value })}>
                  <option value="">Selecciona arrendatario</option>
                  {arrendatarios.map((item) => (
                    <option key={item.id} value={item.id}>{item.nombre_razon_social}</option>
                  ))}
                </select>
                <button type="submit" className="button-primary" disabled={isSubmitting || !estadoCuentaDraft.arrendatario_id}>Recalcular estado</button>
              </form>
            </section>
          </section>

          <TableBlock title="Valores UF" subtitle="Fuente de conversión mensual para contratos en UF." rows={filteredValoresUf} empty="No hay valores UF para este filtro." columns={[
            { label: 'Fecha', render: (row) => row.fecha },
            { label: 'Valor', render: (row) => row.valor },
            { label: 'Source', render: (row) => row.source_key },
          ]} />

          <TableBlock title="Ajustes de contrato" subtitle="Ajustes activos y programados por contrato." rows={filteredAjustes} empty="No hay ajustes para este filtro." columns={[
            { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
            { label: 'Tipo', render: (row) => row.tipo_ajuste },
            { label: 'Monto', render: (row) => `${row.monto} ${row.moneda}` },
            { label: 'Rango', render: (row) => `${row.mes_inicio} → ${row.mes_fin}` },
            { label: 'Activo', render: (row) => <Badge label={row.activo ? 'activo' : 'inactivo'} tone={row.activo ? 'positive' : 'danger'} /> },
          ]} />

          <TableBlock title="Pagos mensuales" subtitle="Cobro calculado, estado y distribución económica." rows={filteredPagos} empty="No hay pagos para este filtro." columns={[
            { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
            { label: 'Periodo', render: (row) => `${row.mes}/${row.anio}` },
            { label: 'Facturable', render: (row) => row.monto_facturable_clp },
            { label: 'Calculado', render: (row) => row.monto_calculado_clp },
            { label: 'Pagado', render: (row) => row.monto_pagado_clp },
            { label: 'Estado', render: (row) => <Badge label={row.estado_pago} tone={toneFor(row.estado_pago)} /> },
          ]} />

          <TableBlock title="Garantías" subtitle="Saldos y estado actual de cada contrato." rows={filteredGarantias} empty="No hay garantías para este filtro." columns={[
            { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
            { label: 'Pactado', render: (row) => row.monto_pactado },
            { label: 'Recibido', render: (row) => row.monto_recibido },
            { label: 'Saldo', render: (row) => row.saldo_vigente },
            { label: 'Estado', render: (row) => <Badge label={row.estado_garantia} tone={toneFor(row.estado_garantia)} /> },
          ]} />

          <TableBlock title="Historial de garantías" subtitle="Movimientos auditables sobre depósitos, devoluciones y retenciones." rows={filteredHistorialGarantias} empty="No hay movimientos de garantía para este filtro." columns={[
            { label: 'Contrato', render: (row) => contratoById.get(row.contrato_id)?.codigo_contrato || row.contrato_id },
            { label: 'Tipo', render: (row) => row.tipo_movimiento },
            { label: 'Monto', render: (row) => row.monto_clp },
            { label: 'Fecha', render: (row) => row.fecha },
            { label: 'Justificación', render: (row) => row.justificacion || 'Sin nota' },
          ]} />

          <TableBlock title="Estado de cuenta" subtitle="Resumen operativo consolidado por arrendatario." rows={filteredEstadosCuenta} empty="No hay estados de cuenta para este filtro." columns={[
            { label: 'Arrendatario', render: (row) => arrendatarioById.get(row.arrendatario)?.nombre_razon_social || row.arrendatario },
            { label: 'Pagos abiertos', render: (row) => count(row.resumen_operativo.pagos_abiertos) },
            { label: 'Pagos atrasados', render: (row) => count(row.resumen_operativo.pagos_atrasados) },
            { label: 'Saldo total', render: (row) => row.resumen_operativo.saldo_total_clp || '0.00' },
            { label: 'Score', render: (row) => row.score_pago ?? 'Sin score' },
          ]} />
        </>
      ) : null}

      {activeView === 'conciliacion' ? (
        <>
          <section className="form-grid">
            <section className="panel">
              <div className="section-heading"><div><h2>Conexión bancaria</h2><p>Conecta una cuenta recaudadora al provider operativo.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateConexion}>
                <select value={conexionDraft.cuenta_recaudadora} onChange={(event) => setConexionDraft((current) => ({ ...current, cuenta_recaudadora: event.target.value }))}>
                  <option value="">Selecciona cuenta</option>
                  {cuentas.map((item) => (
                    <option key={item.id} value={item.id}>{item.numero_cuenta} · {item.owner_display}</option>
                  ))}
                </select>
                <input placeholder="Provider key" value={conexionDraft.provider_key} onChange={(event) => setConexionDraft((current) => ({ ...current, provider_key: event.target.value }))} />
                <input placeholder="Credencial ref" value={conexionDraft.credencial_ref} onChange={(event) => setConexionDraft((current) => ({ ...current, credencial_ref: event.target.value }))} />
                <input placeholder="Scope" value={conexionDraft.scope} onChange={(event) => setConexionDraft((current) => ({ ...current, scope: event.target.value }))} />
                <input type="datetime-local" value={conexionDraft.expira_en} onChange={(event) => setConexionDraft((current) => ({ ...current, expira_en: event.target.value }))} />
                <select value={conexionDraft.estado_conexion} onChange={(event) => setConexionDraft((current) => ({ ...current, estado_conexion: event.target.value }))}>
                  <option value="verificando">Verificando</option>
                  <option value="activa">Activa</option>
                  <option value="pausada">Pausada</option>
                  <option value="inactiva">Inactiva</option>
                </select>
                <label className="checkbox-row"><input type="checkbox" checked={conexionDraft.primaria_movimientos} onChange={(event) => setConexionDraft((current) => ({ ...current, primaria_movimientos: event.target.checked }))} />Primaria movimientos</label>
                <label className="checkbox-row"><input type="checkbox" checked={conexionDraft.primaria_saldos} onChange={(event) => setConexionDraft((current) => ({ ...current, primaria_saldos: event.target.checked }))} />Primaria saldos</label>
                <label className="checkbox-row"><input type="checkbox" checked={conexionDraft.primaria_conectividad} onChange={(event) => setConexionDraft((current) => ({ ...current, primaria_conectividad: event.target.checked }))} />Primaria conectividad</label>
                <button type="submit" className="button-primary" disabled={isSubmitting || !conexionDraft.cuenta_recaudadora}>Guardar conexión</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Movimiento bancario</h2><p>Ingesta manual para probar match exacto, ingreso desconocido y cargo.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateMovimiento}>
                <select value={movimientoDraft.conexion_bancaria} onChange={(event) => setMovimientoDraft((current) => ({ ...current, conexion_bancaria: event.target.value }))}>
                  <option value="">Selecciona conexión</option>
                  {conexionesBancarias.map((item) => (
                    <option key={item.id} value={item.id}>{item.provider_key} · {cuentaById.get(item.cuenta_recaudadora)?.numero_cuenta || item.cuenta_recaudadora}</option>
                  ))}
                </select>
                <input type="date" value={movimientoDraft.fecha_movimiento} onChange={(event) => setMovimientoDraft((current) => ({ ...current, fecha_movimiento: event.target.value }))} />
                <select value={movimientoDraft.tipo_movimiento} onChange={(event) => setMovimientoDraft((current) => ({ ...current, tipo_movimiento: event.target.value }))}>
                  <option value="abono">Abono</option>
                  <option value="cargo">Cargo</option>
                </select>
                <input placeholder="Monto" value={movimientoDraft.monto} onChange={(event) => setMovimientoDraft((current) => ({ ...current, monto: event.target.value }))} />
                <input placeholder="Descripción origen" value={movimientoDraft.descripcion_origen} onChange={(event) => setMovimientoDraft((current) => ({ ...current, descripcion_origen: event.target.value }))} />
                <input placeholder="Número documento" value={movimientoDraft.numero_documento} onChange={(event) => setMovimientoDraft((current) => ({ ...current, numero_documento: event.target.value }))} />
                <input placeholder="Saldo reportado" value={movimientoDraft.saldo_reportado} onChange={(event) => setMovimientoDraft((current) => ({ ...current, saldo_reportado: event.target.value }))} />
                <input placeholder="Referencia" value={movimientoDraft.referencia} onChange={(event) => setMovimientoDraft((current) => ({ ...current, referencia: event.target.value }))} />
                <input placeholder="Transaction ID banco" value={movimientoDraft.transaction_id_banco} onChange={(event) => setMovimientoDraft((current) => ({ ...current, transaction_id_banco: event.target.value }))} />
                <input placeholder="Notas admin" value={movimientoDraft.notas_admin} onChange={(event) => setMovimientoDraft((current) => ({ ...current, notas_admin: event.target.value }))} />
                <button type="submit" className="button-primary" disabled={isSubmitting || !movimientoDraft.conexion_bancaria || !movimientoDraft.monto || !movimientoDraft.descripcion_origen}>Guardar movimiento</button>
              </form>
            </section>
          </section>

          <TableBlock title="Conexiones bancarias" subtitle="Providers activos por cuenta recaudadora." rows={filteredConexiones} empty="No hay conexiones bancarias para este filtro." columns={[
            { label: 'Cuenta', render: (row) => cuentaById.get(row.cuenta_recaudadora)?.numero_cuenta || row.cuenta_recaudadora },
            { label: 'Provider', render: (row) => row.provider_key },
            { label: 'Credencial', render: (row) => row.credencial_ref },
            { label: 'Scope', render: (row) => row.scope || 'Sin scope' },
            { label: 'Estado', render: (row) => <Badge label={row.estado_conexion} tone={toneFor(row.estado_conexion)} /> },
          ]} />

          <TableBlock title="Movimientos bancarios" subtitle="Entrada importada y resultado de conciliación." rows={filteredMovimientos} empty="No hay movimientos para este filtro." columns={[
            { label: 'Fecha', render: (row) => row.fecha_movimiento },
            { label: 'Tipo', render: (row) => row.tipo_movimiento },
            { label: 'Monto', render: (row) => row.monto },
            { label: 'Descripción', render: (row) => row.descripcion_origen },
            { label: 'Referencia', render: (row) => row.referencia || 'Sin referencia' },
            { label: 'Estado', render: (row) => <Badge label={row.estado_conciliacion} tone={toneFor(row.estado_conciliacion)} /> },
            {
              label: 'Acción',
              render: (row) => (
                <button type="button" className="button-ghost inline-action" onClick={() => void handleRetryMatch(row.id)} disabled={isSubmitting}>
                  Reintentar match
                </button>
              ),
            },
          ]} />

          <TableBlock title="Ingresos desconocidos" subtitle="Abonos sin match exacto que requieren revisión." rows={filteredIngresos} empty="No hay ingresos desconocidos para este filtro." columns={[
            { label: 'Fecha', render: (row) => row.fecha_movimiento },
            { label: 'Monto', render: (row) => row.monto },
            { label: 'Cuenta', render: (row) => cuentaById.get(row.cuenta_recaudadora)?.numero_cuenta || row.cuenta_recaudadora },
            { label: 'Descripción', render: (row) => row.descripcion_origen },
            { label: 'Sugerencia', render: (row) => row.sugerencia_asistida?.payment_candidate_ids?.length ? `Pagos candidatos: ${row.sugerencia_asistida.payment_candidate_ids.join(', ')}` : 'Sin sugerencia' },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          ]} />
        </>
      ) : null}

      {activeView === 'contabilidad' ? (
        <>
          <section className="form-grid">
            <section className="panel">
              <div className="section-heading"><div><h2>Configuración fiscal</h2><p>Prerequisito para contabilización y cierre mensual oficial.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateConfigFiscal}>
                <select value={configFiscalDraft.empresa} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, empresa: event.target.value }))}>
                  <option value="">Selecciona empresa</option>
                  {empresas.map((item) => (
                    <option key={item.id} value={item.id}>{item.razon_social}</option>
                  ))}
                </select>
                <select value={configFiscalDraft.regimen_tributario} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, regimen_tributario: event.target.value }))}>
                  <option value="">Selecciona régimen</option>
                  {regimenesTributarios.map((item) => (
                    <option key={item.id} value={item.id}>{item.codigo_regimen}</option>
                  ))}
                </select>
                <input type="date" value={configFiscalDraft.inicio_ejercicio} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, inicio_ejercicio: event.target.value }))} />
                <select value={configFiscalDraft.moneda_funcional} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, moneda_funcional: event.target.value }))}>
                  <option value="CLP">CLP</option>
                  <option value="UF">UF</option>
                </select>
                <input placeholder="Tasa IVA" value={configFiscalDraft.tasa_iva} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, tasa_iva: event.target.value }))} />
                <select value={configFiscalDraft.estado} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, estado: event.target.value }))}>
                  <option value="activa">Activa</option>
                  <option value="borrador">Borrador</option>
                  <option value="inactiva">Inactiva</option>
                </select>
                <label className="checkbox-row"><input type="checkbox" checked={configFiscalDraft.afecta_iva_arriendo} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, afecta_iva_arriendo: event.target.checked }))} />Afecta IVA arriendo</label>
                <label className="checkbox-row"><input type="checkbox" checked={configFiscalDraft.aplica_ppm} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, aplica_ppm: event.target.checked }))} />Aplica PPM</label>
                <button type="submit" className="button-primary" disabled={isSubmitting || !configFiscalDraft.empresa || !configFiscalDraft.regimen_tributario}>Guardar configuración</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Cuenta contable</h2><p>Plan mínimo para reglas y asientos.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateCuentaContable}>
                <select value={cuentaContableDraft.empresa} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, empresa: event.target.value }))}>
                  <option value="">Selecciona empresa</option>
                  {empresas.map((item) => (
                    <option key={item.id} value={item.id}>{item.razon_social}</option>
                  ))}
                </select>
                <input placeholder="Versión plan" value={cuentaContableDraft.plan_cuentas_version} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, plan_cuentas_version: event.target.value }))} />
                <input placeholder="Código" value={cuentaContableDraft.codigo} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, codigo: event.target.value }))} />
                <input placeholder="Nombre" value={cuentaContableDraft.nombre} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, nombre: event.target.value }))} />
                <select value={cuentaContableDraft.naturaleza} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, naturaleza: event.target.value }))}>
                  <option value="deudora">Deudora</option>
                  <option value="acreedora">Acreedora</option>
                </select>
                <input placeholder="Nivel" value={cuentaContableDraft.nivel} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, nivel: event.target.value }))} />
                <select value={cuentaContableDraft.padre} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, padre: event.target.value }))}>
                  <option value="">Sin padre</option>
                  {cuentasContables
                    .filter((item) => !cuentaContableDraft.empresa || item.empresa === Number(cuentaContableDraft.empresa))
                    .map((item) => (
                      <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}</option>
                    ))}
                </select>
                <select value={cuentaContableDraft.estado} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, estado: event.target.value }))}>
                  <option value="activa">Activa</option>
                  <option value="inactiva">Inactiva</option>
                </select>
                <label className="checkbox-row"><input type="checkbox" checked={cuentaContableDraft.es_control_obligatoria} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, es_control_obligatoria: event.target.checked }))} />Cuenta de control obligatoria</label>
                <button type="submit" className="button-primary" disabled={isSubmitting || !cuentaContableDraft.empresa || !cuentaContableDraft.codigo || !cuentaContableDraft.nombre}>Guardar cuenta</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Regla y matriz</h2><p>Relaciona evento contable con cuentas debe/haber.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateReglaContable}>
                <select value={reglaContableDraft.empresa} onChange={(event) => setReglaContableDraft((current) => ({ ...current, empresa: event.target.value }))}>
                  <option value="">Selecciona empresa</option>
                  {empresas.map((item) => (
                    <option key={item.id} value={item.id}>{item.razon_social}</option>
                  ))}
                </select>
                <input placeholder="Evento tipo" value={reglaContableDraft.evento_tipo} onChange={(event) => setReglaContableDraft((current) => ({ ...current, evento_tipo: event.target.value }))} />
                <input placeholder="Versión plan" value={reglaContableDraft.plan_cuentas_version} onChange={(event) => setReglaContableDraft((current) => ({ ...current, plan_cuentas_version: event.target.value }))} />
                <input placeholder="Criterio cargo" value={reglaContableDraft.criterio_cargo} onChange={(event) => setReglaContableDraft((current) => ({ ...current, criterio_cargo: event.target.value }))} />
                <input placeholder="Criterio abono" value={reglaContableDraft.criterio_abono} onChange={(event) => setReglaContableDraft((current) => ({ ...current, criterio_abono: event.target.value }))} />
                <input type="date" value={reglaContableDraft.vigencia_desde} onChange={(event) => setReglaContableDraft((current) => ({ ...current, vigencia_desde: event.target.value }))} />
                <button type="submit" className="button-primary" disabled={isSubmitting || !reglaContableDraft.empresa || !reglaContableDraft.evento_tipo}>Guardar regla</button>
              </form>
              <form className="entity-form subform" onSubmit={handleCreateMatriz}>
                <select value={matrizDraft.regla_contable} onChange={(event) => setMatrizDraft((current) => ({ ...current, regla_contable: event.target.value }))}>
                  <option value="">Selecciona regla</option>
                  {reglasContables.map((item) => (
                    <option key={item.id} value={item.id}>{item.evento_tipo} · {empresaById.get(item.empresa)?.razon_social || item.empresa}</option>
                  ))}
                </select>
                <select value={matrizDraft.cuenta_debe} onChange={(event) => setMatrizDraft((current) => ({ ...current, cuenta_debe: event.target.value }))}>
                  <option value="">Cuenta debe</option>
                  {cuentasContables.map((item) => (
                    <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}</option>
                  ))}
                </select>
                <select value={matrizDraft.cuenta_haber} onChange={(event) => setMatrizDraft((current) => ({ ...current, cuenta_haber: event.target.value }))}>
                  <option value="">Cuenta haber</option>
                  {cuentasContables.map((item) => (
                    <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}</option>
                  ))}
                </select>
                <input placeholder="Condición impuesto" value={matrizDraft.condicion_impuesto} onChange={(event) => setMatrizDraft((current) => ({ ...current, condicion_impuesto: event.target.value }))} />
                <button type="submit" className="button-secondary" disabled={isSubmitting || !matrizDraft.regla_contable || !matrizDraft.cuenta_debe || !matrizDraft.cuenta_haber}>Guardar matriz</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Evento y cierre</h2><p>Evento manual, preparación y acciones sobre cierres.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateEventoContable}>
                <select value={eventoContableDraft.empresa} onChange={(event) => setEventoContableDraft((current) => ({ ...current, empresa: event.target.value }))}>
                  <option value="">Selecciona empresa</option>
                  {empresas.map((item) => (
                    <option key={item.id} value={item.id}>{item.razon_social}</option>
                  ))}
                </select>
                <input placeholder="Evento tipo" value={eventoContableDraft.evento_tipo} onChange={(event) => setEventoContableDraft((current) => ({ ...current, evento_tipo: event.target.value }))} />
                <input placeholder="Entidad origen tipo" value={eventoContableDraft.entidad_origen_tipo} onChange={(event) => setEventoContableDraft((current) => ({ ...current, entidad_origen_tipo: event.target.value }))} />
                <input placeholder="Entidad origen id" value={eventoContableDraft.entidad_origen_id} onChange={(event) => setEventoContableDraft((current) => ({ ...current, entidad_origen_id: event.target.value }))} />
                <input type="date" value={eventoContableDraft.fecha_operativa} onChange={(event) => setEventoContableDraft((current) => ({ ...current, fecha_operativa: event.target.value }))} />
                <input placeholder="Monto base" value={eventoContableDraft.monto_base} onChange={(event) => setEventoContableDraft((current) => ({ ...current, monto_base: event.target.value }))} />
                <input placeholder="Idempotency key" value={eventoContableDraft.idempotency_key} onChange={(event) => setEventoContableDraft((current) => ({ ...current, idempotency_key: event.target.value }))} />
                <input placeholder="Payload resumen JSON" value={eventoContableDraft.payload_resumen} onChange={(event) => setEventoContableDraft((current) => ({ ...current, payload_resumen: event.target.value }))} />
                <button type="submit" className="button-primary" disabled={isSubmitting || !eventoContableDraft.empresa || !eventoContableDraft.monto_base || !eventoContableDraft.idempotency_key}>Guardar evento</button>
              </form>
              <form className="entity-form subform" onSubmit={handlePrepareCierre}>
                <select value={cierreDraft.empresa_id} onChange={(event) => setCierreDraft((current) => ({ ...current, empresa_id: event.target.value }))}>
                  <option value="">Selecciona empresa</option>
                  {empresas.map((item) => (
                    <option key={item.id} value={item.id}>{item.razon_social}</option>
                  ))}
                </select>
                <input placeholder="Año" value={cierreDraft.anio} onChange={(event) => setCierreDraft((current) => ({ ...current, anio: event.target.value }))} />
                <input placeholder="Mes" value={cierreDraft.mes} onChange={(event) => setCierreDraft((current) => ({ ...current, mes: event.target.value }))} />
                <button type="submit" className="button-secondary" disabled={isSubmitting || !cierreDraft.empresa_id}>Preparar cierre</button>
              </form>
            </section>
          </section>

          <TableBlock title="Regímenes tributarios" subtitle="Regímenes disponibles para configuración fiscal." rows={filteredRegimenes} empty="No hay regímenes para este filtro." columns={[
            { label: 'Código', render: (row) => row.codigo_regimen },
            { label: 'Descripción', render: (row) => row.descripcion },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          ]} />

          <TableBlock title="Configuraciones fiscales" subtitle="Estado fiscal activo por empresa." rows={filteredConfigsFiscales} empty="No hay configuraciones fiscales para este filtro." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
            { label: 'Régimen', render: (row) => regimenById.get(row.regimen_tributario)?.codigo_regimen || row.regimen_tributario },
            { label: 'Moneda', render: (row) => row.moneda_funcional },
            { label: 'PPM', render: (row) => row.aplica_ppm ? 'Sí' : 'No' },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          ]} />

          <TableBlock title="Cuentas contables" subtitle="Plan contable disponible por empresa." rows={filteredCuentasContables} empty="No hay cuentas contables para este filtro." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
            { label: 'Código', render: (row) => row.codigo },
            { label: 'Nombre', render: (row) => row.nombre },
            { label: 'Naturaleza', render: (row) => row.naturaleza },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          ]} />

          <TableBlock title="Reglas y matrices" subtitle="Mapeo entre eventos y cuentas debe/haber." rows={filteredReglasContables} empty="No hay reglas contables para este filtro." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
            { label: 'Evento', render: (row) => row.evento_tipo },
            { label: 'Versión', render: (row) => row.plan_cuentas_version },
            { label: 'Cargo', render: (row) => row.criterio_cargo || 'Sin criterio' },
            { label: 'Abono', render: (row) => row.criterio_abono || 'Sin criterio' },
          ]} />

          <TableBlock title="Matrices de reglas" subtitle="Detalle de cuentas usadas por regla activa." rows={filteredMatrices} empty="No hay matrices para este filtro." columns={[
            { label: 'Regla', render: (row) => reglaById.get(row.regla_contable)?.evento_tipo || row.regla_contable },
            { label: 'Debe', render: (row) => cuentaContableById.get(row.cuenta_debe)?.codigo || row.cuenta_debe },
            { label: 'Haber', render: (row) => cuentaContableById.get(row.cuenta_haber)?.codigo || row.cuenta_haber },
            { label: 'Condición', render: (row) => row.condicion_impuesto || 'Sin condición' },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          ]} />

          <TableBlock title="Eventos contables" subtitle="Hechos económicos pendientes, en revisión o contabilizados." rows={filteredEventosContables} empty="No hay eventos contables para este filtro." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa || 0)?.razon_social || row.empresa || 'Sin empresa' },
            { label: 'Evento', render: (row) => row.evento_tipo },
            { label: 'Origen', render: (row) => `${row.entidad_origen_tipo}:${row.entidad_origen_id}` },
            { label: 'Monto', render: (row) => row.monto_base },
            { label: 'Estado', render: (row) => <Badge label={row.estado_contable} tone={toneFor(row.estado_contable)} /> },
            {
              label: 'Acción',
              render: (row) => (
                <button
                  type="button"
                  className="button-ghost inline-action"
                  onClick={() => void handleAccountingAction(`/api/v1/contabilidad/eventos-contables/${row.id}/contabilizar/`, 'Reintento de contabilización ejecutado correctamente.')}
                  disabled={isSubmitting}
                >
                  Contabilizar
                </button>
              ),
            },
          ]} />

          <TableBlock title="Asientos contables" subtitle="Asientos balanceados generados desde eventos." rows={filteredAsientosContables} empty="No hay asientos para este filtro." columns={[
            { label: 'Evento', render: (row) => row.evento_contable },
            { label: 'Período', render: (row) => row.periodo_contable },
            { label: 'Debe', render: (row) => row.debe_total },
            { label: 'Haber', render: (row) => row.haber_total },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          ]} />

          <TableBlock title="Obligaciones mensuales" subtitle="PPM e impuestos preparados desde los cierres." rows={filteredObligaciones} empty="No hay obligaciones mensuales para este filtro." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
            { label: 'Período', render: (row) => `${row.mes}/${row.anio}` },
            { label: 'Tipo', render: (row) => row.obligacion_tipo },
            { label: 'Monto', render: (row) => row.monto_calculado },
            { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
          ]} />

          <TableBlock title="Cierres mensuales" subtitle="Preparación, aprobación y reapertura del período." rows={filteredCierres} empty="No hay cierres mensuales para este filtro." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
            { label: 'Período', render: (row) => `${row.mes}/${row.anio}` },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
            {
              label: 'Acción',
              render: (row) => (
                <div className="inline-actions">
                  <button
                    type="button"
                    className="button-ghost inline-action"
                    onClick={() => void handleAccountingAction(`/api/v1/contabilidad/cierres-mensuales/${row.id}/aprobar/`, 'Cierre aprobado correctamente.')}
                    disabled={isSubmitting}
                  >
                    Aprobar
                  </button>
                  <button
                    type="button"
                    className="button-ghost inline-action"
                    onClick={() => void handleAccountingAction(`/api/v1/contabilidad/cierres-mensuales/${row.id}/reabrir/`, 'Cierre reabierto correctamente.')}
                    disabled={isSubmitting}
                  >
                    Reabrir
                  </button>
                </div>
              ),
            },
          ]} />
        </>
      ) : null}
    </main>
  )
}

export default App
