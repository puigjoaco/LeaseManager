import type { ReactNode } from 'react'

import { count, type Tone } from './shared-utils'

export type Column<T> = { label: string; render: (row: T) => ReactNode }

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
  preserveRowsDuringLoading = false,
}: {
  title: string
  subtitle: string
  rows: T[]
  columns: Column<T>[]
  empty: string
  isLoading?: boolean
  loadingLabel?: string
  preserveRowsDuringLoading?: boolean
}) {
  const showRowsWhileLoading = preserveRowsDuringLoading && isLoading && rows.length > 0
  return (
    <section className="data-block">
      <div className="section-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        {(!isLoading || showRowsWhileLoading) ? <Badge label={`${count(rows.length)} registros`} /> : null}
      </div>
      {isLoading && !showRowsWhileLoading ? (
        <div className="empty-state">{loadingLabel}</div>
      ) : rows.length === 0 ? (
        <div className="empty-state">{empty}</div>
      ) : (
        <>
          {showRowsWhileLoading ? <div className="empty-state compact">{loadingLabel}</div> : null}
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
        </>
      )}
    </section>
  )
}
