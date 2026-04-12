export type ViewKey =
  | 'overview'
  | 'patrimonio'
  | 'operacion'
  | 'contratos'
  | 'documentos'
  | 'canales'
  | 'cobranza'
  | 'conciliacion'
  | 'audit'
  | 'contabilidad'
  | 'sii'
  | 'reporting'

export type SectionKey =
  | 'patrimonio'
  | 'operacion'
  | 'contratos'
  | 'documentos'
  | 'canales'
  | 'cobranza'
  | 'conciliacion'
  | 'audit'
  | 'contabilidad'
  | 'sii'
  | 'reporting'

export function canonicalRole(roleCode: string | null | undefined) {
  const normalized = String(roleCode || '').trim().toLowerCase()
  if (normalized === 'administradorglobal') return 'AdministradorGlobal'
  if (normalized === 'operadordecartera' || normalized === 'operator') return 'OperadorDeCartera'
  if (normalized === 'socio') return 'Socio'
  if (normalized === 'revisorfiscalexterno') return 'RevisorFiscalExterno'
  return roleCode || 'SinRol'
}

export function defaultViewForRole(roleCode: string | null | undefined): ViewKey {
  const role = canonicalRole(roleCode)
  if (role === 'RevisorFiscalExterno') return 'contabilidad'
  if (role === 'Socio') return 'reporting'
  return 'overview'
}

export function allowedViewsForRole(roleCode: string | null | undefined): ViewKey[] {
  const role = canonicalRole(roleCode)
  if (role === 'AdministradorGlobal') {
    return ['overview', 'patrimonio', 'operacion', 'contratos', 'documentos', 'canales', 'cobranza', 'conciliacion', 'audit', 'contabilidad', 'sii', 'reporting']
  }
  if (role === 'OperadorDeCartera') {
    return ['overview', 'patrimonio', 'operacion', 'contratos', 'documentos', 'canales', 'cobranza', 'conciliacion', 'audit']
  }
  if (role === 'RevisorFiscalExterno') {
    return ['audit', 'contabilidad', 'sii', 'reporting']
  }
  if (role === 'Socio') {
    return ['reporting']
  }
  return ['overview']
}

export const VIEW_LABELS: Record<ViewKey, string> = {
  overview: 'Resumen',
  patrimonio: 'Patrimonio',
  operacion: 'Operación',
  contratos: 'Contratos',
  documentos: 'Documentos',
  canales: 'Canales',
  cobranza: 'Cobranza',
  conciliacion: 'Conciliación',
  audit: 'Audit',
  contabilidad: 'Contabilidad',
  sii: 'SII',
  reporting: 'Reporting',
}

export function sectionTitleForView(view: ViewKey, auditTitle: string, reportingTitle: string) {
  if (view === 'patrimonio') return 'Owners, comunidades y propiedades'
  if (view === 'operacion') return 'Cuentas, identidades y mandatos'
  if (view === 'contratos') return 'Arrendatarios, contratos y avisos'
  if (view === 'documentos') return 'Expedientes, políticas y documentos emitidos'
  if (view === 'canales') return 'Gates operativos y mensajes salientes'
  if (view === 'cobranza') return 'Pagos, UF, ajustes, garantías y estado de cuenta'
  if (view === 'conciliacion') return 'Conexiones, movimientos e ingresos desconocidos'
  if (view === 'audit') return auditTitle
  if (view === 'contabilidad') return 'Configuración fiscal, eventos, asientos y cierres'
  if (view === 'sii') return 'Capacidades, DTE, F29 y preparación anual'
  return reportingTitle
}

export function searchPlaceholderForView(view: ViewKey, reportingPlaceholder: string) {
  if (view === 'patrimonio') return 'Nombre, RUT, dirección u owner'
  if (view === 'operacion') return 'Cuenta, owner, canal o mandato'
  if (view === 'contratos') return 'Código, arrendatario, propiedad o causal'
  if (view === 'documentos') return 'Expediente, tipo documental, estado o storage'
  if (view === 'canales') return 'Canal, estado, destinatario o external ref'
  if (view === 'cobranza') return 'Contrato, monto, estado, UF o garantía'
  if (view === 'conciliacion') return 'Movimiento, referencia, estado o ingreso desconocido'
  if (view === 'audit') return 'Evento, severidad, categoría o scope'
  if (view === 'contabilidad') return 'Empresa, evento, cuenta, cierre u obligación'
  if (view === 'sii') return 'Empresa, DTE, F29, DDJJ o F22'
  return reportingPlaceholder
}

export function reportingHeadingForRole(roleCode: string | null | undefined) {
  const role = canonicalRole(roleCode)
  if (role === 'Socio') {
    return { title: 'Mi posición patrimonial', placeholder: 'Comunidad, porcentaje o propiedad' }
  }
  if (role === 'RevisorFiscalExterno') {
    return { title: 'Lectura de control y reporting', placeholder: 'Empresa, período o estado' }
  }
  return { title: 'Dashboard, socios, libros y resumen anual', placeholder: 'Empresa, socio, libro o resolución' }
}

export function auditHeadingForRole(roleCode: string | null | undefined) {
  const role = canonicalRole(roleCode)
  if (role === 'RevisorFiscalExterno') {
    return { title: 'Eventos auditables', subtitle: 'Trazabilidad reciente en solo lectura.' }
  }
  if (role === 'OperadorDeCartera') {
    return { title: 'Resoluciones manuales', subtitle: 'Cola asistida y seguimiento operativo.' }
  }
  return { title: 'Eventos y resoluciones', subtitle: 'Trazabilidad transversal del sistema.' }
}

export function canMutateSection(roleCode: string | null | undefined, section: SectionKey) {
  const role = canonicalRole(roleCode)
  if (role === 'AdministradorGlobal') return true
  if (role === 'OperadorDeCartera') {
    return ['patrimonio', 'operacion', 'contratos', 'documentos', 'canales', 'cobranza', 'conciliacion', 'audit'].includes(section)
  }
  return false
}
