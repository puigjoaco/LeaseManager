export type Tone = 'neutral' | 'positive' | 'warning' | 'danger'

export function toneFor(value: string): Tone {
  const normalized = String(value || '').trim().toLowerCase()
  if (['ok', 'up', 'activa', 'activo', 'abierto', 'prepared', 'preparado', 'pagado', 'contabilizado', 'emitido', 'formalizado', 'sent', 'enviado', 'resolved', 'aceptado', 'approved', 'aprobado'].includes(normalized)) {
    return 'positive'
  }
  if (['warning', 'pendiente', 'pendiente_revision', 'pendiente_revision_contable', 'pendiente_datos', 'condicionado', 'borrador', 'draft', 'in_review', 'futuro'].includes(normalized)) {
    return 'warning'
  }
  if (['danger', 'down', 'blocked', 'bloqueado', 'cerrado', 'suspendido', 'atrasado', 'fallido', 'cancelado', 'rejected', 'forbidden', 'inactivo', 'archivado', 'unreachable'].includes(normalized)) {
    return 'danger'
  }
  return 'neutral'
}

export function count(value: number | undefined) {
  return new Intl.NumberFormat('es-CL').format(value ?? 0)
}

export function stamp(value: string | null) {
  if (!value) return 'Sin refresco reciente'
  return new Intl.DateTimeFormat('es-CL', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}
