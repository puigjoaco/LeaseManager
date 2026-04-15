import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import heroImage from './assets/hero.png'
import { ApiError, apiRequest, API_BASE_URL, fallbackHealth, TOKEN_STORAGE_KEY } from './backoffice/api'
import { Metric, count, toneFor } from './backoffice/shared'
import { ContextBanner, SectionToolbar, WorkspaceHeader, WorkspaceTabs } from './backoffice/shell'
import { effectiveCodeFromPropertyCode, matches, todayIso } from './backoffice/utils'
import { allowedViewsForRole, auditHeadingForRole, canMutateSection, defaultViewForRole, reportingHeadingForRole, sectionTitleForView, searchPlaceholderForView, type SectionKey, type ViewKey, VIEW_LABELS, canonicalRole } from './backoffice/view-config'
import { AuditWorkspace } from './backoffice/workspaces/AuditWorkspace'
import { CanalesWorkspace } from './backoffice/workspaces/CanalesWorkspace'
import { ComplianceWorkspace } from './backoffice/workspaces/ComplianceWorkspace'
import { CobranzaWorkspace } from './backoffice/workspaces/CobranzaWorkspace'
import { ConciliacionWorkspace } from './backoffice/workspaces/ConciliacionWorkspace'
import { ContabilidadWorkspace } from './backoffice/workspaces/ContabilidadWorkspace'
import { DocumentosWorkspace } from './backoffice/workspaces/DocumentosWorkspace'
import { ContratosWorkspace } from './backoffice/workspaces/ContratosWorkspace'
import { OperacionWorkspace } from './backoffice/workspaces/OperacionWorkspace'
import { OverviewWorkspace } from './backoffice/workspaces/OverviewWorkspace'
import { PatrimonioWorkspace } from './backoffice/workspaces/PatrimonioWorkspace'
import { ReportingWorkspace } from './backoffice/workspaces/ReportingWorkspace'
import { SiiWorkspace } from './backoffice/workspaces/SiiWorkspace'
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
  metadata: { socio_id?: number }
  assignments: Array<{ role: string; scope: string | null; is_primary: boolean }>
}

type LoginBootstrap = {
  overview?: {
    dashboard: Dashboard | null
    manual_summary: ManualSummary | null
  } | null
  control?: ControlSnapshot | null
}

type LoginResponse = { token: string; user: CurrentUser; bootstrap?: LoginBootstrap | null }
const USER_STORAGE_KEY = 'leasemanager.auth.user'
const OVERVIEW_STORAGE_KEY_PREFIX = 'leasemanager.overview'
const CONTROL_STORAGE_KEY_PREFIX = 'leasemanager.control'

const SILENT_REFRESH_VIEWS = new Set<ViewKey>([
  'patrimonio',
  'operacion',
  'contratos',
  'documentos',
  'canales',
  'cobranza',
  'conciliacion',
  'audit',
  'contabilidad',
  'sii',
])

function readStoredCurrentUser(): CurrentUser | null {
  if (typeof window === 'undefined') return null
  const rawUser = localStorage.getItem(USER_STORAGE_KEY)
  if (!rawUser) return null

  try {
    const parsed = JSON.parse(rawUser) as Partial<CurrentUser>
    if (
      typeof parsed?.id === 'number'
      && typeof parsed?.username === 'string'
      && typeof parsed?.default_role_code === 'string'
      && Array.isArray(parsed?.assignments)
    ) {
      return parsed as CurrentUser
    }
  } catch {
    // Drop invalid cached payloads and continue with a hard refresh.
  }

  localStorage.removeItem(USER_STORAGE_KEY)
  return null
}

function storeCurrentUser(user: CurrentUser | null) {
  if (typeof window === 'undefined') return
  if (!user) {
    localStorage.removeItem(USER_STORAGE_KEY)
    return
  }
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
}

function clearStoredSession() {
  if (typeof window === 'undefined') return
  localStorage.removeItem(TOKEN_STORAGE_KEY)
  localStorage.removeItem(USER_STORAGE_KEY)
}

function overviewStorageKey(user: Pick<CurrentUser, 'id' | 'username' | 'default_role_code'> | null) {
  if (!user) return null
  return `${OVERVIEW_STORAGE_KEY_PREFIX}:${user.id}:${user.username}:${user.default_role_code}`
}

function readStoredOverviewSnapshot() {
  if (typeof window === 'undefined') {
    return {
      dashboard: null as Dashboard | null,
      manualSummary: null as ManualSummary | null,
      lastLoadedAt: null as string | null,
    }
  }

  const key = overviewStorageKey(readStoredCurrentUser())
  if (!key) {
    return {
      dashboard: null as Dashboard | null,
      manualSummary: null as ManualSummary | null,
      lastLoadedAt: null as string | null,
    }
  }

  const rawSnapshot = localStorage.getItem(key)
  if (!rawSnapshot) {
    return {
      dashboard: null as Dashboard | null,
      manualSummary: null as ManualSummary | null,
      lastLoadedAt: null as string | null,
    }
  }

  try {
    const parsed = JSON.parse(rawSnapshot) as {
      dashboard?: Dashboard | null
      manualSummary?: ManualSummary | null
      lastLoadedAt?: string | null
    }
    return {
      dashboard: parsed.dashboard ?? null,
      manualSummary: parsed.manualSummary ?? null,
      lastLoadedAt: parsed.lastLoadedAt ?? null,
    }
  } catch {
    localStorage.removeItem(key)
    return {
      dashboard: null as Dashboard | null,
      manualSummary: null as ManualSummary | null,
      lastLoadedAt: null as string | null,
    }
  }
}

function storeOverviewSnapshot(
  user: Pick<CurrentUser, 'id' | 'username' | 'default_role_code'> | null,
  snapshot: {
    dashboard: Dashboard | null
    manualSummary: ManualSummary | null
    lastLoadedAt: string | null
  },
) {
  if (typeof window === 'undefined') return
  const key = overviewStorageKey(user)
  if (!key) return
  if (!snapshot.dashboard && !snapshot.manualSummary && !snapshot.lastLoadedAt) {
    localStorage.removeItem(key)
    return
  }
  localStorage.setItem(key, JSON.stringify(snapshot))
}

function controlStorageKey(user: Pick<CurrentUser, 'id' | 'username' | 'default_role_code'> | null) {
  if (!user) return null
  return `${CONTROL_STORAGE_KEY_PREFIX}:${user.id}:${user.username}:${user.default_role_code}`
}

function readStoredControlSnapshot() {
  if (typeof window === 'undefined') {
    return null as null | {
      empresas: Empresa[]
      regimenesTributarios: RegimenTributario[]
      configuracionesFiscales: ConfiguracionFiscal[]
      cuentasContables: CuentaContable[]
      reglasContables: ReglaContable[]
      matricesReglas: MatrizRegla[]
      eventosContables: EventoContable[]
      asientosContables: AsientoContable[]
      obligacionesMensuales: ObligacionMensual[]
      cierresMensuales: CierreMensual[]
      lastLoadedAt: string | null
    }
  }

  const key = controlStorageKey(readStoredCurrentUser())
  if (!key) return null

  const rawSnapshot = localStorage.getItem(key)
  if (!rawSnapshot) return null

  try {
    return JSON.parse(rawSnapshot) as {
      empresas: Empresa[]
      regimenesTributarios: RegimenTributario[]
      configuracionesFiscales: ConfiguracionFiscal[]
      cuentasContables: CuentaContable[]
      reglasContables: ReglaContable[]
      matricesReglas: MatrizRegla[]
      eventosContables: EventoContable[]
      asientosContables: AsientoContable[]
      obligacionesMensuales: ObligacionMensual[]
      cierresMensuales: CierreMensual[]
      lastLoadedAt: string | null
    }
  } catch {
    localStorage.removeItem(key)
    return null
  }
}

function storeControlSnapshot(
  user: Pick<CurrentUser, 'id' | 'username' | 'default_role_code'> | null,
  snapshot: {
    empresas: Empresa[]
    regimenesTributarios: RegimenTributario[]
    configuracionesFiscales: ConfiguracionFiscal[]
    cuentasContables: CuentaContable[]
    reglasContables: ReglaContable[]
    matricesReglas: MatrizRegla[]
    eventosContables: EventoContable[]
    asientosContables: AsientoContable[]
    obligacionesMensuales: ObligacionMensual[]
    cierresMensuales: CierreMensual[]
    lastLoadedAt: string | null
  } | null,
) {
  if (typeof window === 'undefined') return
  const key = controlStorageKey(user)
  if (!key) return
  if (!snapshot) {
    localStorage.removeItem(key)
    return
  }
  localStorage.setItem(key, JSON.stringify(snapshot))
}

function applyOverviewBootstrapSnapshot(
  user: CurrentUser,
  bootstrap: { dashboard: Dashboard | null; manual_summary: ManualSummary | null } | null | undefined,
  setters: {
    setDashboard: (value: Dashboard | null) => void
    setManualSummary: (value: ManualSummary | null) => void
    setLastLoadedAt: (value: string | null) => void
  },
) {
  if (!bootstrap) return
  const loadedAt = new Date().toISOString()
  setters.setDashboard(bootstrap.dashboard ?? null)
  setters.setManualSummary(bootstrap.manual_summary ?? null)
  setters.setLastLoadedAt(loadedAt)
  storeOverviewSnapshot(user, {
    dashboard: bootstrap.dashboard ?? null,
    manualSummary: bootstrap.manual_summary ?? null,
    lastLoadedAt: loadedAt,
  })
}

function applyControlBootstrapSnapshot(
  user: CurrentUser,
  bootstrap: ControlSnapshot | null | undefined,
  setters: {
    setEmpresas: (value: Empresa[]) => void
    setRegimenesTributarios: (value: RegimenTributario[]) => void
    setConfiguracionesFiscales: (value: ConfiguracionFiscal[]) => void
    setCuentasContables: (value: CuentaContable[]) => void
    setReglasContables: (value: ReglaContable[]) => void
    setMatricesReglas: (value: MatrizRegla[]) => void
    setEventosContables: (value: EventoContable[]) => void
    setAsientosContables: (value: AsientoContable[]) => void
    setObligacionesMensuales: (value: ObligacionMensual[]) => void
    setCierresMensuales: (value: CierreMensual[]) => void
    setIsControlCoreLoaded: (value: boolean) => void
    setIsControlCatalogLoaded: (value: boolean) => void
    setIsControlActivityLoaded: (value: boolean) => void
    setLastLoadedAt: (value: string | null) => void
  },
) {
  if (!bootstrap) return
  const loadedAt = new Date().toISOString()
  setters.setEmpresas(bootstrap.empresas)
  setters.setRegimenesTributarios(bootstrap.regimenes_tributarios)
  setters.setConfiguracionesFiscales(bootstrap.configuraciones_fiscales)
  setters.setCuentasContables(bootstrap.cuentas_contables)
  setters.setReglasContables(bootstrap.reglas_contables)
  setters.setMatricesReglas(bootstrap.matrices_reglas)
  setters.setEventosContables(bootstrap.eventos_contables)
  setters.setAsientosContables(bootstrap.asientos_contables)
  setters.setObligacionesMensuales(bootstrap.obligaciones_mensuales)
  setters.setCierresMensuales(bootstrap.cierres_mensuales)
  setters.setIsControlCoreLoaded(true)
  setters.setIsControlCatalogLoaded(
    bootstrap.cuentas_contables.length > 0
    || bootstrap.reglas_contables.length > 0
    || bootstrap.matrices_reglas.length > 0,
  )
  setters.setIsControlActivityLoaded(
    bootstrap.eventos_contables.length > 0
    || bootstrap.asientos_contables.length > 0
    || bootstrap.obligaciones_mensuales.length > 0
    || bootstrap.cierres_mensuales.length > 0,
  )
  setters.setLastLoadedAt(loadedAt)
  storeControlSnapshot(user, {
    empresas: bootstrap.empresas,
    regimenesTributarios: bootstrap.regimenes_tributarios,
    configuracionesFiscales: bootstrap.configuraciones_fiscales,
    cuentasContables: bootstrap.cuentas_contables,
    reglasContables: bootstrap.reglas_contables,
    matricesReglas: bootstrap.matrices_reglas,
    eventosContables: bootstrap.eventos_contables,
    asientosContables: bootstrap.asientos_contables,
    obligacionesMensuales: bootstrap.obligaciones_mensuales,
    cierresMensuales: bootstrap.cierres_mensuales,
    lastLoadedAt: loadedAt,
  })
}

function readStoredInitialView(): ViewKey {
  const storedUser = readStoredCurrentUser()
  return storedUser ? defaultViewForRole(canonicalRole(storedUser.default_role_code)) : 'overview'
}

type Dashboard = {
  socios_total?: number
  empresas_total?: number
  comunidades_total?: number
  propiedades_total?: number
  propiedades_activas?: number
  cuentas_total?: number
  identidades_total?: number
  mandatos_total?: number
  contratos_vigentes?: number
  contratos_futuros?: number
  pagos_pendientes?: number
  pagos_atrasados?: number
  resoluciones_manuales_abiertas?: number
  dtes_borrador?: number
  mensajes_preparados?: number
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
  tasa_ppm_vigente: string | null
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

type ExpedienteDocumental = {
  id: number
  entidad_tipo: string
  entidad_id: string
  estado: string
  owner_operativo: string
}

type PoliticaFirma = {
  id: number
  tipo_documental: string
  requiere_firma_arrendador: boolean
  requiere_firma_arrendatario: boolean
  requiere_codeudor: boolean
  requiere_notaria: boolean
  modo_firma_permitido: string
  estado: string
}

type DocumentoEmitidoItem = {
  id: number
  expediente: number
  tipo_documental: string
  version_plantilla: string
  checksum: string
  fecha_carga: string
  usuario: number | null
  origen: string
  estado: string
  storage_ref: string
  firma_arrendador_registrada: boolean
  firma_arrendatario_registrada: boolean
  firma_codeudor_registrada: boolean
  recepcion_notarial_registrada: boolean
  comprobante_notarial: number | null
}

type CanalMensajeriaItem = {
  id: number
  canal: string
  provider_key: string
  estado_gate: string
  restricciones_operativas: Record<string, unknown>
  evidencia_ref: string
}

type MensajeSalienteItem = {
  id: number
  canal: string
  canal_mensajeria: number
  identidad_envio: number | null
  contrato: number | null
  arrendatario: number | null
  documento_emitido: number | null
  destinatario: string
  asunto: string
  cuerpo: string
  estado: string
  motivo_bloqueo: string
  external_ref: string
  usuario: number | null
  provider_payload: Record<string, unknown>
  enviado_at: string | null
}

type AuditEventItem = {
  id: number
  actor_user: number | null
  actor_user_display: string
  actor_identifier: string
  event_type: string
  severity: string
  entity_type: string
  entity_id: string
  summary: string
  metadata: Record<string, unknown>
  request_id: string
  ip_address: string | null
  created_at: string
}

type ManualResolutionItem = {
  id: string
  category: string
  status: string
  scope_type: string
  scope_reference: string
  summary: string
  rationale: string
  requested_by: number | null
  requested_by_display: string
  resolved_by: number | null
  resolved_by_display: string
  metadata: Record<string, unknown>
  created_at: string
  resolved_at: string | null
}

type AuditSnapshot = {
  events: AuditEventItem[]
  manual_resolutions: ManualResolutionItem[]
}

type ReportingReferenceOptions = {
  empresas: Empresa[]
  socios: Socio[]
}

type PatrimonioSnapshot = {
  socios: Socio[]
  empresas: Empresa[]
  comunidades: Comunidad[]
  propiedades: Propiedad[]
}

type OperationSnapshot = {
  socios: Socio[]
  empresas: Empresa[]
  comunidades: Comunidad[]
  propiedades: Propiedad[]
  cuentas: Cuenta[]
  identidades: Identidad[]
  mandatos: Mandato[]
}

type ContractsSnapshot = {
  arrendatarios: Arrendatario[]
  mandatos: Mandato[]
  contratos: Contrato[]
  avisos: AvisoTermino[]
}

type DocumentsSnapshot = {
  expedientes: ExpedienteDocumental[]
  politicas_firma: PoliticaFirma[]
  documentos_emitidos: DocumentoEmitidoItem[]
}

type ChannelsSnapshot = {
  gates: CanalMensajeriaItem[]
  mensajes: MensajeSalienteItem[]
  identidades: { id: number; canal: string; remitente_visible: string; direccion_o_numero: string }[]
  contratos: { id: number; codigo_contrato: string }[]
  arrendatarios: { id: number; nombre_razon_social: string }[]
  documentos_emitidos: { id: number; tipo_documental: string; storage_ref: string }[]
}

type CobranzaSnapshot = {
  contratos: Contrato[]
  arrendatarios: Arrendatario[]
  valores_uf: ValorUF[]
  ajustes: AjusteContrato[]
  pagos: PagoMensual[]
  garantias: Garantia[]
  historial_garantias: HistorialGarantia[]
  estados_cuenta: EstadoCuenta[]
}

type ConciliacionSnapshot = {
  cuentas: { id: number; numero_cuenta: string; owner_display: string }[]
  conexiones: ConexionBancaria[]
  movimientos: MovimientoBancario[]
  ingresos_desconocidos: IngresoDesconocido[]
}

type SiiSnapshot = {
  empresas: { id: number; razon_social: string }[]
  pagos: { id: number; contrato: number; mes: number; anio: number }[]
  capacidades: CapacidadSii[]
  dtes: DteEmitido[]
  f29s: F29Preparacion[]
  procesos_anuales: ProcesoRentaAnual[]
  ddjjs: DdjjPreparacion[]
  f22s: F22Preparacion[]
}

type ControlSnapshot = {
  empresas: Empresa[]
  regimenes_tributarios: RegimenTributario[]
  configuraciones_fiscales: ConfiguracionFiscal[]
  cuentas_contables: CuentaContable[]
  reglas_contables: ReglaContable[]
  matrices_reglas: MatrizRegla[]
  eventos_contables: EventoContable[]
  asientos_contables: AsientoContable[]
  obligaciones_mensuales: ObligacionMensual[]
  cierres_mensuales: CierreMensual[]
}

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

type PoliticaRetencionDatos = {
  id: number
  categoria_dato: string
  evento_inicio: string
  plazo_minimo_anos: number
  permite_borrado_logico: boolean
  permite_purga_fisica: boolean
  requiere_hold: boolean
  estado: string
}

type ExportacionSensible = {
  id: number
  categoria_dato: string
  export_kind: string
  scope_resumen: Record<string, unknown>
  motivo: string
  payload_hash: string
  encrypted_ref: string
  expires_at: string
  hold_activo: boolean
  estado: string
  created_by: number | null
}

type ExportacionSensiblePreview = {
  id: number
  export_kind: string
  payload_hash: string
  payload: unknown
} | null

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

function App() {
  const initialView = readStoredInitialView()
  const initialOverviewSnapshot = readStoredOverviewSnapshot()
  const initialControlSnapshot = initialView === 'contabilidad' ? readStoredControlSnapshot() : null
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY))
  const [health, setHealth] = useState<HealthPayload>(fallbackHealth)
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(() => readStoredCurrentUser())
  const [dashboard, setDashboard] = useState<Dashboard | null>(initialOverviewSnapshot.dashboard)
  const [manualSummary, setManualSummary] = useState<ManualSummary | null>(initialOverviewSnapshot.manualSummary)
  const [socios, setSocios] = useState<Socio[]>([])
  const [empresas, setEmpresas] = useState<Empresa[]>(initialControlSnapshot?.empresas || [])
  const [arrendatarios, setArrendatarios] = useState<Arrendatario[]>([])
  const [comunidades, setComunidades] = useState<Comunidad[]>([])
  const [propiedades, setPropiedades] = useState<Propiedad[]>([])
  const [cuentas, setCuentas] = useState<Cuenta[]>([])
  const [identidades, setIdentidades] = useState<Identidad[]>([])
  const [mandatos, setMandatos] = useState<Mandato[]>([])
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [expedientes, setExpedientes] = useState<ExpedienteDocumental[]>([])
  const [politicasFirma, setPoliticasFirma] = useState<PoliticaFirma[]>([])
  const [documentosEmitidos, setDocumentosEmitidos] = useState<DocumentoEmitidoItem[]>([])
  const [gatesCanales, setGatesCanales] = useState<CanalMensajeriaItem[]>([])
  const [mensajesSalientes, setMensajesSalientes] = useState<MensajeSalienteItem[]>([])
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
  const [regimenesTributarios, setRegimenesTributarios] = useState<RegimenTributario[]>(initialControlSnapshot?.regimenesTributarios || [])
  const [configuracionesFiscales, setConfiguracionesFiscales] = useState<ConfiguracionFiscal[]>(initialControlSnapshot?.configuracionesFiscales || [])
  const [cuentasContables, setCuentasContables] = useState<CuentaContable[]>(initialControlSnapshot?.cuentasContables || [])
  const [reglasContables, setReglasContables] = useState<ReglaContable[]>(initialControlSnapshot?.reglasContables || [])
  const [matricesReglas, setMatricesReglas] = useState<MatrizRegla[]>(initialControlSnapshot?.matricesReglas || [])
  const [eventosContables, setEventosContables] = useState<EventoContable[]>(initialControlSnapshot?.eventosContables || [])
  const [asientosContables, setAsientosContables] = useState<AsientoContable[]>(initialControlSnapshot?.asientosContables || [])
  const [obligacionesMensuales, setObligacionesMensuales] = useState<ObligacionMensual[]>(initialControlSnapshot?.obligacionesMensuales || [])
  const [cierresMensuales, setCierresMensuales] = useState<CierreMensual[]>(initialControlSnapshot?.cierresMensuales || [])
  const [auditEvents, setAuditEvents] = useState<AuditEventItem[]>([])
  const [manualResolutions, setManualResolutions] = useState<ManualResolutionItem[]>([])
  const [capacidadesSii, setCapacidadesSii] = useState<CapacidadSii[]>([])
  const [dtes, setDtes] = useState<DteEmitido[]>([])
  const [f29s, setF29s] = useState<F29Preparacion[]>([])
  const [procesosAnuales, setProcesosAnuales] = useState<ProcesoRentaAnual[]>([])
  const [ddjjs, setDdjjs] = useState<DdjjPreparacion[]>([])
  const [f22s, setF22s] = useState<F22Preparacion[]>([])
  const [compliancePolicies, setCompliancePolicies] = useState<PoliticaRetencionDatos[]>([])
  const [complianceExports, setComplianceExports] = useState<ExportacionSensible[]>([])
  const [complianceExportPreview, setComplianceExportPreview] = useState<ExportacionSensiblePreview>(null)
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [workspaceError, setWorkspaceError] = useState<string | null>(null)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastLoadedAt, setLastLoadedAt] = useState<string | null>(initialOverviewSnapshot.lastLoadedAt ?? initialControlSnapshot?.lastLoadedAt ?? null)
  const [activeView, setActiveView] = useState<ViewKey>(initialView)
  const [activeContextLabel, setActiveContextLabel] = useState<string | null>(null)
  const [searchText, setSearchText] = useState('')
  const [formMessage, setFormMessage] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [editingSocioId, setEditingSocioId] = useState<number | null>(null)
  const [editingPropiedadId, setEditingPropiedadId] = useState<number | null>(null)
  const [editingCuentaId, setEditingCuentaId] = useState<number | null>(null)
  const [editingMandatoId, setEditingMandatoId] = useState<number | null>(null)
  const [editingConfigFiscalId, setEditingConfigFiscalId] = useState<number | null>(null)
  const [editingArrendatarioId, setEditingArrendatarioId] = useState<number | null>(null)
  const [editingContratoId, setEditingContratoId] = useState<number | null>(null)
  const [editingExpedienteId, setEditingExpedienteId] = useState<number | null>(null)
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
  const [expedienteDraft, setExpedienteDraft] = useState({
    entidad_tipo: 'contrato',
    entidad_id: '',
    estado: 'abierto',
    owner_operativo: '',
  })
  const [politicaFirmaDraft, setPoliticaFirmaDraft] = useState({
    tipo_documental: 'contrato_principal',
    requiere_firma_arrendador: true,
    requiere_firma_arrendatario: true,
    requiere_codeudor: false,
    requiere_notaria: false,
    modo_firma_permitido: 'firma_simple',
    estado: 'activa',
  })
  const [documentoDraft, setDocumentoDraft] = useState({
    expediente: '',
    tipo_documental: 'contrato_principal',
    version_plantilla: 'v1',
    checksum: '',
    fecha_carga: `${todayIso()}T12:00`,
    origen: 'generado_sistema',
    estado: 'emitido',
    storage_ref: '',
    firma_arrendador_registrada: false,
    firma_arrendatario_registrada: false,
    firma_codeudor_registrada: false,
    recepcion_notarial_registrada: false,
    comprobante_notarial: '',
  })
  const [documentoFormalizarDraft, setDocumentoFormalizarDraft] = useState({
    documentoId: '',
    firma_arrendador_registrada: true,
    firma_arrendatario_registrada: true,
    firma_codeudor_registrada: false,
    recepcion_notarial_registrada: false,
    comprobante_notarial: '',
  })
  const [gateCanalDraft, setGateCanalDraft] = useState({
    canal: 'email',
    provider_key: 'gmail_api',
    estado_gate: 'condicionado',
    evidencia_ref: '',
  })
  const [mensajeDraft, setMensajeDraft] = useState({
    canal: 'email',
    canal_mensajeria: '',
    identidad_envio: '',
    contrato: '',
    arrendatario: '',
    documento_emitido: '',
    asunto: '',
    cuerpo: '',
  })
  const [mensajeEnvioDraft, setMensajeEnvioDraft] = useState({
    mensajeId: '',
    external_ref: '',
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
    tasa_ppm_vigente: '',
    ddjj_habilitadas_text: '',
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
  const [editingManualResolutionId, setEditingManualResolutionId] = useState<string | null>(null)
  const [isPatrimonioSnapshotLoading, setIsPatrimonioSnapshotLoading] = useState(false)
  const [isOperationSnapshotLoading, setIsOperationSnapshotLoading] = useState(false)
  const [isContractsSnapshotLoading, setIsContractsSnapshotLoading] = useState(false)
  const [isDocumentsSnapshotLoading, setIsDocumentsSnapshotLoading] = useState(false)
  const [isChannelsSnapshotLoading, setIsChannelsSnapshotLoading] = useState(false)
  const [isCobranzaSnapshotLoading, setIsCobranzaSnapshotLoading] = useState(false)
  const [isConciliacionSnapshotLoading, setIsConciliacionSnapshotLoading] = useState(false)
  const [isSiiSnapshotLoading, setIsSiiSnapshotLoading] = useState(false)
  const [isAuditSnapshotLoading, setIsAuditSnapshotLoading] = useState(false)
  const [isControlCatalogLoading, setIsControlCatalogLoading] = useState(false)
  const [isControlActivityLoading, setIsControlActivityLoading] = useState(false)
  const [isOperationSnapshotLoaded, setIsOperationSnapshotLoaded] = useState(false)
  const [isContractsSnapshotLoaded, setIsContractsSnapshotLoaded] = useState(false)
  const [isDocumentsSnapshotLoaded, setIsDocumentsSnapshotLoaded] = useState(false)
  const [isChannelsSnapshotLoaded, setIsChannelsSnapshotLoaded] = useState(false)
  const [isCobranzaSnapshotLoaded, setIsCobranzaSnapshotLoaded] = useState(false)
  const [isConciliacionSnapshotLoaded, setIsConciliacionSnapshotLoaded] = useState(false)
  const [isSiiSnapshotLoaded, setIsSiiSnapshotLoaded] = useState(false)
  const [isAuditSnapshotLoaded, setIsAuditSnapshotLoaded] = useState(false)
  const [isControlCoreLoaded, setIsControlCoreLoaded] = useState(Boolean(initialControlSnapshot))
  const [isControlCatalogLoaded, setIsControlCatalogLoaded] = useState(Boolean(initialControlSnapshot?.cuentasContables.length || initialControlSnapshot?.reglasContables.length || initialControlSnapshot?.matricesReglas.length))
  const [isControlActivityLoaded, setIsControlActivityLoaded] = useState(Boolean(initialControlSnapshot?.eventosContables.length || initialControlSnapshot?.asientosContables.length || initialControlSnapshot?.obligacionesMensuales.length || initialControlSnapshot?.cierresMensuales.length))
  const [isReportingReferencesLoaded, setIsReportingReferencesLoaded] = useState(false)
  const [isComplianceLoaded, setIsComplianceLoaded] = useState(false)
  const [isPatrimonioSnapshotLoaded, setIsPatrimonioSnapshotLoaded] = useState(false)
  const seededControlRefreshPendingRef = useRef(Boolean(initialControlSnapshot))
  const [manualResolutionDraft, setManualResolutionDraft] = useState({
    status: 'open',
    rationale: '',
  })
  const [politicaRetencionDraft, setPoliticaRetencionDraft] = useState({
    categoria_dato: 'financiero',
    evento_inicio: 'ultimo_evento_relevante',
    plazo_minimo_anos: '6',
    permite_borrado_logico: true,
    permite_purga_fisica: false,
    requiere_hold: false,
    estado: 'activa',
  })
  const [exportacionPrepareDraft, setExportacionPrepareDraft] = useState({
    categoria_dato: 'financiero',
    export_kind: 'financiero_mensual',
    motivo: '',
    hold_activo: false,
    anio: '2026',
    mes: '5',
    anio_tributario: '2027',
    empresa_id: '',
    socio_id: '',
    periodo: '2026-05',
  })

  const effectiveRole = canonicalRole(currentUser?.default_role_code)
  const activeAssignments = currentUser?.assignments || []
  const reportingHeading = reportingHeadingForRole(effectiveRole)
  const auditHeading = auditHeadingForRole(effectiveRole)
  const apiConfigError = !API_BASE_URL ? 'Falta conectar el backend canónico para este entorno. Configura VITE_API_BASE_URL para habilitar el acceso.' : null
  const visibleTabs = allowedViewsForRole(effectiveRole).map((view) => ({ key: view, label: VIEW_LABELS[view] }))
  const currentSectionTag = VIEW_LABELS[activeView]
  const currentSectionTitle = sectionTitleForView(activeView, auditHeading.title, reportingHeading.title)
  const currentSearchPlaceholder = searchPlaceholderForView(activeView, reportingHeading.placeholder)

  function canAccessView(view: ViewKey) {
    return allowedViewsForRole(effectiveRole).includes(view)
  }

  const canEditPatrimonio = canMutateSection(effectiveRole, 'patrimonio')
  const canEditOperacion = canMutateSection(effectiveRole, 'operacion')
  const canEditContratos = canMutateSection(effectiveRole, 'contratos')
  const canEditDocumentos = canMutateSection(effectiveRole, 'documentos')
  const canEditCanales = canMutateSection(effectiveRole, 'canales')
  const canEditCobranza = canMutateSection(effectiveRole, 'cobranza')
  const canEditConciliacion = canMutateSection(effectiveRole, 'conciliacion')
  const canEditAudit = canMutateSection(effectiveRole, 'audit')
  const canEditContabilidad = canMutateSection(effectiveRole, 'contabilidad')
  const canEditSii = canMutateSection(effectiveRole, 'sii')
  const canEditCompliance = canMutateSection(effectiveRole, 'compliance')

  async function loadHealth() {
    try {
      setHealth(await apiRequest<HealthPayload>('/api/v1/health/'))
    } catch {
      setHealth(fallbackHealth)
    }
  }

  async function loadWorkspace(activeToken: string, options: { forceUserRefresh?: boolean; forceDataRefresh?: boolean } = {}) {
    const shouldShowGlobalRefresh = Boolean(
      options.forceUserRefresh
      || options.forceDataRefresh
      || !currentUser
      || !SILENT_REFRESH_VIEWS.has(activeView),
    )
    if (shouldShowGlobalRefresh) {
      setIsRefreshing(true)
    }
    setWorkspaceError(null)
    try {
      const shouldRefreshUser = options.forceUserRefresh || !currentUser
      const me = shouldRefreshUser
        ? await apiRequest<CurrentUser>('/api/v1/auth/me/', { token: activeToken })
        : currentUser
      if (!me) {
        throw new Error('No se pudo resolver la sesión actual.')
      }
      const role = canonicalRole(me.default_role_code)
      const canReadOverview = role === 'AdministradorGlobal' || role === 'OperadorDeCartera'
      const canReadOperational = role === 'AdministradorGlobal' || role === 'OperadorDeCartera'
      const canReadAuditEvents = role === 'AdministradorGlobal' || role === 'RevisorFiscalExterno'
      const canReadManualResolutions = role === 'AdministradorGlobal' || role === 'OperadorDeCartera'
      const canReadControl = role === 'AdministradorGlobal' || role === 'RevisorFiscalExterno'
      const canReadCompliance = role === 'AdministradorGlobal'
      const canReadOwnPartnerSummary = role === 'Socio'
      const shouldRefreshData = Boolean(options.forceDataRefresh)
      const targetView = allowedViewsForRole(role).includes(activeView) ? activeView : defaultViewForRole(role)
      const loadOverview = canReadOverview && targetView === 'overview'
      const loadPatrimonioSnapshot = canReadOperational && targetView === 'patrimonio' && (shouldRefreshData || !isPatrimonioSnapshotLoaded)
      const loadOperationSnapshot = canReadOperational && targetView === 'operacion' && (shouldRefreshData || !isOperationSnapshotLoaded)
      const loadContractsSnapshot = canReadOperational && targetView === 'contratos' && (shouldRefreshData || !isContractsSnapshotLoaded)
      const loadDocumentsSnapshot = canReadOperational && targetView === 'documentos' && (shouldRefreshData || !isDocumentsSnapshotLoaded)
      const loadChannelsSnapshot = canReadOperational && targetView === 'canales' && (shouldRefreshData || !isChannelsSnapshotLoaded)
      const loadCobranzaSnapshot = canReadOperational && targetView === 'cobranza' && (shouldRefreshData || !isCobranzaSnapshotLoaded)
      const loadConciliacionSnapshot = canReadOperational && targetView === 'conciliacion' && (shouldRefreshData || !isConciliacionSnapshotLoaded)
      const loadSiiSnapshot = canReadControl && targetView === 'sii' && (shouldRefreshData || !isSiiSnapshotLoaded)
      const loadAuditSnapshot = (canReadAuditEvents || canReadManualResolutions) && targetView === 'audit' && (shouldRefreshData || !isAuditSnapshotLoaded)
      const loadSocios =
        (canReadOperational || canReadCompliance)
        && ['compliance'].includes(targetView)
      const loadEmpresas =
        (canReadCompliance && targetView === 'compliance')
      const loadReportingReferences = canReadControl && targetView === 'reporting' && (shouldRefreshData || !isReportingReferencesLoaded)
      const loadComunidades = false
      const loadPropiedades = false
      const loadCuentas = canReadOperational && ['conciliacion'].includes(targetView)
      const loadIdentidades = canReadOperational && ['canales'].includes(targetView)
      const loadMandatos = false
      const loadControlCore = canReadControl && targetView === 'contabilidad' && (shouldRefreshData || !isControlCoreLoaded)
      const loadControlCatalog = canReadControl && targetView === 'contabilidad' && (shouldRefreshData || !isControlCatalogLoaded)
      const loadControlActivity = canReadControl && targetView === 'contabilidad' && (shouldRefreshData || !isControlActivityLoaded)
      const bootstrapCompliance = canReadCompliance && targetView === 'compliance' && (shouldRefreshData || !isComplianceLoaded)
      setIsPatrimonioSnapshotLoading(loadPatrimonioSnapshot)
      setIsOperationSnapshotLoading(loadOperationSnapshot)
      setIsContractsSnapshotLoading(loadContractsSnapshot)
      setIsDocumentsSnapshotLoading(loadDocumentsSnapshot)
      setIsChannelsSnapshotLoading(loadChannelsSnapshot)
      setIsCobranzaSnapshotLoading(loadCobranzaSnapshot)
      setIsConciliacionSnapshotLoading(loadConciliacionSnapshot)
      setIsSiiSnapshotLoading(loadSiiSnapshot)
      setIsAuditSnapshotLoading(loadAuditSnapshot)
      setIsControlCatalogLoading(loadControlCatalog)
      setIsControlActivityLoading(loadControlActivity)
      setCurrentUser(me)
      storeCurrentUser(me)
      setActiveView((current) => (
        allowedViewsForRole(role).includes(current) ? current : defaultViewForRole(role)
      ))

      async function requestIf<T>(enabled: boolean, path: string, fallback: T): Promise<T> {
        if (!enabled) return fallback
        return apiRequest<T>(path, { token: activeToken })
      }

      function withRefreshParam(path: string) {
        if (!shouldRefreshData) return path
        return `${path}${path.includes('?') ? '&' : '?'}refresh=1`
      }

      const controlCatalogRequest = loadControlCatalog
        ? requestIf<ControlSnapshot | null>(
          true,
          withRefreshParam('/api/v1/contabilidad/snapshot/?mode=catalogs'),
          null,
        ).catch(() => null)
        : Promise.resolve<ControlSnapshot | null>(null)
      const controlActivityRequest = loadControlActivity
        ? requestIf<ControlSnapshot | null>(
          true,
          withRefreshParam('/api/v1/contabilidad/snapshot/?mode=activity'),
          null,
        ).catch(() => null)
        : Promise.resolve<ControlSnapshot | null>(null)

      const [
        dashboardPayload,
        manualPayload,
        sociosPayload,
        empresasPayload,
        comunidadesPayload,
        propiedadesPayload,
        patrimonioSnapshotPayload,
        cuentasPayload,
        identidadesPayload,
        mandatosPayload,
        operationSnapshotPayload,
        contractsSnapshotPayload,
        documentsSnapshotPayload,
        channelsSnapshotPayload,
        cobranzaSnapshotPayload,
        conciliacionSnapshotPayload,
        siiSnapshotPayload,
        auditSnapshotPayload,
        controlSnapshotPayload,
        reportingReferencePayload,
        compliancePoliciesPayload,
        complianceExportsPayload,
        ownPartnerSummary,
      ] = await Promise.all([
        requestIf<Dashboard | null>(loadOverview, withRefreshParam('/api/v1/reporting/dashboard/operativo/?mode=summary'), dashboard),
        manualSummary,
        requestIf<Socio[]>(loadSocios, '/api/v1/patrimonio/socios/', socios),
        requestIf<Empresa[]>(loadEmpresas, '/api/v1/patrimonio/empresas/', empresas),
        requestIf<Comunidad[]>(loadComunidades, '/api/v1/patrimonio/comunidades/', comunidades),
        requestIf<Propiedad[]>(loadPropiedades, '/api/v1/patrimonio/propiedades/', propiedades),
        requestIf<PatrimonioSnapshot | null>(
          loadPatrimonioSnapshot,
          '/api/v1/patrimonio/snapshot/',
          null,
        ),
        requestIf<Cuenta[]>(loadCuentas, '/api/v1/operacion/cuentas-recaudadoras/', cuentas),
        requestIf<Identidad[]>(loadIdentidades, '/api/v1/operacion/identidades-envio/', identidades),
        requestIf<Mandato[]>(loadMandatos, '/api/v1/operacion/mandatos/', mandatos),
        requestIf<OperationSnapshot | null>(
          loadOperationSnapshot,
          '/api/v1/operacion/snapshot/',
          null,
        ),
        requestIf<ContractsSnapshot | null>(
          loadContractsSnapshot,
          '/api/v1/contratos/snapshot/',
          null,
        ),
        requestIf<DocumentsSnapshot | null>(
          loadDocumentsSnapshot,
          '/api/v1/documentos/snapshot/',
          null,
        ),
        requestIf<ChannelsSnapshot | null>(
          loadChannelsSnapshot,
          '/api/v1/canales/snapshot/',
          null,
        ),
        requestIf<CobranzaSnapshot | null>(
          loadCobranzaSnapshot,
          '/api/v1/cobranza/snapshot/',
          null,
        ),
        requestIf<ConciliacionSnapshot | null>(
          loadConciliacionSnapshot,
          '/api/v1/conciliacion/snapshot/',
          null,
        ),
        requestIf<SiiSnapshot | null>(
          loadSiiSnapshot,
          '/api/v1/sii/snapshot/',
          null,
        ),
        requestIf<AuditSnapshot | null>(
          loadAuditSnapshot,
          '/api/v1/audit/snapshot/',
          null,
        ),
        requestIf<ControlSnapshot | null>(
          loadControlCore,
          withRefreshParam('/api/v1/contabilidad/snapshot/?mode=core'),
          null,
        ),
        requestIf<ReportingReferenceOptions | null>(
          loadReportingReferences,
          '/api/v1/reporting/references/',
          null,
        ),
        requestIf<PoliticaRetencionDatos[]>(bootstrapCompliance, '/api/v1/compliance/politicas-retencion/', compliancePolicies),
        requestIf<ExportacionSensible[]>(bootstrapCompliance, '/api/v1/compliance/exportes/', complianceExports),
        requestIf<ReportingPartnerSummary | null>(
          canReadOwnPartnerSummary && typeof me.metadata?.socio_id === 'number',
          `/api/v1/reporting/socios/${me.metadata.socio_id}/resumen/`,
          reportingPartnerSummary,
        ),
      ])
      setDashboard(dashboardPayload)
      setManualSummary(manualPayload)
      setSocios(sociosPayload)
      setEmpresas(empresasPayload)
      setComunidades(comunidadesPayload)
      setPropiedades(propiedadesPayload)
      if (patrimonioSnapshotPayload) {
        setSocios(patrimonioSnapshotPayload.socios)
        setEmpresas(patrimonioSnapshotPayload.empresas)
        setComunidades(patrimonioSnapshotPayload.comunidades)
        setPropiedades(patrimonioSnapshotPayload.propiedades)
        setIsPatrimonioSnapshotLoaded(true)
      }
      setCuentas(cuentasPayload)
      setIdentidades(identidadesPayload)
      setMandatos(mandatosPayload)
      if (operationSnapshotPayload) {
        setSocios(operationSnapshotPayload.socios)
        setEmpresas(operationSnapshotPayload.empresas)
        setComunidades(operationSnapshotPayload.comunidades)
        setPropiedades(operationSnapshotPayload.propiedades)
        setCuentas(operationSnapshotPayload.cuentas)
        setIdentidades(operationSnapshotPayload.identidades)
        setMandatos(operationSnapshotPayload.mandatos)
        setIsOperationSnapshotLoaded(true)
      }
      if (contractsSnapshotPayload) {
        setArrendatarios(contractsSnapshotPayload.arrendatarios)
        setMandatos(contractsSnapshotPayload.mandatos)
        setContratos(contractsSnapshotPayload.contratos)
        setAvisos(contractsSnapshotPayload.avisos)
        setIsContractsSnapshotLoaded(true)
      }
      if (documentsSnapshotPayload) {
        setExpedientes(documentsSnapshotPayload.expedientes)
        setPoliticasFirma(documentsSnapshotPayload.politicas_firma)
        setDocumentosEmitidos(documentsSnapshotPayload.documentos_emitidos)
        setIsDocumentsSnapshotLoaded(true)
      }
      if (channelsSnapshotPayload) {
        setGatesCanales(channelsSnapshotPayload.gates)
        setMensajesSalientes(channelsSnapshotPayload.mensajes)
        setIdentidades(channelsSnapshotPayload.identidades as Identidad[])
        setContratos(channelsSnapshotPayload.contratos as Contrato[])
        setArrendatarios(channelsSnapshotPayload.arrendatarios as Arrendatario[])
        setDocumentosEmitidos(channelsSnapshotPayload.documentos_emitidos as DocumentoEmitidoItem[])
        setIsChannelsSnapshotLoaded(true)
      }
      if (cobranzaSnapshotPayload) {
        setContratos(cobranzaSnapshotPayload.contratos)
        setArrendatarios(cobranzaSnapshotPayload.arrendatarios)
        setValoresUf(cobranzaSnapshotPayload.valores_uf)
        setAjustes(cobranzaSnapshotPayload.ajustes)
        setPagos(cobranzaSnapshotPayload.pagos)
        setGarantias(cobranzaSnapshotPayload.garantias)
        setHistorialGarantias(cobranzaSnapshotPayload.historial_garantias)
        setEstadosCuenta(cobranzaSnapshotPayload.estados_cuenta)
        setIsCobranzaSnapshotLoaded(true)
      }
      if (conciliacionSnapshotPayload) {
        setCuentas(conciliacionSnapshotPayload.cuentas as Cuenta[])
        setConexionesBancarias(conciliacionSnapshotPayload.conexiones)
        setMovimientosBancarios(conciliacionSnapshotPayload.movimientos)
        setIngresosDesconocidos(conciliacionSnapshotPayload.ingresos_desconocidos)
        setIsConciliacionSnapshotLoaded(true)
      }
      if (siiSnapshotPayload) {
        setEmpresas(siiSnapshotPayload.empresas as Empresa[])
        setPagos(siiSnapshotPayload.pagos as PagoMensual[])
        setCapacidadesSii(siiSnapshotPayload.capacidades)
        setDtes(siiSnapshotPayload.dtes)
        setF29s(siiSnapshotPayload.f29s)
        setProcesosAnuales(siiSnapshotPayload.procesos_anuales)
        setDdjjs(siiSnapshotPayload.ddjjs)
        setF22s(siiSnapshotPayload.f22s)
        setIsSiiSnapshotLoaded(true)
      }
      if (auditSnapshotPayload) {
        setAuditEvents(auditSnapshotPayload.events)
        setManualResolutions(auditSnapshotPayload.manual_resolutions)
        setIsAuditSnapshotLoaded(true)
      }
      if (controlSnapshotPayload?.empresas?.length) {
        setEmpresas(controlSnapshotPayload.empresas)
      } else if (reportingReferencePayload?.empresas?.length) {
        setEmpresas(reportingReferencePayload.empresas)
      }
      if (reportingReferencePayload?.socios?.length) {
        setSocios(reportingReferencePayload.socios)
      }
      if (controlSnapshotPayload) {
        setRegimenesTributarios(controlSnapshotPayload.regimenes_tributarios)
        setConfiguracionesFiscales(controlSnapshotPayload.configuraciones_fiscales)
        setCuentasContables(controlSnapshotPayload.cuentas_contables)
        setReglasContables(controlSnapshotPayload.reglas_contables)
        setMatricesReglas(controlSnapshotPayload.matrices_reglas)
        setEventosContables(controlSnapshotPayload.eventos_contables)
        setAsientosContables(controlSnapshotPayload.asientos_contables)
        setObligacionesMensuales(controlSnapshotPayload.obligaciones_mensuales)
        setCierresMensuales(controlSnapshotPayload.cierres_mensuales)
      }
      if (bootstrapCompliance) {
        setCompliancePolicies(compliancePoliciesPayload)
        setComplianceExports(complianceExportsPayload)
      }
      if (controlSnapshotPayload) setIsControlCoreLoaded(true)
      if (reportingReferencePayload) setIsReportingReferencesLoaded(true)
      if (bootstrapCompliance) setIsComplianceLoaded(true)
      setIsPatrimonioSnapshotLoading(false)
      setIsOperationSnapshotLoading(false)
      if (ownPartnerSummary) {
        setReportingPartnerSummary(ownPartnerSummary)
        setReportingPartnerDraft({ socio_id: String(ownPartnerSummary.socio.id) })
        setSocios([
          {
            id: ownPartnerSummary.socio.id,
            nombre: ownPartnerSummary.socio.nombre,
            rut: ownPartnerSummary.socio.rut,
            email: ownPartnerSummary.socio.email || '',
            telefono: '',
            domicilio: '',
            activo: true,
          },
        ])
      }
      setLastLoadedAt(new Date().toISOString())

      void (async () => {
        if (loadOverview) {
          void (async () => {
            try {
              const secondaryCounts = await requestIf<Partial<Dashboard> | null>(
                true,
                withRefreshParam('/api/v1/reporting/dashboard/overview-secondary/'),
                null,
              )
              if (secondaryCounts) {
                setDashboard((current) => ({ ...(current || {}), ...secondaryCounts }))
              }
            } catch {
              // Keep the lightweight overview instead of surfacing a secondary-count failure.
            }
          })()

          void (async () => {
            try {
              const manualSummaryPayload = await requestIf<ManualSummary | null>(
                true,
                withRefreshParam('/api/v1/reporting/migracion/resoluciones-manuales/?status=open'),
                null,
              )
              if (manualSummaryPayload) {
                setManualSummary(manualSummaryPayload)
              }
            } catch {
              // Keep the summary-first overview even if manual resolution details arrive late.
            }
          })()
        }

        const loadArrendatarios = canReadOperational && ['canales'].includes(targetView)
        const loadContratos = canReadOperational && ['canales', 'sii'].includes(targetView)
        const loadExpedientes = canReadOperational && false
        const loadPoliticasFirma = canReadOperational && false
        const loadDocumentosEmitidos = false
        const loadGatesCanales = false
        const loadMensajesSalientes = false
        const loadAvisos = false
        const loadValoresUf = canReadOperational && false
        const loadAjustes = canReadOperational && false
        const loadPagos = false
        const loadGarantias = canReadOperational && false
        const loadHistorialGarantias = canReadOperational && false
        const loadEstadosCuenta = canReadOperational && false
        const loadConexiones = false
        const loadMovimientos = false
        const loadIngresos = false
        const loadAuditEvents = false
        const loadManualResolutions = false

        if (loadControlCatalog) {
          void (async () => {
            try {
              const controlCatalogSnapshot = await controlCatalogRequest
              if (controlCatalogSnapshot) {
                setCuentasContables(controlCatalogSnapshot.cuentas_contables)
                setReglasContables(controlCatalogSnapshot.reglas_contables)
                setMatricesReglas(controlCatalogSnapshot.matrices_reglas)
                setIsControlCatalogLoaded(true)
              }
            } finally {
              setIsControlCatalogLoading(false)
            }
          })()
        } else {
          setIsControlCatalogLoading(false)
        }

        if (loadControlActivity) {
          void (async () => {
            try {
              const controlActivitySnapshot = await controlActivityRequest
              if (controlActivitySnapshot) {
                setEventosContables(controlActivitySnapshot.eventos_contables)
                setAsientosContables(controlActivitySnapshot.asientos_contables)
                setObligacionesMensuales(controlActivitySnapshot.obligaciones_mensuales)
                setCierresMensuales(controlActivitySnapshot.cierres_mensuales)
                setIsControlActivityLoaded(true)
              }
            } finally {
              setIsControlActivityLoading(false)
            }
          })()
        } else {
          setIsControlActivityLoading(false)
        }

        try {
          const settled = await Promise.allSettled([
            requestIf<Arrendatario[]>(loadArrendatarios, '/api/v1/contratos/arrendatarios/', arrendatarios),
            requestIf<Contrato[]>(loadContratos, '/api/v1/contratos/contratos/', contratos),
            requestIf<ExpedienteDocumental[]>(loadExpedientes, '/api/v1/documentos/expedientes/', expedientes),
            requestIf<PoliticaFirma[]>(loadPoliticasFirma, '/api/v1/documentos/politicas-firma/', politicasFirma),
            requestIf<DocumentoEmitidoItem[]>(loadDocumentosEmitidos, '/api/v1/documentos/documentos-emitidos/', documentosEmitidos),
            requestIf<CanalMensajeriaItem[]>(loadGatesCanales, '/api/v1/canales/gates/', gatesCanales),
            requestIf<MensajeSalienteItem[]>(loadMensajesSalientes, '/api/v1/canales/mensajes/', mensajesSalientes),
            requestIf<AvisoTermino[]>(loadAvisos, '/api/v1/contratos/avisos-termino/', avisos),
            requestIf<ValorUF[]>(loadValoresUf, '/api/v1/cobranza/valores-uf/', valoresUf),
            requestIf<AjusteContrato[]>(loadAjustes, '/api/v1/cobranza/ajustes-contrato/', ajustes),
            requestIf<PagoMensual[]>(loadPagos, '/api/v1/cobranza/pagos-mensuales/', pagos),
            requestIf<Garantia[]>(loadGarantias, '/api/v1/cobranza/garantias/', garantias),
            requestIf<HistorialGarantia[]>(loadHistorialGarantias, '/api/v1/cobranza/historial-garantias/', historialGarantias),
            requestIf<EstadoCuenta[]>(loadEstadosCuenta, '/api/v1/cobranza/estados-cuenta/', estadosCuenta),
            requestIf<ConexionBancaria[]>(loadConexiones, '/api/v1/conciliacion/conexiones-bancarias/', conexionesBancarias),
            requestIf<MovimientoBancario[]>(loadMovimientos, '/api/v1/conciliacion/movimientos/', movimientosBancarios),
            requestIf<IngresoDesconocido[]>(loadIngresos, '/api/v1/conciliacion/ingresos-desconocidos/', ingresosDesconocidos),
            requestIf<AuditEventItem[]>(loadAuditEvents, '/api/v1/audit/events/', auditEvents),
            requestIf<ManualResolutionItem[]>(loadManualResolutions, '/api/v1/audit/manual-resolutions/', manualResolutions),
          ])

          function resolvedValue<T>(index: number, fallback: T): T {
            const item = settled[index]
            return item.status === 'fulfilled' ? (item.value as T) : fallback
          }

          const arrendatariosPayload = resolvedValue<Arrendatario[]>(0, arrendatarios)
          const contratosPayload = resolvedValue<Contrato[]>(1, contratos)
          const expedientesPayload = resolvedValue<ExpedienteDocumental[]>(2, expedientes)
          const politicasFirmaPayload = resolvedValue<PoliticaFirma[]>(3, politicasFirma)
          const documentosEmitidosPayload = resolvedValue<DocumentoEmitidoItem[]>(4, documentosEmitidos)
          const gatesCanalesPayload = resolvedValue<CanalMensajeriaItem[]>(5, gatesCanales)
          const mensajesSalientesPayload = resolvedValue<MensajeSalienteItem[]>(6, mensajesSalientes)
          const avisosPayload = resolvedValue<AvisoTermino[]>(7, avisos)
          const valoresUfPayload = resolvedValue<ValorUF[]>(8, valoresUf)
          const ajustesPayload = resolvedValue<AjusteContrato[]>(9, ajustes)
          const pagosPayload = resolvedValue<PagoMensual[]>(10, pagos)
          const garantiasPayload = resolvedValue<Garantia[]>(11, garantias)
          const historialGarantiasPayload = resolvedValue<HistorialGarantia[]>(12, historialGarantias)
          const estadosCuentaPayload = resolvedValue<EstadoCuenta[]>(13, estadosCuenta)
          const conexionesPayload = resolvedValue<ConexionBancaria[]>(14, conexionesBancarias)
          const movimientosPayload = resolvedValue<MovimientoBancario[]>(15, movimientosBancarios)
          const ingresosPayload = resolvedValue<IngresoDesconocido[]>(16, ingresosDesconocidos)
          const auditEventsPayload = resolvedValue<AuditEventItem[]>(17, auditEvents)
          const manualResolutionsPayload = resolvedValue<ManualResolutionItem[]>(18, manualResolutions)

          setArrendatarios(arrendatariosPayload)
          setContratos(contratosPayload)
          setExpedientes(expedientesPayload)
          setPoliticasFirma(politicasFirmaPayload)
          setDocumentosEmitidos(documentosEmitidosPayload)
          setGatesCanales(gatesCanalesPayload)
          setMensajesSalientes(mensajesSalientesPayload)
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
          setAuditEvents(auditEventsPayload)
          setManualResolutions(manualResolutionsPayload)
          setLastLoadedAt(new Date().toISOString())
        } catch (error) {
          if (error instanceof ApiError && error.status === 401) {
            clearStoredSession()
            setToken(null)
            setCurrentUser(null)
            setWorkspaceError('La sesión expiró. Ingresa nuevamente.')
          }
        }
      })()
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearStoredSession()
        setToken(null)
        setCurrentUser(null)
        setWorkspaceError('La sesión expiró. Ingresa nuevamente.')
        return
      }
      setWorkspaceError(error instanceof Error ? error.message : 'No se pudo cargar el workspace.')
    } finally {
      setIsPatrimonioSnapshotLoading(false)
      setIsOperationSnapshotLoading(false)
      setIsContractsSnapshotLoading(false)
      setIsDocumentsSnapshotLoading(false)
      setIsChannelsSnapshotLoading(false)
      setIsCobranzaSnapshotLoading(false)
      setIsConciliacionSnapshotLoading(false)
      if (shouldShowGlobalRefresh) {
        setIsRefreshing(false)
      }
    }
  }

  useEffect(() => {
    void loadHealth()
  }, [])

  useEffect(() => {
    if (!token) {
      setCurrentUser(null)
      storeCurrentUser(null)
      return
    }
    const forceSeededControlRefresh = activeView === 'contabilidad' && seededControlRefreshPendingRef.current
    if (forceSeededControlRefresh) {
      seededControlRefreshPendingRef.current = false
    }
    void loadWorkspace(token, forceSeededControlRefresh ? { forceDataRefresh: true } : undefined)
  }, [token, activeView])

  useEffect(() => {
    storeOverviewSnapshot(currentUser, { dashboard, manualSummary, lastLoadedAt })
  }, [currentUser, dashboard, manualSummary, lastLoadedAt])

  useEffect(() => {
    const hasControlPayload =
      empresas.length > 0
      || regimenesTributarios.length > 0
      || configuracionesFiscales.length > 0
      || cuentasContables.length > 0
      || reglasContables.length > 0
      || matricesReglas.length > 0
      || eventosContables.length > 0
      || asientosContables.length > 0
      || obligacionesMensuales.length > 0
      || cierresMensuales.length > 0

    storeControlSnapshot(
      currentUser,
      hasControlPayload
        ? {
          empresas,
          regimenesTributarios,
          configuracionesFiscales,
          cuentasContables,
          reglasContables,
          matricesReglas,
          eventosContables,
          asientosContables,
          obligacionesMensuales,
          cierresMensuales,
          lastLoadedAt,
        }
        : null,
    )
  }, [
    currentUser,
    empresas,
    regimenesTributarios,
    configuracionesFiscales,
    cuentasContables,
    reglasContables,
    matricesReglas,
    eventosContables,
    asientosContables,
    obligacionesMensuales,
    cierresMensuales,
    lastLoadedAt,
  ])

  useEffect(() => {
    if (!canAccessView(activeView)) {
      setActiveView(defaultViewForRole(effectiveRole))
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
      storeCurrentUser(response.user)
      setToken(response.token)
      setCurrentUser(response.user)
      applyOverviewBootstrapSnapshot(response.user, response.bootstrap?.overview, {
        setDashboard,
        setManualSummary,
        setLastLoadedAt,
      })
      applyControlBootstrapSnapshot(response.user, response.bootstrap?.control, {
        setEmpresas,
        setRegimenesTributarios,
        setConfiguracionesFiscales,
        setCuentasContables,
        setReglasContables,
        setMatricesReglas,
        setEventosContables,
        setAsientosContables,
        setObligacionesMensuales,
        setCierresMensuales,
        setIsControlCoreLoaded,
        setIsControlCatalogLoaded,
        setIsControlActivityLoaded,
        setLastLoadedAt,
      })
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
    clearStoredSession()
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
    setExpedientes([])
    setPoliticasFirma([])
    setDocumentosEmitidos([])
    setGatesCanales([])
    setMensajesSalientes([])
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
    setAuditEvents([])
    setManualResolutions([])
    setCapacidadesSii([])
    setDtes([])
    setF29s([])
    setProcesosAnuales([])
    setDdjjs([])
    setF22s([])
    setCompliancePolicies([])
    setComplianceExports([])
    setComplianceExportPreview(null)
    setIsPatrimonioSnapshotLoading(false)
    setIsOperationSnapshotLoading(false)
    setIsContractsSnapshotLoading(false)
    setIsDocumentsSnapshotLoading(false)
    setIsChannelsSnapshotLoading(false)
    setIsCobranzaSnapshotLoading(false)
    setIsConciliacionSnapshotLoading(false)
    setIsSiiSnapshotLoading(false)
    setIsAuditSnapshotLoading(false)
    setIsControlCatalogLoading(false)
    setIsControlActivityLoading(false)
    setIsOperationSnapshotLoaded(false)
    setIsContractsSnapshotLoaded(false)
    setIsDocumentsSnapshotLoaded(false)
    setIsChannelsSnapshotLoaded(false)
    setIsCobranzaSnapshotLoaded(false)
    setIsConciliacionSnapshotLoaded(false)
    setIsSiiSnapshotLoaded(false)
    setIsAuditSnapshotLoaded(false)
    setIsControlCoreLoaded(false)
    setIsControlCatalogLoaded(false)
    setIsControlActivityLoaded(false)
    setIsReportingReferencesLoaded(false)
    setIsComplianceLoaded(false)
    setIsPatrimonioSnapshotLoaded(false)
    setEditingManualResolutionId(null)
  }

  async function submitMutation(
    path: string,
    method: 'POST' | 'PATCH',
    body: unknown,
    successMessage: string,
    section?: SectionKey,
  ) {
    if (section && !canMutateSection(effectiveRole, section)) {
      setFormError('Tu rol actual no tiene permisos para modificar esta sección.')
      return false
    }
    if (!token) return
    setIsSubmitting(true)
    setFormMessage(null)
    setFormError(null)
    try {
      await apiRequest(path, { method, token, body })
      await loadWorkspace(token, { forceDataRefresh: true })
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

  function startEditConfigFiscal(row: ConfiguracionFiscal) {
    setEditingConfigFiscalId(row.id)
    setConfigFiscalDraft({
      empresa: String(row.empresa),
      regimen_tributario: String(row.regimen_tributario),
      afecta_iva_arriendo: row.afecta_iva_arriendo,
      tasa_iva: row.tasa_iva,
      tasa_ppm_vigente: row.tasa_ppm_vigente || '',
      ddjj_habilitadas_text: row.ddjj_habilitadas.join(', '),
      aplica_ppm: row.aplica_ppm,
      inicio_ejercicio: row.inicio_ejercicio,
      moneda_funcional: row.moneda_funcional,
      estado: row.estado,
    })
    navigateWithContext('contabilidad', String(row.empresa), `Editando config fiscal: empresa ${row.empresa}`)
  }

  function cancelEditConfigFiscal() {
    setEditingConfigFiscalId(null)
    setConfigFiscalDraft({
      empresa: '',
      regimen_tributario: '',
      afecta_iva_arriendo: false,
      tasa_iva: '0.00',
      tasa_ppm_vigente: '',
      ddjj_habilitadas_text: '',
      aplica_ppm: true,
      inicio_ejercicio: '2026-01-01',
      moneda_funcional: 'CLP',
      estado: 'activa',
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
      await loadWorkspace(token, { forceDataRefresh: true })
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
    const isEdit = editingConfigFiscalId != null
    const currentConfig = isEdit ? configuracionesFiscales.find((item) => item.id === editingConfigFiscalId) : null
    const ddjjHabilitadas = configFiscalDraft.ddjj_habilitadas_text
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
    const ok = await submitMutation(
      isEdit ? `/api/v1/contabilidad/configuraciones-fiscales/${editingConfigFiscalId}/` : '/api/v1/contabilidad/configuraciones-fiscales/',
      isEdit ? 'PATCH' : 'POST',
      {
        empresa: Number(configFiscalDraft.empresa),
        regimen_tributario: Number(configFiscalDraft.regimen_tributario),
        afecta_iva_arriendo: configFiscalDraft.afecta_iva_arriendo,
        tasa_iva: configFiscalDraft.tasa_iva,
        tasa_ppm_vigente: configFiscalDraft.tasa_ppm_vigente || null,
        aplica_ppm: configFiscalDraft.aplica_ppm,
        ddjj_habilitadas: ddjjHabilitadas.length ? ddjjHabilitadas : (currentConfig?.ddjj_habilitadas || []),
        inicio_ejercicio: configFiscalDraft.inicio_ejercicio,
        moneda_funcional: configFiscalDraft.moneda_funcional,
        estado: configFiscalDraft.estado,
      },
      isEdit ? 'Configuración fiscal actualizada correctamente.' : 'Configuración fiscal creada correctamente.',
    )
    if (ok) {
      setConfigFiscalDraft({
        empresa: '',
        regimen_tributario: '',
        afecta_iva_arriendo: false,
        tasa_iva: '0.00',
        tasa_ppm_vigente: '',
        ddjj_habilitadas_text: '',
        aplica_ppm: true,
        inicio_ejercicio: '2026-01-01',
        moneda_funcional: 'CLP',
        estado: 'activa',
      })
      setEditingConfigFiscalId(null)
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
      await loadWorkspace(token, { forceDataRefresh: true })
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
      await loadWorkspace(token, { forceDataRefresh: true })
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
    const query = new URLSearchParams({ status: reportingMigrationDraft.status, refresh: '1' })
    await fetchReportingData<ReportingMigrationSummary>(
      `/api/v1/reporting/migracion/resoluciones-manuales/?${query.toString()}`,
      setReportingMigrationSummary,
      'Resumen de resoluciones manuales cargado correctamente.',
    )
  }

  async function handleCreatePoliticaRetencion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditCompliance) return
    const success = await submitMutation(
      '/api/v1/compliance/politicas-retencion/',
      'POST',
      {
        categoria_dato: politicaRetencionDraft.categoria_dato,
        evento_inicio: politicaRetencionDraft.evento_inicio,
        plazo_minimo_anos: Number(politicaRetencionDraft.plazo_minimo_anos),
        permite_borrado_logico: politicaRetencionDraft.permite_borrado_logico,
        permite_purga_fisica: politicaRetencionDraft.permite_purga_fisica,
        requiere_hold: politicaRetencionDraft.requiere_hold,
        estado: politicaRetencionDraft.estado,
      },
      'Política de retención creada correctamente.',
      'compliance',
    )
    if (!success) return
    setPoliticaRetencionDraft({
      categoria_dato: 'financiero',
      evento_inicio: 'ultimo_evento_relevante',
      plazo_minimo_anos: '6',
      permite_borrado_logico: true,
      permite_purga_fisica: false,
      requiere_hold: false,
      estado: 'activa',
    })
  }

  async function handlePrepareExportacion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditCompliance) return
    const body: Record<string, unknown> = {
      categoria_dato: exportacionPrepareDraft.categoria_dato,
      export_kind: exportacionPrepareDraft.export_kind,
      motivo: exportacionPrepareDraft.motivo,
      hold_activo: exportacionPrepareDraft.hold_activo,
    }
    if (exportacionPrepareDraft.empresa_id) body.empresa_id = Number(exportacionPrepareDraft.empresa_id)
    if (exportacionPrepareDraft.socio_id) body.socio_id = Number(exportacionPrepareDraft.socio_id)
    if (exportacionPrepareDraft.anio) body.anio = Number(exportacionPrepareDraft.anio)
    if (exportacionPrepareDraft.mes) body.mes = Number(exportacionPrepareDraft.mes)
    if (exportacionPrepareDraft.anio_tributario) body.anio_tributario = Number(exportacionPrepareDraft.anio_tributario)
    if (exportacionPrepareDraft.periodo) body.periodo = exportacionPrepareDraft.periodo
    const success = await submitMutation(
      '/api/v1/compliance/exportes/preparar/',
      'POST',
      body,
      'Exportación sensible preparada correctamente.',
      'compliance',
    )
    if (!success) return
    setExportacionPrepareDraft((current) => ({
      ...current,
      motivo: '',
      hold_activo: false,
    }))
  }

  async function handleViewExportacionContenido(exportId: number) {
    if (!token) return
    setIsSubmitting(true)
    setFormMessage(null)
    setFormError(null)
    try {
      const payload = await apiRequest<ExportacionSensiblePreview>(`/api/v1/compliance/exportes/${exportId}/contenido/`, { token })
      setComplianceExportPreview(payload)
      setFormMessage('Contenido de exportación cargado correctamente.')
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'No se pudo cargar el contenido de la exportación.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleRevokeExportacion(exportId: number) {
    if (!canEditCompliance) return
    const success = await submitMutation(
      `/api/v1/compliance/exportes/${exportId}/revocar/`,
      'POST',
      {},
      'Exportación sensible revocada correctamente.',
      'compliance',
    )
    if (success && complianceExportPreview?.id === exportId) {
      setComplianceExportPreview(null)
    }
  }

  async function handleCreateExpediente(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditDocumentos) return
    const isEdit = editingExpedienteId != null
    const success = await submitMutation(
      isEdit ? `/api/v1/documentos/expedientes/${editingExpedienteId}/` : '/api/v1/documentos/expedientes/',
      isEdit ? 'PATCH' : 'POST',
      expedienteDraft,
      isEdit ? 'Expediente actualizado correctamente.' : 'Expediente creado correctamente.',
      'documentos',
    )
    if (!success) return
    setEditingExpedienteId(null)
    setExpedienteDraft({ entidad_tipo: 'contrato', entidad_id: '', estado: 'abierto', owner_operativo: '' })
  }

  async function handleCreatePoliticaFirma(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditDocumentos) return
    const success = await submitMutation(
      '/api/v1/documentos/politicas-firma/',
      'POST',
      politicaFirmaDraft,
      'Política documental creada correctamente.',
      'documentos',
    )
    if (!success) return
  }

  async function handleCreateDocumento(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditDocumentos) return
    const success = await submitMutation(
      '/api/v1/documentos/documentos-emitidos/',
      'POST',
      {
        ...documentoDraft,
        fecha_carga: documentoDraft.fecha_carga ? new Date(documentoDraft.fecha_carga).toISOString() : undefined,
        comprobante_notarial: documentoDraft.comprobante_notarial || null,
      },
      'Documento emitido creado correctamente.',
      'documentos',
    )
    if (!success) return
  }

  async function handleFormalizeDocumento(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditDocumentos || !documentoFormalizarDraft.documentoId) return
    const success = await submitMutation(
      `/api/v1/documentos/documentos-emitidos/${documentoFormalizarDraft.documentoId}/formalizar/`,
      'POST',
      {
        firma_arrendador_registrada: documentoFormalizarDraft.firma_arrendador_registrada,
        firma_arrendatario_registrada: documentoFormalizarDraft.firma_arrendatario_registrada,
        firma_codeudor_registrada: documentoFormalizarDraft.firma_codeudor_registrada,
        recepcion_notarial_registrada: documentoFormalizarDraft.recepcion_notarial_registrada,
        comprobante_notarial: documentoFormalizarDraft.comprobante_notarial || null,
      },
      'Documento formalizado correctamente.',
      'documentos',
    )
    if (!success) return
  }

  async function handleCreateGateCanal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditCanales) return
    const success = await submitMutation(
      '/api/v1/canales/gates/',
      'POST',
      { ...gateCanalDraft, restricciones_operativas: {} },
      'Gate de canal creado correctamente.',
      'canales',
    )
    if (!success) return
  }

  async function handlePrepareMensaje(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditCanales) return
    const success = await submitMutation(
      '/api/v1/canales/mensajes/preparar/',
      'POST',
      {
        canal: mensajeDraft.canal,
        canal_mensajeria: mensajeDraft.canal_mensajeria,
        identidad_envio: mensajeDraft.identidad_envio || null,
        contrato: mensajeDraft.contrato || null,
        arrendatario: mensajeDraft.arrendatario || null,
        documento_emitido: mensajeDraft.documento_emitido || null,
        asunto: mensajeDraft.asunto,
        cuerpo: mensajeDraft.cuerpo,
      },
      'Mensaje preparado correctamente.',
      'canales',
    )
    if (!success) return
  }

  async function handleRegistrarEnvioMensaje(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditCanales || !mensajeEnvioDraft.mensajeId) return
    const success = await submitMutation(
      `/api/v1/canales/mensajes/${mensajeEnvioDraft.mensajeId}/registrar-envio/`,
      'POST',
      { external_ref: mensajeEnvioDraft.external_ref },
      'Envío manual registrado correctamente.',
      'canales',
    )
    if (!success) return
  }

  async function handleUpdateManualResolution(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditAudit || !editingManualResolutionId) return
    const success = await submitMutation(
      `/api/v1/audit/manual-resolutions/${editingManualResolutionId}/`,
      'PATCH',
      manualResolutionDraft,
      'Resolución manual actualizada correctamente.',
      'audit',
    )
    if (!success) return
    setEditingManualResolutionId(null)
    setManualResolutionDraft({ status: 'open', rationale: '' })
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

  function startEditManualResolution(row: ManualResolutionItem) {
    setEditingManualResolutionId(row.id)
    setManualResolutionDraft({
      status: row.status,
      rationale: row.rationale || '',
    })
  }

  function cancelEditManualResolution() {
    setEditingManualResolutionId(null)
    setManualResolutionDraft({ status: 'open', rationale: '' })
  }

  function startEditExpediente(row: ExpedienteDocumental) {
    setEditingExpedienteId(row.id)
    setExpedienteDraft({
      entidad_tipo: row.entidad_tipo,
      entidad_id: row.entidad_id,
      estado: row.estado,
      owner_operativo: row.owner_operativo,
    })
  }

  function cancelEditExpediente() {
    setEditingExpedienteId(null)
    setExpedienteDraft({ entidad_tipo: 'contrato', entidad_id: '', estado: 'abierto', owner_operativo: '' })
  }

  function goToDocumentoContext(documentoId: number) {
    const document = documentosEmitidos.find((item) => item.id === documentoId)
    navigateWithContext(
      'canales',
      document?.storage_ref || '',
      document ? `Documento: ${document.storage_ref}` : `Documento: ${documentoId}`,
    )
    setMensajeDraft((current) => ({ ...current, documento_emitido: String(documentoId) }))
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
  const filteredExpedientes = useMemo(
    () =>
      expedientes.filter((item) =>
        matches(normalizedSearch, [item.entidad_tipo, item.entidad_id, item.estado, item.owner_operativo]),
      ),
    [expedientes, normalizedSearch],
  )
  const filteredPoliticasFirma = useMemo(
    () =>
      politicasFirma.filter((item) =>
        matches(normalizedSearch, [item.tipo_documental, item.modo_firma_permitido, item.estado]),
      ),
    [politicasFirma, normalizedSearch],
  )
  const filteredDocumentosEmitidos = useMemo(
    () =>
      documentosEmitidos.filter((item) =>
        matches(normalizedSearch, [item.tipo_documental, item.version_plantilla, item.estado, item.origen, item.storage_ref]),
      ),
    [documentosEmitidos, normalizedSearch],
  )
  const filteredGatesCanales = useMemo(
    () =>
      gatesCanales.filter((item) =>
        matches(normalizedSearch, [item.canal, item.provider_key, item.estado_gate, item.evidencia_ref]),
      ),
    [gatesCanales, normalizedSearch],
  )
  const filteredMensajesSalientes = useMemo(
    () =>
      mensajesSalientes.filter((item) =>
        matches(normalizedSearch, [item.canal, item.destinatario, item.asunto, item.estado, item.external_ref, item.cuerpo]),
      ),
    [mensajesSalientes, normalizedSearch],
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
  const filteredAuditEvents = useMemo(
    () =>
      auditEvents.filter((item) =>
        matches(normalizedSearch, [
          item.event_type,
          item.severity,
          item.entity_type,
          item.entity_id,
          item.summary,
          item.actor_user_display,
        ]),
      ),
    [auditEvents, normalizedSearch],
  )
  const filteredManualResolutions = useMemo(
    () =>
      manualResolutions.filter((item) =>
        matches(normalizedSearch, [
          item.category,
          item.status,
          item.scope_type,
          item.scope_reference,
          item.summary,
          item.requested_by_display,
          item.resolved_by_display,
        ]),
      ),
    [manualResolutions, normalizedSearch],
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
  const filteredCompliancePolicies = useMemo(
    () =>
      compliancePolicies.filter((item) =>
        matches(normalizedSearch, [
          item.categoria_dato,
          item.evento_inicio,
          item.plazo_minimo_anos,
          item.estado,
        ]),
      ),
    [compliancePolicies, normalizedSearch],
  )
  const filteredComplianceExports = useMemo(
    () =>
      complianceExports.filter((item) =>
        matches(normalizedSearch, [
          item.categoria_dato,
          item.export_kind,
          item.payload_hash,
          item.encrypted_ref,
          item.estado,
          item.motivo,
        ]),
      ),
    [complianceExports, normalizedSearch],
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
  const activeManualResolution = useMemo(
    () => manualResolutions.find((item) => item.id === editingManualResolutionId) || null,
    [manualResolutions, editingManualResolutionId],
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
              <p>{apiConfigError ? 'El frontend ya está arriba, pero todavía no tiene un backend configurado para este entorno.' : 'Usa las credenciales del backend canónico.'}</p>
            </div>
          </div>
          <form className="login-form" onSubmit={handleLogin}>
            <label>
              <span>Usuario</span>
              <input value={username} onChange={(event) => setUsername(event.target.value)} disabled={Boolean(apiConfigError)} />
            </label>
            <label>
              <span>Contraseña</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={Boolean(apiConfigError)}
              />
            </label>
            <button type="submit" className="button-primary" disabled={isLoggingIn || Boolean(apiConfigError)}>
              {isLoggingIn ? 'Ingresando...' : 'Ingresar'}
            </button>
          </form>
          {apiConfigError ? <p className="form-message error-text">{apiConfigError}</p> : null}
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
      <WorkspaceHeader
        userLabel={currentUser ? `${currentUser.display_name || currentUser.username} · ${currentUser.default_role_code}` : 'Cargando sesión...'}
        effectiveRole={effectiveRole}
        assignments={activeAssignments}
        lastLoadedAt={lastLoadedAt}
        isRefreshing={isRefreshing}
        onRefresh={() => { if (token) void loadWorkspace(token, { forceUserRefresh: true, forceDataRefresh: true }) }}
        onLogout={() => void handleLogout()}
      />

      <WorkspaceTabs
        tabs={visibleTabs}
        activeView={activeView}
        onSelect={(view) => {
          setActiveView(view as ViewKey)
          setActiveContextLabel(null)
        }}
      />

      {apiConfigError ? <div className="banner-error">{apiConfigError}</div> : null}
      {workspaceError ? <div className="banner-error">{workspaceError}</div> : null}
      {activeView !== 'overview' && activeContextLabel ? <ContextBanner label={activeContextLabel} onClear={() => setActiveContextLabel(null)} /> : null}

      {activeView === 'overview' ? (
        <OverviewWorkspace
          dashboard={dashboard}
          manualSummary={manualSummary}
          health={health}
          counts={{
            socios: socios.length,
            empresas: empresas.length,
            comunidades: comunidades.length,
            propiedades: propiedades.length,
            cuentas: cuentas.length,
            identidades: identidades.length,
            mandatos: mandatos.length,
          }}
          toneFor={toneFor}
        />
      ) : null}

      {activeView !== 'overview' ? <SectionToolbar tag={currentSectionTag} title={currentSectionTitle} placeholder={currentSearchPlaceholder} searchText={searchText} onSearchChange={setSearchText} /> : null}

      {activeView !== 'overview' && formMessage ? <div className="banner-success">{formMessage}</div> : null}
      {activeView !== 'overview' && formError ? <div className="banner-error">{formError}</div> : null}

      {activeView === 'patrimonio' ? (
        <PatrimonioWorkspace
          canEditPatrimonio={canEditPatrimonio}
          editingSocioId={editingSocioId}
          socioDraft={socioDraft}
          setSocioDraft={setSocioDraft}
          handleCreateSocio={handleCreateSocio}
          cancelEditSocio={cancelEditSocio}
          editingPropiedadId={editingPropiedadId}
          propiedadDraft={propiedadDraft}
          setPropiedadDraft={setPropiedadDraft}
          handleCreatePropiedad={handleCreatePropiedad}
          cancelEditPropiedad={cancelEditPropiedad}
          patrimonioOwners={patrimonioOwners}
          filteredSocios={filteredSocios}
          filteredEmpresas={filteredEmpresas}
          filteredComunidades={filteredComunidades}
          filteredPropiedades={filteredPropiedades}
          toneFor={toneFor}
          isSubmitting={isSubmitting}
          isLoading={isPatrimonioSnapshotLoading}
          startEditSocio={startEditSocio}
          startEditPropiedad={startEditPropiedad}
          goToEmpresaContext={goToEmpresaContext}
          goToEmpresaSiiContext={(empresaId, razonSocial) => {
            navigateWithContext('sii', razonSocial)
            setCapacidadSiiDraft((current) => ({ ...current, empresa: String(empresaId) }))
          }}
          goToPropertyOperationContext={(propiedadId, codigoPropiedad) => {
            navigateWithContext('operacion', codigoPropiedad, `Propiedad: ${codigoPropiedad}`)
            setMandatoDraft((current) => ({ ...current, propiedad_id: String(propiedadId) }))
          }}
          canOpenContabilidad={canAccessView('contabilidad')}
          canOpenSii={canAccessView('sii')}
        />
      ) : null}

      {activeView === 'operacion' ? (
        <OperacionWorkspace
          canEditOperacion={canEditOperacion}
          editingCuentaId={editingCuentaId}
          cuentaDraft={cuentaDraft}
          setCuentaDraft={setCuentaDraft}
          handleCreateCuenta={handleCreateCuenta}
          cancelEditCuenta={cancelEditCuenta}
          editingMandatoId={editingMandatoId}
          mandatoDraft={mandatoDraft}
          setMandatoDraft={setMandatoDraft}
          handleCreateMandato={handleCreateMandato}
          cancelEditMandato={cancelEditMandato}
          simpleOwners={simpleOwners}
          patrimonioOwners={patrimonioOwners}
          propiedades={propiedades}
          cuentas={cuentas}
          filteredCuentas={filteredCuentas}
          filteredIdentidades={filteredIdentidades}
          filteredMandatos={filteredMandatos}
          toneFor={toneFor}
          isSubmitting={isSubmitting}
          isLoading={isOperationSnapshotLoading}
          startEditCuenta={startEditCuenta}
          startEditMandato={startEditMandato}
          goToCuentaConciliacion={(cuentaId, numeroCuenta) => {
            navigateWithContext('conciliacion', numeroCuenta, `Cuenta: ${numeroCuenta}`)
            setConexionDraft((current) => ({ ...current, cuenta_recaudadora: String(cuentaId) }))
          }}
          goToMandatoContext={goToMandatoContext}
        />
      ) : null}

      {activeView === 'contratos' ? (
        <ContratosWorkspace
          canEditContratos={canEditContratos}
          editingArrendatarioId={editingArrendatarioId}
          arrendatarioDraft={arrendatarioDraft}
          setArrendatarioDraft={setArrendatarioDraft}
          handleCreateArrendatario={handleCreateArrendatario}
          cancelEditArrendatario={cancelEditArrendatario}
          editingContratoId={editingContratoId}
          contratoDraft={contratoDraft}
          setContratoDraft={setContratoDraft}
          handleCreateContrato={handleCreateContrato}
          cancelEditContrato={cancelEditContrato}
          avisoDraft={avisoDraft}
          setAvisoDraft={setAvisoDraft}
          handleCreateAviso={handleCreateAviso}
          mandatos={mandatos}
          arrendatarios={arrendatarios}
          contratos={contratos}
          filteredArrendatarios={filteredArrendatarios}
          filteredContratos={filteredContratos}
          filteredAvisos={filteredAvisos}
          arrendatarioById={arrendatarioById}
          mandatoById={mandatoById}
          contratoById={contratoById}
          toneFor={toneFor}
          isSubmitting={isSubmitting}
          isLoading={isContractsSnapshotLoading}
          startEditArrendatario={startEditArrendatario}
          startEditContrato={startEditContrato}
          goToArrendatarioContext={goToArrendatarioContext}
          goToContratoContext={goToContratoContext}
          prepareExpedienteForContract={(row) => {
            navigateWithContext('documentos', row.codigo_contrato, `Contrato: ${row.codigo_contrato}`)
            setExpedienteDraft((current) => ({
              ...current,
              entidad_tipo: 'contrato',
              entidad_id: String(row.id),
              owner_operativo: `mandato:${row.mandato_operacion}`,
            }))
          }}
        />
      ) : null}

      {activeView === 'documentos' ? (
        <DocumentosWorkspace
          canEditDocumentos={canEditDocumentos}
          editingExpedienteId={editingExpedienteId}
          expedienteDraft={expedienteDraft}
          setExpedienteDraft={setExpedienteDraft}
          handleCreateExpediente={handleCreateExpediente}
          cancelEditExpediente={cancelEditExpediente}
          politicaFirmaDraft={politicaFirmaDraft}
          setPoliticaFirmaDraft={setPoliticaFirmaDraft}
          handleCreatePoliticaFirma={handleCreatePoliticaFirma}
          documentoDraft={documentoDraft}
          setDocumentoDraft={setDocumentoDraft}
          handleCreateDocumento={handleCreateDocumento}
          documentoFormalizarDraft={documentoFormalizarDraft}
          setDocumentoFormalizarDraft={setDocumentoFormalizarDraft}
          handleFormalizeDocumento={handleFormalizeDocumento}
          expedientes={expedientes}
          documentosEmitidos={documentosEmitidos}
          filteredExpedientes={filteredExpedientes}
          filteredPoliticasFirma={filteredPoliticasFirma}
          filteredDocumentosEmitidos={filteredDocumentosEmitidos}
          isSubmitting={isSubmitting}
          isLoading={isDocumentsSnapshotLoading}
          startEditExpediente={startEditExpediente}
          goToDocumentoContext={goToDocumentoContext}
        />
      ) : null}

      {activeView === 'canales' ? (
        <CanalesWorkspace
          canEditCanales={canEditCanales}
          gateCanalDraft={gateCanalDraft}
          setGateCanalDraft={setGateCanalDraft}
          handleCreateGateCanal={handleCreateGateCanal}
          mensajeDraft={mensajeDraft}
          setMensajeDraft={setMensajeDraft}
          handlePrepareMensaje={handlePrepareMensaje}
          mensajeEnvioDraft={mensajeEnvioDraft}
          setMensajeEnvioDraft={setMensajeEnvioDraft}
          handleRegistrarEnvioMensaje={handleRegistrarEnvioMensaje}
          gatesCanales={gatesCanales}
          identidades={identidades}
          contratos={contratos}
          arrendatarios={arrendatarios}
          documentosEmitidos={documentosEmitidos}
          mensajesSalientes={mensajesSalientes}
          filteredGatesCanales={filteredGatesCanales}
          filteredMensajesSalientes={filteredMensajesSalientes}
          isSubmitting={isSubmitting}
          isLoading={isChannelsSnapshotLoading}
          contratoById={contratoById}
          toneFor={toneFor}
        />
      ) : null}

      {activeView === 'cobranza' ? (
        <CobranzaWorkspace
          canEditCobranza={canEditCobranza}
          ufDraft={ufDraft}
          setUfDraft={setUfDraft}
          handleCreateUf={handleCreateUf}
          ajusteDraft={ajusteDraft}
          setAjusteDraft={setAjusteDraft}
          handleCreateAjuste={handleCreateAjuste}
          pagoDraft={pagoDraft}
          setPagoDraft={setPagoDraft}
          handleGeneratePago={handleGeneratePago}
          garantiaDraft={garantiaDraft}
          setGarantiaDraft={setGarantiaDraft}
          handleCreateGarantia={handleCreateGarantia}
          garantiaMovimientoDraft={garantiaMovimientoDraft}
          setGarantiaMovimientoDraft={setGarantiaMovimientoDraft}
          handleGarantiaMovimiento={handleGarantiaMovimiento}
          estadoCuentaDraft={estadoCuentaDraft}
          setEstadoCuentaDraft={setEstadoCuentaDraft}
          handleRebuildEstadoCuenta={handleRebuildEstadoCuenta}
          contratos={contratos}
          garantias={garantias}
          arrendatarios={arrendatarios}
          filteredValoresUf={filteredValoresUf}
          filteredAjustes={filteredAjustes}
          filteredPagos={filteredPagos}
          filteredGarantias={filteredGarantias}
          filteredHistorialGarantias={filteredHistorialGarantias}
          filteredEstadosCuenta={filteredEstadosCuenta}
          contratoById={contratoById}
          arrendatarioById={arrendatarioById}
          toneFor={toneFor}
          isSubmitting={isSubmitting}
          isLoading={isCobranzaSnapshotLoading}
          navigateToConciliacion={(row) => { navigateWithContext('conciliacion', `${row.mes}/${row.anio}`) }}
          goToPagoContext={goToPagoContext}
          canOpenSii={canAccessView('sii')}
        />
      ) : null}

      {activeView === 'conciliacion' ? (
        <ConciliacionWorkspace
          canEditConciliacion={canEditConciliacion}
          conexionDraft={conexionDraft}
          setConexionDraft={setConexionDraft}
          handleCreateConexion={handleCreateConexion}
          movimientoDraft={movimientoDraft}
          setMovimientoDraft={setMovimientoDraft}
          handleCreateMovimiento={handleCreateMovimiento}
          filteredConexiones={filteredConexiones}
          filteredMovimientos={filteredMovimientos}
          filteredIngresos={filteredIngresos}
          cuentas={cuentas}
          conexionesBancarias={conexionesBancarias}
          cuentaById={cuentaById}
          toneFor={toneFor}
          isSubmitting={isSubmitting}
          isLoading={isConciliacionSnapshotLoading}
          handleRetryMatch={handleRetryMatch}
        />
      ) : null}

      {activeView === 'audit' ? (
        <AuditWorkspace
          effectiveRole={effectiveRole}
          canEditAudit={canEditAudit}
          auditHeading={auditHeading}
          activeManualResolution={activeManualResolution}
          editingManualResolutionId={editingManualResolutionId}
          manualResolutionDraft={manualResolutionDraft}
          setManualResolutionDraft={setManualResolutionDraft}
          handleUpdateManualResolution={handleUpdateManualResolution}
          cancelEditManualResolution={cancelEditManualResolution}
          filteredAuditEvents={filteredAuditEvents}
          filteredManualResolutions={filteredManualResolutions}
          startEditManualResolution={startEditManualResolution}
          isSubmitting={isSubmitting}
          isLoading={isAuditSnapshotLoading}
        />
      ) : null}

      {activeView === 'contabilidad' ? (
        <ContabilidadWorkspace
          canEditContabilidad={canEditContabilidad}
          editingConfigFiscalId={editingConfigFiscalId}
          configFiscalDraft={configFiscalDraft}
          setConfigFiscalDraft={setConfigFiscalDraft}
          handleCreateConfigFiscal={handleCreateConfigFiscal}
          cancelEditConfigFiscal={cancelEditConfigFiscal}
          cuentaContableDraft={cuentaContableDraft}
          setCuentaContableDraft={setCuentaContableDraft}
          handleCreateCuentaContable={handleCreateCuentaContable}
          reglaContableDraft={reglaContableDraft}
          setReglaContableDraft={setReglaContableDraft}
          handleCreateReglaContable={handleCreateReglaContable}
          matrizDraft={matrizDraft}
          setMatrizDraft={setMatrizDraft}
          handleCreateMatriz={handleCreateMatriz}
          eventoContableDraft={eventoContableDraft}
          setEventoContableDraft={setEventoContableDraft}
          handleCreateEventoContable={handleCreateEventoContable}
          cierreDraft={cierreDraft}
          setCierreDraft={setCierreDraft}
          handlePrepareCierre={handlePrepareCierre}
          filteredRegimenes={filteredRegimenes}
          filteredConfigsFiscales={filteredConfigsFiscales}
          filteredCuentasContables={filteredCuentasContables}
          filteredReglasContables={filteredReglasContables}
          filteredMatrices={filteredMatrices}
          filteredEventosContables={filteredEventosContables}
          filteredAsientosContables={filteredAsientosContables}
          filteredObligaciones={filteredObligaciones}
          filteredCierres={filteredCierres}
          empresas={empresas}
          regimenesTributarios={regimenesTributarios}
          cuentasContables={cuentasContables}
          reglasContables={reglasContables}
          empresaById={empresaById}
          regimenById={regimenById}
          reglaById={reglaById}
          cuentaContableById={cuentaContableById}
          toneFor={toneFor}
          isSubmitting={isSubmitting}
          handleAccountingAction={handleAccountingAction}
          startEditConfigFiscal={startEditConfigFiscal}
          onViewImpact={(companyId) => {
            const companyName = empresaById.get(companyId)?.razon_social || String(companyId)
            navigateWithContext('reporting', companyName, `Empresa: ${companyName}`)
            setReportingFinancialDraft((current) => ({ ...current, empresa_id: String(companyId) }))
          }}
          isCatalogLoading={isControlCatalogLoading}
          isActivityLoading={isControlActivityLoading}
        />
      ) : null}

      {activeView === 'sii' ? (
        <SiiWorkspace
          canEditSii={canEditSii}
          capacidadSiiDraft={capacidadSiiDraft}
          setCapacidadSiiDraft={setCapacidadSiiDraft}
          handleCreateCapacidadSii={handleCreateCapacidadSii}
          dteDraft={dteDraft}
          setDteDraft={setDteDraft}
          handleGenerateDte={handleGenerateDte}
          f29Draft={f29Draft}
          setF29Draft={setF29Draft}
          handleGenerateF29={handleGenerateF29}
          annualDraft={annualDraft}
          setAnnualDraft={setAnnualDraft}
          handleGenerateAnnual={handleGenerateAnnual}
          empresas={empresas}
          pagos={pagos}
          contratoById={contratoById}
          filteredCapacidadesSii={filteredCapacidadesSii}
          filteredDtes={filteredDtes}
          filteredF29s={filteredF29s}
          filteredProcesosAnuales={filteredProcesosAnuales}
          filteredDdjjs={filteredDdjjs}
          filteredF22s={filteredF22s}
          empresaById={empresaById}
          capacidadSiiById={capacidadSiiById}
          toneFor={toneFor}
          isSubmitting={isSubmitting}
          isLoading={isSiiSnapshotLoading}
          handleSiiStatusUpdate={handleSiiStatusUpdate}
          onViewReporting={(companyId) => {
            const companyName = empresaById.get(companyId)?.razon_social || String(companyId)
            navigateWithContext('reporting', companyName, `Empresa: ${companyName}`)
            setReportingFinancialDraft((current) => ({ ...current, empresa_id: String(companyId) }))
          }}
        />
      ) : null}

      {activeView === 'compliance' ? (
        <ComplianceWorkspace
          canEditCompliance={canEditCompliance}
          politicaRetencionDraft={politicaRetencionDraft}
          setPoliticaRetencionDraft={setPoliticaRetencionDraft}
          handleCreatePoliticaRetencion={handleCreatePoliticaRetencion}
          exportacionPrepareDraft={exportacionPrepareDraft}
          setExportacionPrepareDraft={setExportacionPrepareDraft}
          handlePrepareExportacion={handlePrepareExportacion}
          filteredCompliancePolicies={filteredCompliancePolicies}
          filteredComplianceExports={filteredComplianceExports}
          complianceExportPreview={complianceExportPreview}
          handleViewExportacionContenido={handleViewExportacionContenido}
          handleRevokeExportacion={handleRevokeExportacion}
          empresas={empresas}
          socios={socios}
          isSubmitting={isSubmitting}
        />
      ) : null}

      {activeView === 'reporting' ? (
        <ReportingWorkspace
          effectiveRole={effectiveRole}
          currentUser={currentUser}
          reportingFinancialDraft={reportingFinancialDraft}
          setReportingFinancialDraft={setReportingFinancialDraft}
          handleFetchFinancialSummary={handleFetchFinancialSummary}
          reportingPartnerDraft={reportingPartnerDraft}
          setReportingPartnerDraft={setReportingPartnerDraft}
          handleFetchPartnerSummary={handleFetchPartnerSummary}
          reportingBooksDraft={reportingBooksDraft}
          setReportingBooksDraft={setReportingBooksDraft}
          handleFetchBooksSummary={handleFetchBooksSummary}
          reportingAnnualDraft={reportingAnnualDraft}
          setReportingAnnualDraft={setReportingAnnualDraft}
          handleFetchAnnualSummary={handleFetchAnnualSummary}
          reportingMigrationDraft={reportingMigrationDraft}
          setReportingMigrationDraft={setReportingMigrationDraft}
          handleFetchMigrationSummary={handleFetchMigrationSummary}
          reportingFinancialSummary={reportingFinancialSummary}
          reportingPartnerSummary={reportingPartnerSummary}
          reportingBooksSummary={reportingBooksSummary}
          reportingAnnualSummary={reportingAnnualSummary}
          reportingMigrationSummary={reportingMigrationSummary}
          empresas={empresas}
          socios={socios}
          empresaById={empresaById}
          isSubmitting={isSubmitting}
          toneFor={toneFor}
          count={count}
        />
      ) : null}
    </main>
  )
}

export default App
