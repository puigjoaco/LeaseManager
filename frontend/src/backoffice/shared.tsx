import type { ReactNode } from 'react'

export type Tone = 'neutral' | 'positive' | 'warning' | 'danger'
export type Column<T> = { label: string; render: (row: T) => ReactNode }

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

export function Badge({ label, tone = 'neutral' }: { label: string; tone?: Tone }) {
  return <span className={`status-badge tone-${tone}`}>{label}</span>
}

export function Metric({ label, value, tone = 'neutral' }: { label: string; value: string; tone?: Tone }) {
  return (
    <article className={`metric-tile metric-${tone}`}>
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value}</strong>
    </article>
  )
}

export function TableBlock<T extends { id: number | string }>({
  title,
  subtitle,
  rows,
  columns,
  empty,
  isLoading = false,
  loadingLabel = 'Cargando...',
}: {
  title: string
  subtitle: string
  rows: T[]
  columns: Column<T>[]
  empty: string
  isLoading?: boolean
  loadingLabel?: string
}) {
  return (
    <section className="data-block">
      <div className="section-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        {!isLoading ? <Badge label={`${count(rows.length)} registros`} /> : null}
      </div>
      {isLoading ? (
        <div className="empty-state">{loadingLabel}</div>
      ) : rows.length === 0 ? (
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
