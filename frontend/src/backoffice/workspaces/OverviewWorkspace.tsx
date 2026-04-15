import { Badge, Metric, count } from '../shared'

type DashboardLike = {
  socios_total?: number
  empresas_total?: number
  comunidades_total?: number
  propiedades_total?: number
  propiedades_activas?: number
  cuentas_total?: number
  identidades_total?: number
  mandatos_total?: number
  contratos_vigentes?: number
  pagos_pendientes?: number
  pagos_atrasados?: number
  resoluciones_manuales_abiertas?: number
  dtes_borrador?: number
  mensajes_preparados?: number
}

type ManualSummaryLike = {
  total: number
  categorias: Array<{ category: string; total: number }>
} | null

type HealthLike = {
  status: string
  services: Record<string, { status: string }>
}

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'

export function OverviewWorkspace({
  dashboard,
  manualSummary,
  health,
  counts,
  toneFor,
}: {
  dashboard: DashboardLike | null
  manualSummary: ManualSummaryLike
  health: HealthLike
  counts: {
    socios: number
    empresas: number
    comunidades: number
    propiedades: number
    cuentas: number
    identidades: number
    mandatos: number
  }
  toneFor: (value: string) => Tone
}) {
  return (
    <>
      <section className="metric-grid">
        <Metric label="Propiedades activas" value={count(dashboard?.propiedades_activas)} tone="positive" />
        <Metric label="Contratos vigentes" value={count(dashboard?.contratos_vigentes)} tone="positive" />
        <Metric label="Pagos pendientes" value={count(dashboard?.pagos_pendientes)} tone="warning" />
        <Metric label="Pagos atrasados" value={count(dashboard?.pagos_atrasados)} tone="danger" />
        <Metric
          label="Resoluciones abiertas"
          value={count(dashboard?.resoluciones_manuales_abiertas ?? manualSummary?.total)}
          tone={(dashboard?.resoluciones_manuales_abiertas ?? manualSummary?.total) ? 'warning' : 'positive'}
        />
        <Metric label="DTE borrador" value={count(dashboard?.dtes_borrador)} tone="neutral" />
      </section>

      <section className="panel-grid">
        <section className="panel">
          <div className="section-heading"><div><h2>Patrimonio</h2><p>Owners, comunidades y propiedades activas.</p></div></div>
          <div className="list-stack">
            <div className="list-row"><span>Socios</span><strong>{count(dashboard?.socios_total ?? counts.socios)}</strong></div>
            <div className="list-row"><span>Empresas</span><strong>{count(dashboard?.empresas_total ?? counts.empresas)}</strong></div>
            <div className="list-row"><span>Comunidades</span><strong>{count(dashboard?.comunidades_total ?? counts.comunidades)}</strong></div>
            <div className="list-row"><span>Propiedades</span><strong>{count(dashboard?.propiedades_total ?? counts.propiedades)}</strong></div>
          </div>
        </section>
        <section className="panel">
          <div className="section-heading"><div><h2>Operación</h2><p>Cuentas, identidades y mandatos vigentes.</p></div></div>
          <div className="list-stack">
            <div className="list-row"><span>Cuentas recaudadoras</span><strong>{count(dashboard?.cuentas_total ?? counts.cuentas)}</strong></div>
            <div className="list-row"><span>Identidades de envío</span><strong>{count(dashboard?.identidades_total ?? counts.identidades)}</strong></div>
            <div className="list-row"><span>Mandatos</span><strong>{count(dashboard?.mandatos_total ?? counts.mandatos)}</strong></div>
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
            {manualSummary === null ? <div className="empty-state compact">Cargando cola manual...</div> : null}
            {manualSummary?.categorias.slice(0, 4).map((item) => (
              <div className="list-row" key={item.category}><span>{item.category.replaceAll('_', ' ')}</span><strong>{count(item.total)}</strong></div>
            ))}
            {manualSummary && !manualSummary.categorias.length ? <div className="empty-state compact">No hay categorías abiertas.</div> : null}
          </div>
        </section>
      </section>
    </>
  )
}
