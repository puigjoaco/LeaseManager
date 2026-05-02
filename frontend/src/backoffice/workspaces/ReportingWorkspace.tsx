import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, Metric, TableBlock } from '../shared'

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'

type CurrentUserLike = {
  username: string
  display_name: string
} | null

type EmpresaItem = {
  id: number
  razon_social: string
}

type SocioItem = {
  id: number
  nombre: string
}

type ReportingFinancialDraft = {
  anio: string
  mes: string
  empresa_id: string
}

type ReportingPartnerDraft = {
  socio_id: string
}

type ReportingBooksDraft = {
  empresa_id: string
  periodo: string
}

type ReportingAnnualDraft = {
  anio_tributario: string
  empresa_id: string
}

type ReportingMigrationDraft = {
  status: string
}

type ReportingFinancialSummary = {
  pagos_generados: number
  monto_facturable_total_clp: string
  monto_cobrado_total_clp: string
  eventos_contables_posteados: number
  asientos_contables: number
  dtes_emitidos: number
  obligaciones: Array<{ tipo: string; monto_calculado: string; estado_preparacion: string }>
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
  periodo: string
  libro_diario: { resumen: Record<string, unknown> }
  libro_mayor: { resumen: Record<string, unknown> }
  balance_comprobacion: { resumen: Record<string, unknown> }
}

type ReportingAnnualSummary = {
  procesos_renta: Array<{ empresa_id: number; estado: string; fecha_preparacion: string | null }>
  ddjj_preparadas: Array<{ empresa_id: number; estado_preparacion: string; paquete_ref: string }>
  f22_preparados: Array<{ empresa_id: number; estado_preparacion: string; borrador_ref: string }>
}

type ReportingMigrationSummary = {
  total: number
  categorias: Array<{ category: string; total: number }>
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

function sumPercentages(values: Array<{ porcentaje: string }>) {
  const total = values.reduce((accumulator, item) => accumulator + Number(item.porcentaje || 0), 0)
  return `${total.toFixed(2)}%`
}

export function ReportingWorkspace({
  effectiveRole,
  effectiveRoles,
  currentUser,
  reportingFinancialDraft,
  setReportingFinancialDraft,
  handleFetchFinancialSummary,
  reportingPartnerDraft,
  setReportingPartnerDraft,
  handleFetchPartnerSummary,
  reportingBooksDraft,
  setReportingBooksDraft,
  handleFetchBooksSummary,
  reportingAnnualDraft,
  setReportingAnnualDraft,
  handleFetchAnnualSummary,
  reportingMigrationDraft,
  setReportingMigrationDraft,
  handleFetchMigrationSummary,
  reportingFinancialSummary,
  reportingPartnerSummary,
  reportingBooksSummary,
  reportingAnnualSummary,
  reportingMigrationSummary,
  empresas,
  socios,
  empresaById,
  isSubmitting,
  toneFor,
  count,
}: {
  effectiveRole: string
  effectiveRoles: string[]
  currentUser: CurrentUserLike
  reportingFinancialDraft: ReportingFinancialDraft
  setReportingFinancialDraft: Dispatch<SetStateAction<ReportingFinancialDraft>>
  handleFetchFinancialSummary: (event: FormEvent<HTMLFormElement>) => Promise<void>
  reportingPartnerDraft: ReportingPartnerDraft
  setReportingPartnerDraft: Dispatch<SetStateAction<ReportingPartnerDraft>>
  handleFetchPartnerSummary: (event: FormEvent<HTMLFormElement>) => Promise<void>
  reportingBooksDraft: ReportingBooksDraft
  setReportingBooksDraft: Dispatch<SetStateAction<ReportingBooksDraft>>
  handleFetchBooksSummary: (event: FormEvent<HTMLFormElement>) => Promise<void>
  reportingAnnualDraft: ReportingAnnualDraft
  setReportingAnnualDraft: Dispatch<SetStateAction<ReportingAnnualDraft>>
  handleFetchAnnualSummary: (event: FormEvent<HTMLFormElement>) => Promise<void>
  reportingMigrationDraft: ReportingMigrationDraft
  setReportingMigrationDraft: Dispatch<SetStateAction<ReportingMigrationDraft>>
  handleFetchMigrationSummary: (event: FormEvent<HTMLFormElement>) => Promise<void>
  reportingFinancialSummary: ReportingFinancialSummary | null
  reportingPartnerSummary: ReportingPartnerSummary | null
  reportingBooksSummary: ReportingBooksSummary | null
  reportingAnnualSummary: ReportingAnnualSummary | null
  reportingMigrationSummary: ReportingMigrationSummary | null
  empresas: EmpresaItem[]
  socios: SocioItem[]
  empresaById: ReadonlyMap<number, EmpresaItem>
  isSubmitting: boolean
  toneFor: (value: string) => Tone
  count: (value: number | undefined) => string
}) {
  const canReadMigrationBacklog = effectiveRoles.includes('AdministradorGlobal')
  const isReadOnlyReporting =
    !canReadMigrationBacklog
    && (effectiveRoles.includes('RevisorFiscalExterno') || effectiveRoles.includes('Socio'))

  return (
    <>
      {isReadOnlyReporting ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Reporting.</div> : null}
      {effectiveRole === 'Socio' ? (
        <>
          <section className="panel">
            <div className="section-heading"><div><h2>Resumen propio</h2><p>Participaciones, propiedades y estado relacionado.</p></div></div>
            <div className="list-stack">
              <div className="list-row"><span>Perfil</span><strong>{currentUser?.display_name || currentUser?.username}</strong></div>
              <div className="list-row"><span>Socio vinculado</span><strong>{reportingPartnerSummary?.socio.nombre || 'Sin resumen cargado'}</strong></div>
              <div className="list-row"><span>RUT</span><strong>{reportingPartnerSummary?.socio.rut || 'Sin dato'}</strong></div>
            </div>
          </section>
          {reportingPartnerSummary ? (
            <section className="metric-grid compact-grid">
              <Metric label="Empresas" value={count(reportingPartnerSummary.participaciones_empresas.length)} tone="neutral" />
              <Metric label="Comunidades" value={count(reportingPartnerSummary.participaciones_comunidades.length)} tone="neutral" />
              <Metric label="Propiedades directas" value={count(reportingPartnerSummary.propiedades_directas.length)} tone="neutral" />
              <Metric label="Contratos directos" value={count(reportingPartnerSummary.contratos_directos_activos)} tone="positive" />
              <Metric label="Estados de cuenta" value={count(reportingPartnerSummary.estados_cuenta_relacionados)} tone="neutral" />
              <Metric label="Participación comunitaria" value={sumPercentages(reportingPartnerSummary.participaciones_comunidades)} tone="positive" />
            </section>
          ) : null}
        </>
      ) : (
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

          {canReadMigrationBacklog ? (
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
          ) : null}
        </section>
      )}

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

      {canReadMigrationBacklog && reportingMigrationSummary ? (
        <>
          <section className="metric-grid">
            <Metric label="Resoluciones" value={count(reportingMigrationSummary.total)} tone={reportingMigrationSummary.total ? 'warning' : 'positive'} />
          </section>
          <TableBlock title="Categorías de backlog" subtitle="Conteo de resoluciones manuales por categoría." rows={reportingMigrationSummary.categorias.map((item, index) => ({ id: index + 1, ...item }))} empty="No hay categorías para este estado." columns={[
            { label: 'Categoría', render: (row) => row.category },
            { label: 'Total', render: (row) => count(row.total) },
          ]} />
          <TableBlock title="Propiedades owner manual required" subtitle="Detalle del backlog manual de migración." rows={reportingMigrationSummary.propiedades_owner_manual_required.map((item, index) => {
            return {
              id: index + 1,
              scope_reference: item.scope_reference,
              summary: item.summary,
              codigo: item.codigo,
              direccion: item.direccion,
              candidate_owner_model: item.candidate_owner_model,
              participaciones_count: item.participaciones_count,
              total_pct: item.total_pct,
              blocked_contract_legacy_ids: item.blocked_contract_legacy_ids,
              socios: item.socios,
            }
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
  )
}
