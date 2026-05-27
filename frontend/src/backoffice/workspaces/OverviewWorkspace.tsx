import { Badge, Metric } from '../shared'
import { count } from '../shared-utils'

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
  movimientos_sin_clasificar?: number
  diferencias_banco_sistema?: number
  contratos_por_vencer?: number
  avisos_termino_registrados?: number
  garantias_incompletas?: number
  fallas_integracion?: number
  cierres_bloqueados?: number
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

type RuntimeSignalLike = {
  status?: string | null
  source_kind?: string | null
  has_evidence_ref?: boolean
  value?: Record<string, unknown>
}

type OperationalObservabilityLike = {
  classification: string
  ready_for_stage7_observability: boolean
  issue_counts: Record<string, number>
  sections: {
    runtime_signals: Record<string, unknown>
  }
} | null

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'

function runtimeSignal(observability: OperationalObservabilityLike, key: string): RuntimeSignalLike {
  const value = observability?.sections.runtime_signals[key]
  return value && typeof value === 'object' ? value as RuntimeSignalLike : {}
}

function observabilityTone(value: string | boolean | undefined | null): Tone {
  if (value === true) return 'positive'
  const normalized = String(value || '').trim().toLowerCase()
  if (['ok', 'resuelto_confirmado', 'ready'].includes(normalized)) return 'positive'
  if (['attention', 'parcial', 'missing', 'pendiente'].includes(normalized)) return 'warning'
  if (['blocked', 'bloqueado', 'down', 'fallido'].includes(normalized)) return 'danger'
  return 'neutral'
}

export function OverviewWorkspace({
  dashboard,
  manualSummary,
  operationalObservability,
  health,
  counts,
  toneFor,
}: {
  dashboard: DashboardLike | null
  manualSummary: ManualSummaryLike
  operationalObservability: OperationalObservabilityLike
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
  const manualResolutionCount = dashboard?.resoluciones_manuales_abiertas ?? manualSummary?.total ?? 0
  const monthlyLatencySignal = runtimeSignal(operationalObservability, 'monthly_calculation_latency')
  const queueRuntimeSignal = runtimeSignal(operationalObservability, 'queue_runtime')
  const failedWebhooksSignal = runtimeSignal(operationalObservability, 'failed_webhooks')
  const failedCronsSignal = runtimeSignal(operationalObservability, 'failed_crons')
  const observabilityAttention = operationalObservability?.issue_counts.attention ?? 0

  return (
    <>
      <section className="metric-grid">
        <Metric label="Propiedades activas" value={count(dashboard?.propiedades_activas)} tone="positive" />
        <Metric label="Contratos vigentes" value={count(dashboard?.contratos_vigentes)} tone="positive" />
        <Metric label="Pagos pendientes" value={count(dashboard?.pagos_pendientes)} tone="warning" />
        <Metric label="Pagos atrasados" value={count(dashboard?.pagos_atrasados)} tone="danger" />
        <Metric
          label="Mov. sin clasificar"
          value={count(dashboard?.movimientos_sin_clasificar)}
          tone={dashboard?.movimientos_sin_clasificar ? 'warning' : 'positive'}
        />
        <Metric
          label="Diferencias banco"
          value={count(dashboard?.diferencias_banco_sistema)}
          tone={dashboard?.diferencias_banco_sistema ? 'danger' : 'positive'}
        />
        <Metric
          label="Resoluciones abiertas"
          value={count(manualResolutionCount)}
          tone={manualResolutionCount ? 'warning' : 'positive'}
        />
        <Metric label="DTE borrador" value={count(dashboard?.dtes_borrador)} tone="neutral" />
        <Metric
          label="Issues operación"
          value={count(observabilityAttention)}
          tone={observabilityAttention ? 'warning' : 'positive'}
        />
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
          <div className="section-heading"><div><h2>Bloqueadores operativos</h2><p>Alertas PRD para priorizar cierre y continuidad.</p></div></div>
          <div className="list-stack">
            <div className="list-row"><span>Contratos por vencer</span><strong>{count(dashboard?.contratos_por_vencer)}</strong></div>
            <div className="list-row"><span>Avisos de término</span><strong>{count(dashboard?.avisos_termino_registrados)}</strong></div>
            <div className="list-row"><span>Garantías incompletas</span><strong>{count(dashboard?.garantias_incompletas)}</strong></div>
            <div className="list-row"><span>Fallas de integración</span><strong>{count(dashboard?.fallas_integracion)}</strong></div>
            <div className="list-row"><span>Cierres bloqueados</span><strong>{count(dashboard?.cierres_bloqueados)}</strong></div>
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
          <div className="section-heading"><div><h2>Operación productiva</h2><p>Gates, backlog y señales runtime.</p></div></div>
          <div className="list-stack">
            {operationalObservability ? (
              <>
                <div className="list-row">
                  <span>Clasificación</span>
                  <Badge
                    label={operationalObservability.classification}
                    tone={observabilityTone(operationalObservability.classification)}
                  />
                </div>
                <div className="list-row">
                  <span>Gate observabilidad</span>
                  <Badge
                    label={operationalObservability.ready_for_stage7_observability ? 'ok' : 'parcial'}
                    tone={observabilityTone(operationalObservability.ready_for_stage7_observability)}
                  />
                </div>
                <div className="list-row"><span>Latencia mensual</span><Badge label={monthlyLatencySignal.status || 'missing'} tone={observabilityTone(monthlyLatencySignal.status)} /></div>
                <div className="list-row"><span>Colas y tareas</span><Badge label={queueRuntimeSignal.status || 'missing'} tone={observabilityTone(queueRuntimeSignal.status)} /></div>
                <div className="list-row"><span>Webhooks fallidos</span><Badge label={failedWebhooksSignal.status || 'missing'} tone={observabilityTone(failedWebhooksSignal.status)} /></div>
                <div className="list-row"><span>Crons fallidos</span><Badge label={failedCronsSignal.status || 'missing'} tone={observabilityTone(failedCronsSignal.status)} /></div>
              </>
            ) : (
              <div className="empty-state compact">Auditoría operativa no cargada.</div>
            )}
          </div>
        </section>
        <section className="panel">
          <div className="section-heading"><div><h2>Cola manual</h2><p>Resumen rápido del backlog asistido.</p></div></div>
          <div className="list-stack">
            {manualSummary === null ? (
              manualResolutionCount > 0
                ? <div className="empty-state compact">Actualizando detalle de {count(manualResolutionCount)} resoluciones...</div>
                : <div className="empty-state compact">No hay categorías abiertas.</div>
            ) : null}
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
