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

type Socio = {
  id: number
  nombre: string
  rut: string
  email: string
  telefono: string
  domicilio: string
  activo: boolean
}
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
  rol_avaluo: string
  codigo_propiedad: string
  direccion: string
  comuna: string
  region: string
  tipo_inmueble: string
  owner_tipo: string
  owner_id: number
  owner_display: string
  estado: string
}
type Cuenta = {
  id: number
  institucion: string
  numero_cuenta: string
  tipo_cuenta: string
  owner_tipo: string
  owner_id: number
  owner_display: string
  titular_nombre: string
  titular_rut: string
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
  propietario_tipo: string
  propietario_id: number
  propietario_display: string
  administrador_operativo_tipo: string
  administrador_operativo_id: number
  administrador_operativo_display: string
  recaudador_tipo: string
  recaudador_id: number
  recaudador_display: string
  entidad_facturadora_id: number | null
  entidad_facturadora_display: string | null
  cuenta_recaudadora_id: number
  cuenta_recaudadora_display: string
  tipo_relacion_operativa: string
  autoriza_recaudacion: boolean
  autoriza_facturacion: boolean
  autoriza_comunicacion: boolean
  vigencia_desde: string
  vigencia_hasta: string | null
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
  tiene_tramos: boolean
  tiene_gastos_comunes: boolean
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
    tipo_periodo: string
    origen_periodo: string
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
  | 'sii'
  | 'reporting'

type SectionKey =
  | 'patrimonio'
  | 'operacion'
  | 'contratos'
  | 'cobranza'
  | 'conciliacion'
  | 'contabilidad'
  | 'sii'
  | 'reporting'

type CapacidadSii = {
  id: number
  empresa: number
  capacidad_key: string
  certificado_ref: string
  ambiente: string
  estado_gate: string
  ultimo_resultado: Record<string, unknown>
}

type DteEmitido = {
  id: number
  empresa: number
  capacidad_tributaria: number
  contrato: number
  pago_mensual: number
  distribucion_cobro_mensual: number
  arrendatario: number
  tipo_dte: string
  monto_neto_clp: string
  fecha_emision: string
  estado_dte: string
  sii_track_id: string
  ultimo_estado_sii: string
  observaciones: string
}

type F29Preparacion = {
  id: number
  empresa: number
  capacidad_tributaria: number
  cierre_mensual: number
  anio: number
  mes: number
  estado_preparacion: string
  resumen_formulario: Record<string, unknown>
  borrador_ref: string
  observaciones: string
}

type ProcesoRentaAnual = {
  id: number
  empresa: number
  anio_tributario: number
  estado: string
  fecha_preparacion: string | null
}

type DdjjPreparacion = {
  id: number
  empresa: number
  capacidad_tributaria: number
  proceso_renta_anual: number
  anio_tributario: number
  estado_preparacion: string
  paquete_ref: string
  observaciones: string
}

type F22Preparacion = {
  id: number
  empresa: number
  capacidad_tributaria: number
  proceso_renta_anual: number
  anio_tributario: number
  estado_preparacion: string
  borrador_ref: string
  observaciones: string
}

type ReportingFinancialSummary = {
  anio: number
  mes: number
  empresa_id: number | null
  pagos_generados: number
  monto_facturable_total_clp: string
  monto_cobrado_total_clp: string
  eventos_contables_posteados: number
  monto_eventos_total_clp: string
  asientos_contables: number
  dtes_emitidos: number
  obligaciones: Array<{ tipo: string; monto_calculado: string; estado_preparacion: string }>
  cierres: Array<{ empresa_id: number; estado: string; fecha_preparacion: string | null; fecha_aprobacion: string | null }>
}

type ReportingPartnerSummary = {
  socio: { id: number; nombre: string; rut: string; email: string }
  participaciones_empresas: Array<{ empresa_id: number; empresa: string; porcentaje: string }>
  participaciones_comunidades: Array<{ comunidad_id: number; comunidad: string; porcentaje: string }>
  propiedades_directas: Array<{ propiedad_id: number; codigo_propiedad: string; direccion: string; estado: string }>
  contratos_directos_activos: number
  estados_cuenta_relacionados: number
}

type ReportingBooksSummary = {
  empresa_id: number
  periodo: string
  libro_diario: { id: number | null; estado_snapshot: string | null; storage_ref: string; resumen: Record<string, unknown> }
  libro_mayor: { id: number | null; estado_snapshot: string | null; storage_ref: string; resumen: Record<string, unknown> }
  balance_comprobacion: { id: number | null; estado_snapshot: string | null; storage_ref: string; resumen: Record<string, unknown> }
}

type ReportingAnnualSummary = {
  anio_tributario: number
  empresa_id: number | null
  procesos_renta: Array<{ empresa_id: number; estado: string; fecha_preparacion: string | null; resumen_anual: Record<string, unknown> }>
  ddjj_preparadas: Array<{ empresa_id: number; estado_preparacion: string; paquete_ref: string; resumen_paquete: Record<string, unknown> }>
  f22_preparados: Array<{ empresa_id: number; estado_preparacion: string; borrador_ref: string; resumen_f22: Record<string, unknown> }>
}

type ReportingMigrationSummary = {
  status: string
  total: number
  categorias: Array<{ category: string; total: number }>
  scope_types: Array<{ scope_type: string; total: number }>
  propiedades_owner_manual_required: Array<{
    id: string
    scope_reference: string
    summary: string
    codigo: number
    direccion: string
    candidate_owner_model: string
    participaciones_count: number
    total_pct: number
    blocked_contract_legacy_ids: string[]
    socios: Array<{ socio_nombre?: string; porcentaje?: string }>
  }>
}

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
  options: { method?: 'GET' | 'POST' | 'PATCH'; token?: string | null; body?: unknown } = {},
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

function canonicalRole(roleCode: string | null | undefined) {
  const normalized = String(roleCode || '').trim().toLowerCase()
  if (normalized === 'administradorglobal') return 'AdministradorGlobal'
  if (normalized === 'operadordecartera' || normalized === 'operator') return 'OperadorDeCartera'
  if (normalized === 'socio') return 'Socio'
  if (normalized === 'revisorfiscalexterno') return 'RevisorFiscalExterno'
  return roleCode || 'SinRol'
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
  const [capacidadesSii, setCapacidadesSii] = useState<CapacidadSii[]>([])
  const [dtes, setDtes] = useState<DteEmitido[]>([])
  const [f29s, setF29s] = useState<F29Preparacion[]>([])
  const [procesosAnuales, setProcesosAnuales] = useState<ProcesoRentaAnual[]>([])
  const [ddjjs, setDdjjs] = useState<DdjjPreparacion[]>([])
  const [f22s, setF22s] = useState<F22Preparacion[]>([])
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [workspaceError, setWorkspaceError] = useState<string | null>(null)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastLoadedAt, setLastLoadedAt] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<ViewKey>('overview')
  const [activeContextLabel, setActiveContextLabel] = useState<string | null>(null)
  const [searchText, setSearchText] = useState('')
  const [formMessage, setFormMessage] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [editingSocioId, setEditingSocioId] = useState<number | null>(null)
  const [editingPropiedadId, setEditingPropiedadId] = useState<number | null>(null)
  const [editingCuentaId, setEditingCuentaId] = useState<number | null>(null)
  const [editingMandatoId, setEditingMandatoId] = useState<number | null>(null)
  const [editingArrendatarioId, setEditingArrendatarioId] = useState<number | null>(null)
  const [editingContratoId, setEditingContratoId] = useState<number | null>(null)
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
  const [capacidadSiiDraft, setCapacidadSiiDraft] = useState({
    empresa: '',
    capacidad_key: 'DTEEmision',
    certificado_ref: 'cert-local',
    ambiente: 'certificacion',
    estado_gate: 'abierto',
  })
  const [dteDraft, setDteDraft] = useState({
    pago_mensual_id: '',
    tipo_dte: '34',
  })
  const [f29Draft, setF29Draft] = useState({
    empresa_id: '',
    anio: '2026',
    mes: '5',
  })
  const [annualDraft, setAnnualDraft] = useState({
    empresa_id: '',
    anio_tributario: '2027',
  })
  const [reportingFinancialDraft, setReportingFinancialDraft] = useState({
    anio: '2026',
    mes: '5',
    empresa_id: '',
  })
  const [reportingPartnerDraft, setReportingPartnerDraft] = useState({
    socio_id: '',
  })
  const [reportingBooksDraft, setReportingBooksDraft] = useState({
    empresa_id: '',
    periodo: '2026-05',
  })
  const [reportingAnnualDraft, setReportingAnnualDraft] = useState({
    anio_tributario: '2027',
    empresa_id: '',
  })
  const [reportingMigrationDraft, setReportingMigrationDraft] = useState({
    status: 'open',
  })
  const [reportingFinancialSummary, setReportingFinancialSummary] = useState<ReportingFinancialSummary | null>(null)
  const [reportingPartnerSummary, setReportingPartnerSummary] = useState<ReportingPartnerSummary | null>(null)
  const [reportingBooksSummary, setReportingBooksSummary] = useState<ReportingBooksSummary | null>(null)
  const [reportingAnnualSummary, setReportingAnnualSummary] = useState<ReportingAnnualSummary | null>(null)
  const [reportingMigrationSummary, setReportingMigrationSummary] = useState<ReportingMigrationSummary | null>(null)

  const effectiveRole = canonicalRole(currentUser?.default_role_code)
  const activeAssignments = currentUser?.assignments || []

  function canAccessView(view: ViewKey) {
    if (effectiveRole === 'AdministradorGlobal') return true
    if (effectiveRole === 'OperadorDeCartera') return true
    if (effectiveRole === 'Socio') return view === 'overview' || view === 'reporting'
    if (effectiveRole === 'RevisorFiscalExterno') {
      return ['overview', 'contabilidad', 'sii', 'reporting'].includes(view)
    }
    return view === 'overview'
  }

  function canMutateSection(section: SectionKey) {
    if (effectiveRole === 'AdministradorGlobal') return true
    if (effectiveRole === 'OperadorDeCartera') {
      return ['patrimonio', 'operacion', 'contratos', 'cobranza', 'conciliacion'].includes(section)
    }
    return false
  }

  const canEditPatrimonio = canMutateSection('patrimonio')
  const canEditOperacion = canMutateSection('operacion')
  const canEditContratos = canMutateSection('contratos')
  const canEditCobranza = canMutateSection('cobranza')
  const canEditConciliacion = canMutateSection('conciliacion')
  const canEditContabilidad = canMutateSection('contabilidad')
  const canEditSii = canMutateSection('sii')

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
        capacidadesSiiPayload,
        dtesPayload,
        f29Payload,
        procesosAnualesPayload,
        ddjjsPayload,
        f22sPayload,
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
        apiRequest<CapacidadSii[]>('/api/v1/sii/capacidades/', { token: activeToken }),
        apiRequest<DteEmitido[]>('/api/v1/sii/dtes/', { token: activeToken }),
        apiRequest<F29Preparacion[]>('/api/v1/sii/f29/', { token: activeToken }),
        apiRequest<ProcesoRentaAnual[]>('/api/v1/sii/anual/', { token: activeToken }),
        apiRequest<DdjjPreparacion[]>('/api/v1/sii/anual/ddjj/', { token: activeToken }),
        apiRequest<F22Preparacion[]>('/api/v1/sii/anual/f22/', { token: activeToken }),
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
      setCapacidadesSii(capacidadesSiiPayload)
      setDtes(dtesPayload)
      setF29s(f29Payload)
      setProcesosAnuales(procesosAnualesPayload)
      setDdjjs(ddjjsPayload)
      setF22s(f22sPayload)
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

  useEffect(() => {
    if (!canAccessView(activeView)) {
      setActiveView('overview')
      setActiveContextLabel(null)
    }
  }, [activeView, effectiveRole])

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
    setCapacidadesSii([])
    setDtes([])
    setF29s([])
    setProcesosAnuales([])
    setDdjjs([])
    setF22s([])
  }

  async function submitMutation(
    path: string,
    method: 'POST' | 'PATCH',
    body: unknown,
    successMessage: string,
    section?: SectionKey,
  ) {
    if (section && !canMutateSection(section)) {
      setFormError('Tu rol actual no tiene permisos para modificar esta sección.')
      return false
    }
    if (!token) return
    setIsSubmitting(true)
    setFormMessage(null)
    setFormError(null)
    try {
      await apiRequest(path, { method, token, body })
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

  async function submitCreate(path: string, body: unknown, successMessage: string) {
    return submitMutation(path, 'POST', body, successMessage)
  }

  async function handleCreateSocio(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditPatrimonio) return
    const isEdit = editingSocioId != null
    const ok = await submitMutation(
      isEdit ? `/api/v1/patrimonio/socios/${editingSocioId}/` : '/api/v1/patrimonio/socios/',
      isEdit ? 'PATCH' : 'POST',
      socioDraft,
      isEdit ? 'Socio actualizado correctamente.' : 'Socio creado correctamente.',
    )
    if (ok) {
      setSocioDraft({ nombre: '', rut: '', email: '', telefono: '', domicilio: '', activo: true })
      setEditingSocioId(null)
    }
  }

  async function handleCreatePropiedad(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditPatrimonio) return
    const isEdit = editingPropiedadId != null
    const ok = await submitMutation(
      isEdit ? `/api/v1/patrimonio/propiedades/${editingPropiedadId}/` : '/api/v1/patrimonio/propiedades/',
      isEdit ? 'PATCH' : 'POST',
      {
        ...propiedadDraft,
        owner_id: Number(propiedadDraft.owner_id),
      },
      isEdit ? 'Propiedad actualizada correctamente.' : 'Propiedad creada correctamente.',
    )
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
      setEditingPropiedadId(null)
    }
  }

  async function handleCreateCuenta(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditOperacion) return
    const isEdit = editingCuentaId != null
    const ok = await submitMutation(
      isEdit
        ? `/api/v1/operacion/cuentas-recaudadoras/${editingCuentaId}/`
        : '/api/v1/operacion/cuentas-recaudadoras/',
      isEdit ? 'PATCH' : 'POST',
      {
        ...cuentaDraft,
        owner_id: Number(cuentaDraft.owner_id),
      },
      isEdit ? 'Cuenta recaudadora actualizada correctamente.' : 'Cuenta recaudadora creada correctamente.',
    )
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
      setEditingCuentaId(null)
    }
  }

  async function handleCreateMandato(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditOperacion) return
    const isEdit = editingMandatoId != null
    const ok = await submitMutation(
      isEdit ? `/api/v1/operacion/mandatos/${editingMandatoId}/` : '/api/v1/operacion/mandatos/',
      isEdit ? 'PATCH' : 'POST',
      {
        ...mandatoDraft,
        propiedad_id: Number(mandatoDraft.propiedad_id),
        propietario_id: Number(mandatoDraft.propietario_id),
        administrador_operativo_id: Number(mandatoDraft.administrador_operativo_id),
        recaudador_id: Number(mandatoDraft.recaudador_id),
        entidad_facturadora_id: mandatoDraft.entidad_facturadora_id ? Number(mandatoDraft.entidad_facturadora_id) : null,
        cuenta_recaudadora_id: Number(mandatoDraft.cuenta_recaudadora_id),
        vigencia_hasta: mandatoDraft.vigencia_hasta || null,
      },
      isEdit ? 'Mandato operativo actualizado correctamente.' : 'Mandato operativo creado correctamente.',
    )
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
      setEditingMandatoId(null)
    }
  }

  async function handleCreateArrendatario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditContratos) return
    const isEdit = editingArrendatarioId != null
    const ok = await submitMutation(
      isEdit ? `/api/v1/contratos/arrendatarios/${editingArrendatarioId}/` : '/api/v1/contratos/arrendatarios/',
      isEdit ? 'PATCH' : 'POST',
      arrendatarioDraft,
      isEdit ? 'Arrendatario actualizado correctamente.' : 'Arrendatario creado correctamente.',
    )
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
      setEditingArrendatarioId(null)
    }
  }

  async function handleCreateContrato(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditContratos) return
    const selectedMandate = mandatos.find((item) => item.id === Number(contratoDraft.mandato_operacion))
    if (!selectedMandate) {
      setFormError('Debes seleccionar un mandato operativo válido.')
      return
    }
    const code = effectiveCodeFromPropertyCode(selectedMandate.propiedad_codigo)
    const isEdit = editingContratoId != null
    const ok = await submitMutation(
      isEdit ? `/api/v1/contratos/contratos/${editingContratoId}/` : '/api/v1/contratos/contratos/',
      isEdit ? 'PATCH' : 'POST',
      {
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
      },
      isEdit ? 'Contrato actualizado correctamente.' : 'Contrato creado correctamente.',
    )
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
      setEditingContratoId(null)
    }
  }

  function startEditSocio(row: Socio) {
    setEditingSocioId(row.id)
    setSocioDraft({
      nombre: row.nombre,
      rut: row.rut,
      email: row.email,
      telefono: row.telefono,
      domicilio: row.domicilio ?? '',
      activo: row.activo,
    })
    navigateWithContext('patrimonio', row.nombre, `Editando socio: ${row.nombre}`)
  }

  function cancelEditSocio() {
    setEditingSocioId(null)
    setSocioDraft({ nombre: '', rut: '', email: '', telefono: '', domicilio: '', activo: true })
    setActiveContextLabel(null)
  }

  function startEditPropiedad(row: Propiedad) {
    setEditingPropiedadId(row.id)
    setPropiedadDraft({
      codigo_propiedad: row.codigo_propiedad,
      direccion: row.direccion,
      comuna: row.comuna,
      region: row.region,
      rol_avaluo: row.rol_avaluo,
      tipo_inmueble: row.tipo_inmueble,
      estado: row.estado,
      owner_tipo: row.owner_tipo,
      owner_id: String(row.owner_id),
    })
    navigateWithContext('patrimonio', row.codigo_propiedad, `Editando propiedad: ${row.codigo_propiedad}`)
  }

  function cancelEditPropiedad() {
    setEditingPropiedadId(null)
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
    setActiveContextLabel(null)
  }

  function startEditCuenta(row: Cuenta) {
    setEditingCuentaId(row.id)
    setCuentaDraft({
      institucion: row.institucion,
      numero_cuenta: row.numero_cuenta,
      tipo_cuenta: row.tipo_cuenta,
      titular_nombre: row.titular_nombre,
      titular_rut: row.titular_rut,
      moneda_operativa: row.moneda_operativa,
      estado_operativo: row.estado_operativo,
      owner_tipo: row.owner_tipo,
      owner_id: String(row.owner_id),
    })
    navigateWithContext('operacion', row.numero_cuenta, `Editando cuenta: ${row.numero_cuenta}`)
  }

  function cancelEditCuenta() {
    setEditingCuentaId(null)
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
    setActiveContextLabel(null)
  }

  function startEditMandato(row: Mandato) {
    setEditingMandatoId(row.id)
    setMandatoDraft({
      propiedad_id: String(row.propiedad_id),
      propietario_tipo: row.propietario_tipo,
      propietario_id: String(row.propietario_id),
      administrador_operativo_tipo: row.administrador_operativo_tipo,
      administrador_operativo_id: String(row.administrador_operativo_id),
      recaudador_tipo: row.recaudador_tipo,
      recaudador_id: String(row.recaudador_id),
      entidad_facturadora_id: row.entidad_facturadora_id ? String(row.entidad_facturadora_id) : '',
      cuenta_recaudadora_id: String(row.cuenta_recaudadora_id),
      tipo_relacion_operativa: row.tipo_relacion_operativa,
      autoriza_recaudacion: row.autoriza_recaudacion,
      autoriza_facturacion: row.autoriza_facturacion,
      autoriza_comunicacion: row.autoriza_comunicacion,
      vigencia_desde: row.vigencia_desde,
      vigencia_hasta: row.vigencia_hasta || '',
      estado: row.estado,
    })
    navigateWithContext('operacion', row.propiedad_codigo, `Editando mandato: ${row.propiedad_codigo}`)
  }

  function cancelEditMandato() {
    setEditingMandatoId(null)
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
    setActiveContextLabel(null)
  }

  function startEditArrendatario(row: Arrendatario) {
    setEditingArrendatarioId(row.id)
    setArrendatarioDraft({
      tipo_arrendatario: row.tipo_arrendatario,
      nombre_razon_social: row.nombre_razon_social,
      rut: row.rut,
      email: row.email,
      telefono: row.telefono,
      domicilio_notificaciones: row.domicilio_notificaciones,
      estado_contacto: row.estado_contacto,
      whatsapp_bloqueado: row.whatsapp_bloqueado,
    })
    navigateWithContext('contratos', row.nombre_razon_social, `Editando arrendatario: ${row.nombre_razon_social}`)
  }

  function cancelEditArrendatario() {
    setEditingArrendatarioId(null)
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
    setActiveContextLabel(null)
  }

  function startEditContrato(row: Contrato) {
    setEditingContratoId(row.id)
    setContratoDraft({
      codigo_contrato: row.codigo_contrato,
      mandato_operacion: String(row.mandato_operacion),
      arrendatario: String(row.arrendatario),
      fecha_inicio: row.fecha_inicio,
      fecha_fin_vigente: row.fecha_fin_vigente,
      fecha_entrega: row.fecha_entrega || '',
      dia_pago_mensual: String(row.dia_pago_mensual),
      plazo_notificacion_termino_dias: String(row.plazo_notificacion_termino_dias),
      dias_prealerta_admin: String(row.dias_prealerta_admin),
      estado: row.estado,
      tiene_tramos: row.tiene_tramos,
      tiene_gastos_comunes: row.tiene_gastos_comunes,
      monto_base: row.periodos_contractuales_detail[0]?.monto_base || '',
      moneda_base: row.periodos_contractuales_detail[0]?.moneda_base || 'CLP',
      tipo_periodo: row.periodos_contractuales_detail[0]?.tipo_periodo || 'base',
      origen_periodo: row.periodos_contractuales_detail[0]?.origen_periodo || 'backoffice',
    })
    navigateWithContext('contratos', row.codigo_contrato, `Editando contrato: ${row.codigo_contrato}`)
  }

  function cancelEditContrato() {
    setEditingContratoId(null)
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
    setActiveContextLabel(null)
  }

  async function handleCreateAviso(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditContratos) return
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
    if (!canEditCobranza) return
    const ok = await submitCreate('/api/v1/cobranza/valores-uf/', ufDraft, 'Valor UF creado correctamente.')
    if (ok) {
      setUfDraft({ fecha: todayIso(), valor: '', source_key: 'manual' })
    }
  }

  async function handleCreateAjuste(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditCobranza) return
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
    if (!canEditCobranza) return
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
    if (!canEditCobranza) return
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
    if (!canEditCobranza) return
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
    if (!canEditCobranza) return
    const ok = await submitCreate('/api/v1/cobranza/estados-cuenta/recalcular/', {
      arrendatario_id: Number(estadoCuentaDraft.arrendatario_id),
    }, 'Estado de cuenta recalculado correctamente.')
    if (ok) {
      setEstadoCuentaDraft({ arrendatario_id: '' })
    }
  }

  async function handleCreateConexion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditConciliacion) return
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
    if (!canEditConciliacion) return
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
    if (!canEditConciliacion) return
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
    if (!canEditContabilidad) return
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
    if (!canEditContabilidad) return
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
    if (!canEditContabilidad) return
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
    if (!canEditContabilidad) return
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
    if (!canEditContabilidad) return
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
    if (!canEditContabilidad) return
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
    if (!canEditContabilidad) return
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

  async function handleCreateCapacidadSii(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditSii) return
    const ok = await submitCreate('/api/v1/sii/capacidades/', {
      empresa: Number(capacidadSiiDraft.empresa),
      capacidad_key: capacidadSiiDraft.capacidad_key,
      certificado_ref: capacidadSiiDraft.certificado_ref,
      ambiente: capacidadSiiDraft.ambiente,
      estado_gate: capacidadSiiDraft.estado_gate,
      ultimo_resultado: {},
    }, 'Capacidad SII creada correctamente.')
    if (ok) {
      setCapacidadSiiDraft({
        empresa: '',
        capacidad_key: 'DTEEmision',
        certificado_ref: 'cert-local',
        ambiente: 'certificacion',
        estado_gate: 'abierto',
      })
    }
  }

  async function handleGenerateDte(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditSii) return
    const ok = await submitCreate('/api/v1/sii/dtes/generar/', {
      pago_mensual_id: Number(dteDraft.pago_mensual_id),
      tipo_dte: dteDraft.tipo_dte,
    }, 'Borrador DTE generado correctamente.')
    if (ok) {
      setDteDraft({ pago_mensual_id: '', tipo_dte: '34' })
    }
  }

  async function handleGenerateF29(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditSii) return
    const ok = await submitCreate('/api/v1/sii/f29/generar/', {
      empresa_id: Number(f29Draft.empresa_id),
      anio: Number(f29Draft.anio),
      mes: Number(f29Draft.mes),
    }, 'F29 generado correctamente.')
    if (ok) {
      setF29Draft({ empresa_id: '', anio: '2026', mes: '5' })
    }
  }

  async function handleGenerateAnnual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditSii) return
    const ok = await submitCreate('/api/v1/sii/anual/generar/', {
      empresa_id: Number(annualDraft.empresa_id),
      anio_tributario: Number(annualDraft.anio_tributario),
    }, 'Preparación anual generada correctamente.')
    if (ok) {
      setAnnualDraft({ empresa_id: '', anio_tributario: '2027' })
    }
  }

  async function handleSiiStatusUpdate(path: string, body: Record<string, unknown>, successMessage: string) {
    if (!canEditSii) return
    if (!token) return
    setIsSubmitting(true)
    setFormMessage(null)
    setFormError(null)
    try {
      await apiRequest(path, { method: 'POST', token, body })
      await loadWorkspace(token)
      setFormMessage(successMessage)
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'No se pudo actualizar el estado SII.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function fetchReportingData<T>(path: string, onSuccess: (payload: T) => void, successMessage: string) {
    if (!token) return
    setIsSubmitting(true)
    setFormMessage(null)
    setFormError(null)
    try {
      const payload = await apiRequest<T>(path, { token })
      onSuccess(payload)
      setFormMessage(successMessage)
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'No se pudo cargar el reporte.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleFetchFinancialSummary(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const query = new URLSearchParams({
      anio: reportingFinancialDraft.anio,
      mes: reportingFinancialDraft.mes,
    })
    if (reportingFinancialDraft.empresa_id) query.set('empresa_id', reportingFinancialDraft.empresa_id)
    await fetchReportingData<ReportingFinancialSummary>(
      `/api/v1/reporting/financiero/mensual/?${query.toString()}`,
      setReportingFinancialSummary,
      'Resumen financiero cargado correctamente.',
    )
  }

  async function handleFetchPartnerSummary(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await fetchReportingData<ReportingPartnerSummary>(
      `/api/v1/reporting/socios/${Number(reportingPartnerDraft.socio_id)}/resumen/`,
      setReportingPartnerSummary,
      'Resumen de socio cargado correctamente.',
    )
  }

  async function handleFetchBooksSummary(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const query = new URLSearchParams({
      empresa_id: reportingBooksDraft.empresa_id,
      periodo: reportingBooksDraft.periodo,
    })
    await fetchReportingData<ReportingBooksSummary>(
      `/api/v1/reporting/contabilidad/libros-periodo/?${query.toString()}`,
      setReportingBooksSummary,
      'Resumen de libros cargado correctamente.',
    )
  }

  async function handleFetchAnnualSummary(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const query = new URLSearchParams({
      anio_tributario: reportingAnnualDraft.anio_tributario,
    })
    if (reportingAnnualDraft.empresa_id) query.set('empresa_id', reportingAnnualDraft.empresa_id)
    await fetchReportingData<ReportingAnnualSummary>(
      `/api/v1/reporting/tributario/anual/?${query.toString()}`,
      setReportingAnnualSummary,
      'Resumen anual cargado correctamente.',
    )
  }

  async function handleFetchMigrationSummary(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const query = new URLSearchParams({ status: reportingMigrationDraft.status })
    await fetchReportingData<ReportingMigrationSummary>(
      `/api/v1/reporting/migracion/resoluciones-manuales/?${query.toString()}`,
      setReportingMigrationSummary,
      'Resumen de resoluciones manuales cargado correctamente.',
    )
  }

  function navigateWithContext(view: ViewKey, search = '', label = '') {
    setActiveView(view)
    setSearchText(search)
    setActiveContextLabel(label || search || null)
    setFormMessage(null)
    setFormError(null)
  }

  function goToEmpresaContext(empresaId: number) {
    const companyLabel = empresaById.get(empresaId)?.razon_social || ''
    navigateWithContext('contabilidad', companyLabel, `Empresa: ${companyLabel}`)
    const defaultRegimenId = regimenesTributarios[0]?.id
    setConfigFiscalDraft((current) => ({
      ...current,
      empresa: String(empresaId),
      regimen_tributario: current.regimen_tributario || (defaultRegimenId ? String(defaultRegimenId) : ''),
    }))
    setCuentaContableDraft((current) => ({ ...current, empresa: String(empresaId) }))
    setReglaContableDraft((current) => ({ ...current, empresa: String(empresaId) }))
    setCierreDraft((current) => ({ ...current, empresa_id: String(empresaId) }))
    setCapacidadSiiDraft((current) => ({ ...current, empresa: String(empresaId) }))
    setF29Draft((current) => ({ ...current, empresa_id: String(empresaId) }))
    setAnnualDraft((current) => ({ ...current, empresa_id: String(empresaId) }))
    setReportingFinancialDraft((current) => ({ ...current, empresa_id: String(empresaId) }))
    setReportingAnnualDraft((current) => ({ ...current, empresa_id: String(empresaId) }))
  }

  function goToMandatoContext(mandatoId: number) {
    const mandate = mandatoById.get(mandatoId)
    navigateWithContext(
      'contratos',
      mandate?.propiedad_codigo || '',
      `Mandato: ${mandate?.propiedad_codigo || mandatoId}`,
    )
    setContratoDraft((current) => ({
      ...current,
      mandato_operacion: String(mandatoId),
    }))
  }

  function goToContratoContext(contratoId: number) {
    const contract = contratoById.get(contratoId)
    navigateWithContext(
      'cobranza',
      contract?.codigo_contrato || '',
      `Contrato: ${contract?.codigo_contrato || contratoId}`,
    )
    setAjusteDraft((current) => ({ ...current, contrato: String(contratoId) }))
    setPagoDraft((current) => ({ ...current, contrato_id: String(contratoId) }))
    setGarantiaDraft((current) => ({ ...current, contrato: String(contratoId) }))
  }

  function goToPagoContext(pagoId: number) {
    const payment = pagos.find((item) => item.id === pagoId)
    navigateWithContext(
      'sii',
      payment ? `${payment.mes}/${payment.anio}` : '',
      payment ? `Pago: ${payment.mes}/${payment.anio}` : `Pago: ${pagoId}`,
    )
    setDteDraft((current) => ({ ...current, pago_mensual_id: String(pagoId) }))
  }

  function goToArrendatarioContext(arrendatarioId: number) {
    const tenant = arrendatarioById.get(arrendatarioId)
    navigateWithContext(
      'cobranza',
      tenant?.nombre_razon_social || '',
      `Arrendatario: ${tenant?.nombre_razon_social || arrendatarioId}`,
    )
    setEstadoCuentaDraft({ arrendatario_id: String(arrendatarioId) })
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
  const filteredCapacidadesSii = useMemo(
    () =>
      capacidadesSii.filter((item) =>
        matches(normalizedSearch, [item.empresa, item.capacidad_key, item.ambiente, item.estado_gate]),
      ),
    [capacidadesSii, normalizedSearch],
  )
  const filteredDtes = useMemo(
    () =>
      dtes.filter((item) =>
        matches(normalizedSearch, [item.empresa, item.contrato, item.pago_mensual, item.tipo_dte, item.estado_dte, item.sii_track_id]),
      ),
    [dtes, normalizedSearch],
  )
  const filteredF29s = useMemo(
    () =>
      f29s.filter((item) =>
        matches(normalizedSearch, [item.empresa, item.anio, item.mes, item.estado_preparacion, item.borrador_ref]),
      ),
    [f29s, normalizedSearch],
  )
  const filteredProcesosAnuales = useMemo(
    () =>
      procesosAnuales.filter((item) =>
        matches(normalizedSearch, [item.empresa, item.anio_tributario, item.estado]),
      ),
    [procesosAnuales, normalizedSearch],
  )
  const filteredDdjjs = useMemo(
    () =>
      ddjjs.filter((item) =>
        matches(normalizedSearch, [item.empresa, item.anio_tributario, item.estado_preparacion, item.paquete_ref]),
      ),
    [ddjjs, normalizedSearch],
  )
  const filteredF22s = useMemo(
    () =>
      f22s.filter((item) =>
        matches(normalizedSearch, [item.empresa, item.anio_tributario, item.estado_preparacion, item.borrador_ref]),
      ),
    [f22s, normalizedSearch],
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
  const capacidadSiiById = useMemo(() => new Map(capacidadesSii.map((item) => [item.id, item])), [capacidadesSii])

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
          {currentUser ? (
            <div className="scope-strip">
              <Badge label={effectiveRole} tone="neutral" />
              {activeAssignments.map((assignment, index) => (
                <Badge
                  key={`${assignment.role}-${assignment.scope || 'global'}-${index}`}
                  label={assignment.scope ? `${assignment.role} · ${assignment.scope}` : assignment.role}
                  tone={assignment.is_primary ? 'positive' : 'neutral'}
                />
              ))}
            </div>
          ) : null}
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
        {(['overview', 'patrimonio', 'operacion', 'contratos', 'cobranza', 'conciliacion', 'contabilidad', 'sii', 'reporting'] as ViewKey[])
          .filter((view) => canAccessView(view))
          .map((view) => (
          <button
            key={view}
            type="button"
            className={activeView === view ? 'tab-button is-active' : 'tab-button'}
            onClick={() => {
              setActiveView(view)
              setActiveContextLabel(null)
            }}
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
                        : view === 'contabilidad'
                        ? 'Contabilidad'
                          : view === 'sii'
                            ? 'SII'
                            : 'Reporting'}
          </button>
        ))}
      </section>

      {workspaceError ? <div className="banner-error">{workspaceError}</div> : null}
      {activeView !== 'overview' && activeContextLabel ? (
        <div className="context-banner">
          <span>{activeContextLabel}</span>
          <button type="button" className="button-ghost inline-action" onClick={() => setActiveContextLabel(null)}>
            Limpiar contexto
          </button>
        </div>
      ) : null}

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
                        : activeView === 'contabilidad'
                        ? 'Contabilidad'
                          : activeView === 'sii'
                            ? 'SII'
                            : 'Reporting'}
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
                        : activeView === 'contabilidad'
                          ? 'Configuración fiscal, eventos, asientos y cierres'
                          : activeView === 'sii'
                            ? 'Capacidades, DTE, F29 y preparación anual'
                            : 'Dashboard, socios, libros y resumen anual'}
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
                          : activeView === 'contabilidad'
                            ? 'Empresa, evento, cuenta, cierre u obligación'
                            : activeView === 'sii'
                              ? 'Empresa, DTE, F29, DDJJ o F22'
                              : 'Empresa, socio, libro o resolución'
              }
            />
          </label>
        </section>
      ) : null}

      {activeView !== 'overview' && formMessage ? <div className="banner-success">{formMessage}</div> : null}
      {activeView !== 'overview' && formError ? <div className="banner-error">{formError}</div> : null}

      {activeView === 'patrimonio' ? (
        <>
          {!canEditPatrimonio ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Patrimonio.</div> : null}
          <section className="form-grid">
            <section className="panel">
              <div className="section-heading"><div><h2>{editingSocioId ? 'Editar socio' : 'Alta rápida de socio'}</h2><p>Ingreso mínimo para participantes activos.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateSocio}>
                <input placeholder="Nombre completo" value={socioDraft.nombre} onChange={(event) => setSocioDraft((current) => ({ ...current, nombre: event.target.value }))} />
                <input placeholder="RUT" value={socioDraft.rut} onChange={(event) => setSocioDraft((current) => ({ ...current, rut: event.target.value }))} />
                <input placeholder="Email" value={socioDraft.email} onChange={(event) => setSocioDraft((current) => ({ ...current, email: event.target.value }))} />
                <input placeholder="Teléfono" value={socioDraft.telefono} onChange={(event) => setSocioDraft((current) => ({ ...current, telefono: event.target.value }))} />
                <input placeholder="Domicilio" value={socioDraft.domicilio} onChange={(event) => setSocioDraft((current) => ({ ...current, domicilio: event.target.value }))} />
                <label className="checkbox-row"><input type="checkbox" checked={socioDraft.activo} onChange={(event) => setSocioDraft((current) => ({ ...current, activo: event.target.checked }))} />Activo</label>
                <div className="inline-actions">
                  <button type="submit" className="button-primary" disabled={isSubmitting}>{editingSocioId ? 'Guardar cambios' : 'Guardar socio'}</button>
                  {editingSocioId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditSocio}>Cancelar</button> : null}
                </div>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>{editingPropiedadId ? 'Editar propiedad' : 'Alta rápida de propiedad'}</h2><p>Owner explícito y código operativo desde el inicio.</p></div></div>
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
                <div className="inline-actions">
                  <button type="submit" className="button-primary" disabled={isSubmitting || !propiedadDraft.owner_id}>{editingPropiedadId ? 'Guardar cambios' : 'Guardar propiedad'}</button>
                  {editingPropiedadId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditPropiedad}>Cancelar</button> : null}
                </div>
              </form>
            </section>
          </section>

          <TableBlock title="Socios" subtitle="Participantes y representantes activos." rows={filteredSocios} empty="No hay socios para este filtro." columns={[
            { label: 'Nombre', render: (row) => row.nombre },
            { label: 'RUT', render: (row) => row.rut },
            { label: 'Contacto', render: (row) => row.email || row.telefono || 'Sin dato' },
            { label: 'Estado', render: (row) => <Badge label={row.activo ? 'activo' : 'inactivo'} tone={row.activo ? 'positive' : 'danger'} /> },
            {
              label: 'Acción',
              render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditSocio(row)}>Editar</button>,
            },
          ]} />
          <TableBlock title="Empresas" subtitle="Owners empresariales y participaciones vigentes." rows={filteredEmpresas} empty="No hay empresas para este filtro." columns={[
            { label: 'Razón social', render: (row) => row.razon_social },
            { label: 'RUT', render: (row) => row.rut },
            { label: 'Participaciones', render: (row) => count(row.participaciones_detail.length) },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
            {
              label: 'Siguiente paso',
              render: (row) => (
                <div className="inline-actions">
                  <button type="button" className="button-ghost inline-action" onClick={() => goToEmpresaContext(row.id)}>
                    Contabilidad
                  </button>
                  <button type="button" className="button-ghost inline-action" onClick={() => { navigateWithContext('sii', row.razon_social); setCapacidadSiiDraft((current) => ({ ...current, empresa: String(row.id) })) }}>
                    SII
                  </button>
                </div>
              ),
            },
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
            {
              label: 'Editar',
              render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditPropiedad(row)}>Editar</button>,
            },
            {
              label: 'Siguiente paso',
              render: (row) => (
                <button
                  type="button"
                  className="button-ghost inline-action"
                  onClick={() => {
                    navigateWithContext('operacion', row.codigo_propiedad, `Propiedad: ${row.codigo_propiedad}`)
                    setMandatoDraft((current) => ({ ...current, propiedad_id: String(row.id) }))
                  }}
                >
                  Crear mandato
                </button>
              ),
            },
          ]} />
        </>
      ) : null}

      {activeView === 'operacion' ? (
        <>
          {!canEditOperacion ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Operación.</div> : null}
          <section className="form-grid">
            <section className="panel">
              <div className="section-heading"><div><h2>{editingCuentaId ? 'Editar cuenta' : 'Alta rápida de cuenta'}</h2><p>Cuenta recaudadora con owner bancario explícito.</p></div></div>
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
                <div className="inline-actions">
                  <button type="submit" className="button-primary" disabled={isSubmitting || !cuentaDraft.owner_id}>{editingCuentaId ? 'Guardar cambios' : 'Guardar cuenta'}</button>
                  {editingCuentaId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditCuenta}>Cancelar</button> : null}
                </div>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>{editingMandatoId ? 'Editar mandato' : 'Alta rápida de mandato'}</h2><p>Separación explícita entre propietario, administrador, recaudador y facturadora.</p></div></div>
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
                <div className="inline-actions">
                  <button type="submit" className="button-primary" disabled={isSubmitting || !mandatoDraft.propiedad_id || !mandatoDraft.propietario_id || !mandatoDraft.administrador_operativo_id || !mandatoDraft.recaudador_id || !mandatoDraft.cuenta_recaudadora_id}>{editingMandatoId ? 'Guardar cambios' : 'Guardar mandato'}</button>
                  {editingMandatoId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditMandato}>Cancelar</button> : null}
                </div>
              </form>
            </section>
          </section>

          <TableBlock title="Cuentas recaudadoras" subtitle="Ownership bancario operativo." rows={filteredCuentas} empty="No hay cuentas para este filtro." columns={[
            { label: 'Cuenta', render: (row) => `${row.institucion} · ${row.numero_cuenta}` },
            { label: 'Owner', render: (row) => `${row.owner_display} · ${row.owner_tipo}` },
            { label: 'Moneda', render: (row) => row.moneda_operativa },
            { label: 'Estado', render: (row) => <Badge label={row.estado_operativo} tone={toneFor(row.estado_operativo)} /> },
            {
              label: 'Editar',
              render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditCuenta(row)}>Editar</button>,
            },
            {
              label: 'Siguiente paso',
              render: (row) => (
                <button
                  type="button"
                  className="button-ghost inline-action"
                  onClick={() => {
                    navigateWithContext('conciliacion', row.numero_cuenta, `Cuenta: ${row.numero_cuenta}`)
                    setConexionDraft((current) => ({ ...current, cuenta_recaudadora: String(row.id) }))
                  }}
                >
                  Conectar banco
                </button>
              ),
            },
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
            {
              label: 'Editar',
              render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditMandato(row)}>Editar</button>,
            },
            {
              label: 'Siguiente paso',
              render: (row) => (
                <button type="button" className="button-ghost inline-action" onClick={() => goToMandatoContext(row.id)}>
                  Crear contrato
                </button>
              ),
            },
          ]} />
        </>
      ) : null}

      {activeView === 'contratos' ? (
        <>
          {!canEditContratos ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Contratos.</div> : null}
          <section className="form-grid">
            <section className="panel">
              <div className="section-heading"><div><h2>{editingArrendatarioId ? 'Editar arrendatario' : 'Alta rápida de arrendatario'}</h2><p>Base mínima para contratar sobre mandatos ya activos.</p></div></div>
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
                <div className="inline-actions">
                  <button type="submit" className="button-primary" disabled={isSubmitting}>{editingArrendatarioId ? 'Guardar cambios' : 'Guardar arrendatario'}</button>
                  {editingArrendatarioId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditArrendatario}>Cancelar</button> : null}
                </div>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>{editingContratoId ? 'Editar contrato' : 'Alta rápida de contrato'}</h2><p>Contrato simple con una propiedad principal y un primer período.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateContrato}>
                <input placeholder="Código contrato" value={contratoDraft.codigo_contrato} onChange={(event) => setContratoDraft((current) => ({ ...current, codigo_contrato: event.target.value }))} disabled={editingContratoId != null} />
                <select value={contratoDraft.mandato_operacion} onChange={(event) => setContratoDraft((current) => ({ ...current, mandato_operacion: event.target.value }))}>
                  <option value="">Selecciona mandato</option>
                  {mandatos.map((item) => (
                    <option key={item.id} value={item.id}>{item.propiedad_codigo} · {item.propietario_display}</option>
                  ))}
                </select>
                <select value={contratoDraft.arrendatario} onChange={(event) => setContratoDraft((current) => ({ ...current, arrendatario: event.target.value }))} disabled={editingContratoId != null}>
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
                <div className="inline-actions">
                  <button type="submit" className="button-primary" disabled={isSubmitting || !contratoDraft.codigo_contrato || !contratoDraft.mandato_operacion || !contratoDraft.arrendatario || !contratoDraft.monto_base}>{editingContratoId ? 'Guardar cambios' : 'Guardar contrato'}</button>
                  {editingContratoId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditContrato}>Cancelar</button> : null}
                </div>
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
            {
              label: 'Editar',
              render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditArrendatario(row)}>Editar</button>,
            },
            {
              label: 'Siguiente paso',
              render: (row) => (
                <button type="button" className="button-ghost inline-action" onClick={() => goToArrendatarioContext(row.id)}>
                  Estado de cuenta
                </button>
              ),
            },
          ]} />

          <TableBlock title="Contratos" subtitle="Contratos cargados sobre mandatos ya vigentes." rows={filteredContratos} empty="No hay contratos para este filtro." columns={[
            { label: 'Código', render: (row) => row.codigo_contrato },
            { label: 'Arrendatario', render: (row) => arrendatarioById.get(row.arrendatario)?.nombre_razon_social || row.arrendatario },
            { label: 'Mandato', render: (row) => mandatoById.get(row.mandato_operacion)?.propiedad_codigo || row.mandato_operacion },
            { label: 'Propiedad', render: (row) => row.contrato_propiedades_detail[0] ? `${row.contrato_propiedades_detail[0].propiedad_codigo} · ${row.contrato_propiedades_detail[0].propiedad_direccion}` : 'Sin propiedad' },
            { label: 'Periodo', render: (row) => `${row.fecha_inicio} → ${row.fecha_fin_vigente}` },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
            {
              label: 'Editar',
              render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditContrato(row)}>Editar</button>,
            },
            {
              label: 'Siguiente paso',
              render: (row) => (
                <button type="button" className="button-ghost inline-action" onClick={() => goToContratoContext(row.id)}>
                  Cobranza
                </button>
              ),
            },
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
          {!canEditCobranza ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Cobranza.</div> : null}
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
            {
              label: 'Siguiente paso',
              render: (row) => (
                <div className="inline-actions">
                  <button type="button" className="button-ghost inline-action" onClick={() => { navigateWithContext('conciliacion', `${row.mes}/${row.anio}`) }}>
                    Conciliar
                  </button>
                  <button type="button" className="button-ghost inline-action" onClick={() => goToPagoContext(row.id)}>
                    DTE
                  </button>
                </div>
              ),
            },
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
          {!canEditConciliacion ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Conciliación.</div> : null}
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
          {!canEditContabilidad ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Contabilidad.</div> : null}
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
                <div className="inline-actions">
                  <button
                    type="button"
                    className="button-ghost inline-action"
                    onClick={() => void handleAccountingAction(`/api/v1/contabilidad/eventos-contables/${row.id}/contabilizar/`, 'Reintento de contabilización ejecutado correctamente.')}
                    disabled={isSubmitting}
                  >
                    Contabilizar
                  </button>
                  {row.empresa ? (
                    <button
                      type="button"
                      className="button-ghost inline-action"
                      onClick={() => {
                        if (row.empresa == null) return
                        const companyId = row.empresa
                        const companyName = empresaById.get(companyId)?.razon_social || String(companyId)
                        navigateWithContext('reporting', companyName, `Empresa: ${companyName}`)
                        setReportingFinancialDraft((current) => ({ ...current, empresa_id: String(companyId) }))
                      }}
                    >
                      Ver impacto
                    </button>
                  ) : null}
                </div>
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

      {activeView === 'sii' ? (
        <>
          {!canEditSii ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en SII.</div> : null}
          <section className="form-grid">
            <section className="panel">
              <div className="section-heading"><div><h2>Capacidad SII</h2><p>Gate operativo por empresa y capacidad tributaria.</p></div></div>
              <form className="entity-form" onSubmit={handleCreateCapacidadSii}>
                <select value={capacidadSiiDraft.empresa} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, empresa: event.target.value }))}>
                  <option value="">Selecciona empresa</option>
                  {empresas.map((item) => (
                    <option key={item.id} value={item.id}>{item.razon_social}</option>
                  ))}
                </select>
                <select value={capacidadSiiDraft.capacidad_key} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, capacidad_key: event.target.value }))}>
                  <option value="DTEEmision">DTE Emisión</option>
                  <option value="DTEConsultaEstado">DTE Consulta Estado</option>
                  <option value="F29Preparacion">F29 Preparación</option>
                  <option value="F29Presentacion">F29 Presentación</option>
                  <option value="DDJJPreparacion">DDJJ Preparación</option>
                  <option value="F22Preparacion">F22 Preparación</option>
                </select>
                <input placeholder="Certificado ref" value={capacidadSiiDraft.certificado_ref} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, certificado_ref: event.target.value }))} />
                <select value={capacidadSiiDraft.ambiente} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, ambiente: event.target.value }))}>
                  <option value="certificacion">Certificación</option>
                  <option value="produccion">Producción</option>
                </select>
                <select value={capacidadSiiDraft.estado_gate} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, estado_gate: event.target.value }))}>
                  <option value="abierto">Abierto</option>
                  <option value="condicionado">Condicionado</option>
                  <option value="cerrado">Cerrado</option>
                  <option value="suspendido">Suspendido</option>
                  <option value="podado">Podado</option>
                </select>
                <button type="submit" className="button-primary" disabled={isSubmitting || !capacidadSiiDraft.empresa}>Guardar capacidad</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Generar DTE</h2><p>Borrador desde un pago mensual con distribución facturable.</p></div></div>
              <form className="entity-form" onSubmit={handleGenerateDte}>
                <select value={dteDraft.pago_mensual_id} onChange={(event) => setDteDraft((current) => ({ ...current, pago_mensual_id: event.target.value }))}>
                  <option value="">Selecciona pago</option>
                  {pagos.map((item) => (
                    <option key={item.id} value={item.id}>{contratoById.get(item.contrato)?.codigo_contrato || item.contrato} · {item.mes}/{item.anio}</option>
                  ))}
                </select>
                <select value={dteDraft.tipo_dte} onChange={(event) => setDteDraft((current) => ({ ...current, tipo_dte: event.target.value }))}>
                  <option value="34">34 · Factura Exenta</option>
                  <option value="56">56 · Nota Débito</option>
                  <option value="61">61 · Nota Crédito</option>
                </select>
                <button type="submit" className="button-primary" disabled={isSubmitting || !dteDraft.pago_mensual_id}>Generar DTE</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Generar F29</h2><p>Borrador mensual desde cierre contable preparado.</p></div></div>
              <form className="entity-form" onSubmit={handleGenerateF29}>
                <select value={f29Draft.empresa_id} onChange={(event) => setF29Draft((current) => ({ ...current, empresa_id: event.target.value }))}>
                  <option value="">Selecciona empresa</option>
                  {empresas.map((item) => (
                    <option key={item.id} value={item.id}>{item.razon_social}</option>
                  ))}
                </select>
                <input placeholder="Año" value={f29Draft.anio} onChange={(event) => setF29Draft((current) => ({ ...current, anio: event.target.value }))} />
                <input placeholder="Mes" value={f29Draft.mes} onChange={(event) => setF29Draft((current) => ({ ...current, mes: event.target.value }))} />
                <button type="submit" className="button-primary" disabled={isSubmitting || !f29Draft.empresa_id}>Generar F29</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Preparación anual</h2><p>Genera proceso anual, DDJJ y F22.</p></div></div>
              <form className="entity-form" onSubmit={handleGenerateAnnual}>
                <select value={annualDraft.empresa_id} onChange={(event) => setAnnualDraft((current) => ({ ...current, empresa_id: event.target.value }))}>
                  <option value="">Selecciona empresa</option>
                  {empresas.map((item) => (
                    <option key={item.id} value={item.id}>{item.razon_social}</option>
                  ))}
                </select>
                <input placeholder="Año tributario" value={annualDraft.anio_tributario} onChange={(event) => setAnnualDraft((current) => ({ ...current, anio_tributario: event.target.value }))} />
                <button type="submit" className="button-primary" disabled={isSubmitting || !annualDraft.empresa_id}>Generar anual</button>
              </form>
            </section>
          </section>

          <TableBlock title="Capacidades SII" subtitle="Gate y ambiente por empresa/capacidad." rows={filteredCapacidadesSii} empty="No hay capacidades SII para este filtro." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
            { label: 'Capacidad', render: (row) => row.capacidad_key },
            { label: 'Ambiente', render: (row) => row.ambiente },
            { label: 'Estado', render: (row) => <Badge label={row.estado_gate} tone={toneFor(row.estado_gate)} /> },
          ]} />

          <TableBlock title="DTE emitidos" subtitle="Borradores y estados manuales de DTE." rows={filteredDtes} empty="No hay DTE para este filtro." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
            { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
            { label: 'Pago', render: (row) => row.pago_mensual },
            { label: 'Monto', render: (row) => row.monto_neto_clp },
            { label: 'Estado', render: (row) => <Badge label={row.estado_dte} tone={toneFor(row.estado_dte)} /> },
            {
              label: 'Acción',
              render: (row) => (
                <div className="inline-actions">
                  <button
                    type="button"
                    className="button-ghost inline-action"
                    onClick={() => void handleSiiStatusUpdate(`/api/v1/sii/dtes/${row.id}/estado/`, { estado_dte: 'aceptado', sii_track_id: row.sii_track_id || 'TRACK-LOCAL', ultimo_estado_sii: 'ACEPTADO' }, 'Estado DTE actualizado correctamente.')}
                    disabled={isSubmitting}
                  >
                    Marcar aceptado
                  </button>
                  <button
                    type="button"
                    className="button-ghost inline-action"
                    onClick={() => { navigateWithContext('reporting', empresaById.get(row.empresa)?.razon_social || ''); setReportingFinancialDraft((current) => ({ ...current, empresa_id: String(row.empresa) })) }}
                  >
                    Reporting
                  </button>
                </div>
              ),
            },
          ]} />

          <TableBlock title="F29 mensuales" subtitle="Preparación mensual desde cierres aprobados." rows={filteredF29s} empty="No hay F29 para este filtro." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
            { label: 'Período', render: (row) => `${row.mes}/${row.anio}` },
            { label: 'Capacidad', render: (row) => capacidadSiiById.get(row.capacidad_tributaria)?.capacidad_key || row.capacidad_tributaria },
            { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
            {
              label: 'Acción',
              render: (row) => (
                <button
                  type="button"
                  className="button-ghost inline-action"
                  onClick={() => void handleSiiStatusUpdate(`/api/v1/sii/f29/${row.id}/estado/`, { estado_preparacion: 'preparado', borrador_ref: row.borrador_ref || 'F29-LOCAL' }, 'Estado F29 actualizado correctamente.')}
                  disabled={isSubmitting}
                >
                  Actualizar estado
                </button>
              ),
            },
          ]} />

          <TableBlock title="Proceso renta anual" subtitle="Proceso consolidado por empresa y año tributario." rows={filteredProcesosAnuales} empty="No hay procesos anuales para este filtro." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
            { label: 'Año tributario', render: (row) => row.anio_tributario },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
            { label: 'Preparación', render: (row) => row.fecha_preparacion || 'Sin fecha' },
          ]} />

          <TableBlock title="DDJJ preparadas" subtitle="Paquetes anuales listos o en preparación." rows={filteredDdjjs} empty="No hay DDJJ para este filtro." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
            { label: 'Año tributario', render: (row) => row.anio_tributario },
            { label: 'Paquete', render: (row) => row.paquete_ref || 'Sin ref' },
            { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
            {
              label: 'Acción',
              render: (row) => (
                <button
                  type="button"
                  className="button-ghost inline-action"
                  onClick={() => void handleSiiStatusUpdate(`/api/v1/sii/anual/ddjj/${row.id}/estado/`, { estado_preparacion: 'preparado', ref_value: row.paquete_ref || 'DDJJ-LOCAL' }, 'Estado DDJJ actualizado correctamente.')}
                  disabled={isSubmitting}
                >
                  Actualizar estado
                </button>
              ),
            },
          ]} />

          <TableBlock title="F22 preparados" subtitle="Borradores anuales por empresa." rows={filteredF22s} empty="No hay F22 para este filtro." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
            { label: 'Año tributario', render: (row) => row.anio_tributario },
            { label: 'Borrador', render: (row) => row.borrador_ref || 'Sin ref' },
            { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
            {
              label: 'Acción',
              render: (row) => (
                <button
                  type="button"
                  className="button-ghost inline-action"
                  onClick={() => void handleSiiStatusUpdate(`/api/v1/sii/anual/f22/${row.id}/estado/`, { estado_preparacion: 'preparado', ref_value: row.borrador_ref || 'F22-LOCAL' }, 'Estado F22 actualizado correctamente.')}
                  disabled={isSubmitting}
                >
                  Actualizar estado
                </button>
              ),
            },
          ]} />
        </>
      ) : null}

      {activeView === 'reporting' ? (
        <>
          <section className="form-grid">
            <section className="panel">
              <div className="section-heading"><div><h2>Resumen financiero mensual</h2><p>Pagos, eventos, cierres y obligaciones por período.</p></div></div>
              <form className="entity-form" onSubmit={handleFetchFinancialSummary}>
                <select value={reportingFinancialDraft.empresa_id} onChange={(event) => setReportingFinancialDraft((current) => ({ ...current, empresa_id: event.target.value }))}>
                  <option value="">Todas las empresas</option>
                  {empresas.map((item) => (
                    <option key={item.id} value={item.id}>{item.razon_social}</option>
                  ))}
                </select>
                <input placeholder="Año" value={reportingFinancialDraft.anio} onChange={(event) => setReportingFinancialDraft((current) => ({ ...current, anio: event.target.value }))} />
                <input placeholder="Mes" value={reportingFinancialDraft.mes} onChange={(event) => setReportingFinancialDraft((current) => ({ ...current, mes: event.target.value }))} />
                <button type="submit" className="button-primary" disabled={isSubmitting}>Cargar resumen</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Resumen por socio</h2><p>Participaciones, propiedades directas y estado relacionado.</p></div></div>
              <form className="entity-form" onSubmit={handleFetchPartnerSummary}>
                <select value={reportingPartnerDraft.socio_id} onChange={(event) => setReportingPartnerDraft({ socio_id: event.target.value })}>
                  <option value="">Selecciona socio</option>
                  {socios.map((item) => (
                    <option key={item.id} value={item.id}>{item.nombre}</option>
                  ))}
                </select>
                <button type="submit" className="button-primary" disabled={isSubmitting || !reportingPartnerDraft.socio_id}>Cargar socio</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Libros por período</h2><p>Libro diario, mayor y balance de comprobación.</p></div></div>
              <form className="entity-form" onSubmit={handleFetchBooksSummary}>
                <select value={reportingBooksDraft.empresa_id} onChange={(event) => setReportingBooksDraft((current) => ({ ...current, empresa_id: event.target.value }))}>
                  <option value="">Selecciona empresa</option>
                  {empresas.map((item) => (
                    <option key={item.id} value={item.id}>{item.razon_social}</option>
                  ))}
                </select>
                <input placeholder="Período YYYY-MM" value={reportingBooksDraft.periodo} onChange={(event) => setReportingBooksDraft((current) => ({ ...current, periodo: event.target.value }))} />
                <button type="submit" className="button-primary" disabled={isSubmitting || !reportingBooksDraft.empresa_id}>Cargar libros</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Resumen tributario anual</h2><p>Proceso renta, DDJJ y F22 consolidados.</p></div></div>
              <form className="entity-form" onSubmit={handleFetchAnnualSummary}>
                <select value={reportingAnnualDraft.empresa_id} onChange={(event) => setReportingAnnualDraft((current) => ({ ...current, empresa_id: event.target.value }))}>
                  <option value="">Todas las empresas</option>
                  {empresas.map((item) => (
                    <option key={item.id} value={item.id}>{item.razon_social}</option>
                  ))}
                </select>
                <input placeholder="Año tributario" value={reportingAnnualDraft.anio_tributario} onChange={(event) => setReportingAnnualDraft((current) => ({ ...current, anio_tributario: event.target.value }))} />
                <button type="submit" className="button-primary" disabled={isSubmitting}>Cargar anual</button>
              </form>
            </section>

            <section className="panel">
              <div className="section-heading"><div><h2>Resoluciones manuales</h2><p>Backlog de migración pendiente o resuelto.</p></div></div>
              <form className="entity-form" onSubmit={handleFetchMigrationSummary}>
                <select value={reportingMigrationDraft.status} onChange={(event) => setReportingMigrationDraft({ status: event.target.value })}>
                  <option value="open">Open</option>
                  <option value="resolved">Resolved</option>
                  <option value="in_review">In review</option>
                </select>
                <button type="submit" className="button-primary" disabled={isSubmitting}>Cargar backlog</button>
              </form>
            </section>
          </section>

          {reportingFinancialSummary ? (
            <>
              <section className="metric-grid">
                <Metric label="Pagos generados" value={count(reportingFinancialSummary.pagos_generados)} tone="neutral" />
                <Metric label="Facturable total" value={reportingFinancialSummary.monto_facturable_total_clp} tone="positive" />
                <Metric label="Cobrado total" value={reportingFinancialSummary.monto_cobrado_total_clp} tone="positive" />
                <Metric label="Eventos posteados" value={count(reportingFinancialSummary.eventos_contables_posteados)} tone="neutral" />
                <Metric label="Asientos" value={count(reportingFinancialSummary.asientos_contables)} tone="neutral" />
                <Metric label="DTE emitidos" value={count(reportingFinancialSummary.dtes_emitidos)} tone="neutral" />
              </section>
              <TableBlock title="Obligaciones del período" subtitle="Obligaciones tributarias del resumen financiero." rows={reportingFinancialSummary.obligaciones.map((item, index) => ({ id: index + 1, ...item }))} empty="No hay obligaciones en este resumen." columns={[
                { label: 'Tipo', render: (row) => row.tipo },
                { label: 'Monto', render: (row) => row.monto_calculado },
                { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
              ]} />
            </>
          ) : null}

          {reportingPartnerSummary ? (
            <>
              <section className="panel-grid">
                <section className="panel">
                  <div className="section-heading"><div><h2>Socio</h2><p>{reportingPartnerSummary.socio.nombre}</p></div></div>
                  <div className="list-stack">
                    <div className="list-row"><span>RUT</span><strong>{reportingPartnerSummary.socio.rut}</strong></div>
                    <div className="list-row"><span>Email</span><strong>{reportingPartnerSummary.socio.email || 'Sin email'}</strong></div>
                    <div className="list-row"><span>Contratos directos</span><strong>{count(reportingPartnerSummary.contratos_directos_activos)}</strong></div>
                    <div className="list-row"><span>Estados cuenta</span><strong>{count(reportingPartnerSummary.estados_cuenta_relacionados)}</strong></div>
                  </div>
                </section>
                <section className="panel">
                  <div className="section-heading"><div><h2>Propiedades directas</h2><p>Visión resumida del socio seleccionado.</p></div></div>
                  <div className="list-stack">
                    {reportingPartnerSummary.propiedades_directas.map((item) => (
                      <div className="list-row" key={item.propiedad_id}><span>{item.codigo_propiedad}</span><strong>{item.estado}</strong></div>
                    ))}
                    {reportingPartnerSummary.propiedades_directas.length === 0 ? <div className="empty-state compact">Sin propiedades directas.</div> : null}
                  </div>
                </section>
              </section>
              <TableBlock title="Participaciones en empresas" subtitle="Participación patrimonial del socio." rows={reportingPartnerSummary.participaciones_empresas.map((item) => ({ id: item.empresa_id, ...item }))} empty="No hay participaciones en empresas." columns={[
                { label: 'Empresa', render: (row) => row.empresa },
                { label: 'Porcentaje', render: (row) => row.porcentaje },
              ]} />
              <TableBlock title="Participaciones en comunidades" subtitle="Participación patrimonial comunitaria del socio." rows={reportingPartnerSummary.participaciones_comunidades.map((item) => ({ id: item.comunidad_id, ...item }))} empty="No hay participaciones en comunidades." columns={[
                { label: 'Comunidad', render: (row) => row.comunidad },
                { label: 'Porcentaje', render: (row) => row.porcentaje },
              ]} />
            </>
          ) : null}

          {reportingBooksSummary ? (
            <section className="panel-grid">
              <section className="panel">
                <div className="section-heading"><div><h2>Libro diario</h2><p>{reportingBooksSummary.periodo}</p></div></div>
                <pre className="json-block">{JSON.stringify(reportingBooksSummary.libro_diario.resumen, null, 2)}</pre>
              </section>
              <section className="panel">
                <div className="section-heading"><div><h2>Libro mayor</h2><p>{reportingBooksSummary.periodo}</p></div></div>
                <pre className="json-block">{JSON.stringify(reportingBooksSummary.libro_mayor.resumen, null, 2)}</pre>
              </section>
              <section className="panel">
                <div className="section-heading"><div><h2>Balance comprobación</h2><p>{reportingBooksSummary.periodo}</p></div></div>
                <pre className="json-block">{JSON.stringify(reportingBooksSummary.balance_comprobacion.resumen, null, 2)}</pre>
              </section>
            </section>
          ) : null}

          {reportingAnnualSummary ? (
            <>
              <TableBlock title="Procesos renta anual" subtitle="Resumen consolidado por empresa." rows={reportingAnnualSummary.procesos_renta.map((item) => ({ id: item.empresa_id, ...item }))} empty="No hay procesos de renta para este filtro." columns={[
                { label: 'Empresa', render: (row) => empresaById.get(row.empresa_id)?.razon_social || row.empresa_id },
                { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
                { label: 'Preparación', render: (row) => row.fecha_preparacion || 'Sin fecha' },
              ]} />
              <TableBlock title="DDJJ preparadas" subtitle="Paquetes DDJJ por empresa." rows={reportingAnnualSummary.ddjj_preparadas.map((item) => ({ id: item.empresa_id, ...item }))} empty="No hay DDJJ para este resumen." columns={[
                { label: 'Empresa', render: (row) => empresaById.get(row.empresa_id)?.razon_social || row.empresa_id },
                { label: 'Paquete', render: (row) => row.paquete_ref || 'Sin ref' },
                { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
              ]} />
              <TableBlock title="F22 preparados" subtitle="Borradores F22 por empresa." rows={reportingAnnualSummary.f22_preparados.map((item) => ({ id: item.empresa_id, ...item }))} empty="No hay F22 para este resumen." columns={[
                { label: 'Empresa', render: (row) => empresaById.get(row.empresa_id)?.razon_social || row.empresa_id },
                { label: 'Borrador', render: (row) => row.borrador_ref || 'Sin ref' },
                { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
              ]} />
            </>
          ) : null}

          {reportingMigrationSummary ? (
            <>
              <section className="metric-grid">
                <Metric label="Resoluciones" value={count(reportingMigrationSummary.total)} tone={reportingMigrationSummary.total ? 'warning' : 'positive'} />
              </section>
              <TableBlock title="Categorías de backlog" subtitle="Conteo de resoluciones manuales por categoría." rows={reportingMigrationSummary.categorias.map((item, index) => ({ id: index + 1, ...item }))} empty="No hay categorías para este estado." columns={[
                { label: 'Categoría', render: (row) => row.category },
                { label: 'Total', render: (row) => count(row.total) },
              ]} />
              <TableBlock title="Propiedades owner manual required" subtitle="Detalle del backlog manual de migración." rows={reportingMigrationSummary.propiedades_owner_manual_required.map((item, index) => {
                const { id: _ignoredId, ...rest } = item
                return { id: index + 1, ...rest }
              })} empty="No hay propiedades manuales en este estado." columns={[
                { label: 'Código', render: (row) => row.codigo },
                { label: 'Dirección', render: (row) => row.direccion },
                { label: 'Modelo', render: (row) => row.candidate_owner_model },
                { label: 'Participaciones', render: (row) => count(row.participaciones_count) },
                { label: 'Contratos bloqueados', render: (row) => row.blocked_contract_legacy_ids.join(', ') || 'Ninguno' },
              ]} />
            </>
          ) : null}
        </>
      ) : null}
    </main>
  )
}

export default App
