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

type ReportingCompanyProgressDraft = {
  empresa_id: string
  fiscal_year: string
}

type ReportingCompanyReviewPackageDraft = {
  empresa_id: string
  fiscal_year: string
  bank_support_manifest: string
}

type ReportingMigrationDraft = {
  status: string
}

type ReportTraceability = {
  estado: string
  tipo_reporte: string
  fuentes: string[]
  controles: Record<string, string | number | boolean>
}

type ReportingFinancialSummary = {
  trazabilidad: ReportTraceability
  pagos_generados: number
  monto_facturable_total_clp: string
  monto_cobrado_total_clp: string
  eventos_contables_posteados: number
  asientos_contables: number
  dtes_emitidos: number
  control_cierre_mensual: Array<{
    empresa_id: number
    cierre_contable_estado: string
    cierre_contable_aprobado: boolean
    banco_cuadrado: boolean
    cuentas_bancarias_con_movimientos: number
    movimientos_bancarios_sin_resolver: number
    obligaciones_total: number
    obligaciones_pendientes: number
    f29_requerido: boolean
    f29_estado: string
    estado_control: string
    bloqueadores_periodo: string[]
  }>
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
  trazabilidad: ReportTraceability
  libro_diario: { resumen: Record<string, unknown> }
  libro_mayor: { resumen: Record<string, unknown> }
  balance_comprobacion: { resumen: Record<string, unknown> }
}

type ReportingAnnualSummary = {
  trazabilidad: ReportTraceability
  procesos_renta: Array<{ empresa_id: number; estado: string; fecha_preparacion: string | null; responsable_revision_ref: string }>
  ddjj_preparadas: Array<{ empresa_id: number; estado_preparacion: string; paquete_ref: string; responsable_revision_ref: string }>
  f22_preparados: Array<{ empresa_id: number; estado_preparacion: string; borrador_ref: string; responsable_revision_ref: string }>
}

type ReportingCompanyProgressSummary = {
  empresa: { id: number; razon_social: string; estado: string }
  fiscal_year: number
  tax_year: number
  classification: string
  progress_percent: number
  ready_for_company_accounting_review: boolean
  review_boundary: {
    meaning_when_ready: string
    autonomous_accounting: boolean
    final_tax_calculation: boolean
    sii_submission: boolean
    requires_responsible_review: boolean
    requires_expert_or_official_validation: boolean
    allowed_next_action: string
    not_allowed_actions: string[]
  }
  fiscal_config: {
    active: boolean
    regime_code: string
    supported: boolean
    supported_regime_code: string
  }
  phases: Record<string, {
    label: string
    status: string
    ready: boolean
    expected: number
    completed: number
    missing: Array<string | number>
  }>
  issue_counts: { blocking: number }
  issues: Array<{ code: string; severity: string; count: number; message: string }>
  next_blocking_phase: string
  trazabilidad: ReportTraceability
}

type ReportingCompanyCandidatesSummary = {
  selection_boundary: {
    purpose: string
    uses_external_sources: boolean
    opens_external_gates: boolean
    autonomous_accounting: boolean
    final_tax_calculation: boolean
    sii_submission: boolean
  }
  candidates: Array<{
    empresa: { id: number; razon_social: string; estado: string }
    fiscal_config_active: boolean
    fiscal_regime_code: string
    fiscal_regime_supported: boolean
    supported_fiscal_regime_code: string
    recommended_fiscal_year: number | null
    years: Array<{
      fiscal_year: number
      tax_year: number
      signals: {
        monthly_closes: number
        monthly_balances: number
        monthly_balances_squared: number
        f29_monthly: number
        annual_processes: number
        annual_trial_balance: number
        rli_cpt_workbooks: number
        annual_dossier: number
        annual_export: number
      }
      signal_count: number
      recommended: boolean
    }>
  }>
  summary: { companies_total: number; candidate_companies: number; candidate_years: number; unsupported_fiscal_regime_companies: number }
  trazabilidad: ReportTraceability
}

type ReportingCompanyReviewPackageSummary = {
  schema_version: string
  classification: string
  ready_for_productive_accounting_review: boolean
  summary: {
    accounting_progress_percent: number
    bank_support_coverage_percent: number
    blocking_issues_total: number
    warnings_total: number
  }
  empresa: { id: number; razon_social: string; estado: string }
  fiscal_year: number
  tax_year: number
  boundary: {
    autonomous_accounting: boolean
    final_tax_calculation: boolean
    sii_submission: boolean
    uses_external_integrations: boolean
    requires_responsible_review: boolean
    requires_expert_or_official_validation: boolean
  }
  bank_support_coverage: {
    classification: string
    coverage_percent: number
    ready_for_accounting_document_review: boolean
    summary: {
      required_operations: number
      operations_with_full_support: number
      attachments_total: number
      confirmations_total: number
    }
    operations: Array<{
      operation_ref: string
      label_ref: string
      status: string
      required_categories: string[]
      covered_categories: string[]
      missing_categories: string[]
      attachments_count: number
    }>
  }
  issues: Array<{ code: string; severity: string; count: number; message: string }>
  warnings: Array<{ code: string; severity: string; count: number; message: string }>
  evidence: Record<string, string>
  trazabilidad: ReportTraceability
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

function progressTone(value: ReportingCompanyProgressSummary): Tone {
  if (value.ready_for_company_accounting_review) return 'positive'
  if (value.classification === 'sin_datos') return 'danger'
  return 'warning'
}

function reviewPackageTone(value: ReportingCompanyReviewPackageSummary): Tone {
  if (value.ready_for_productive_accounting_review) return 'positive'
  if (value.classification === 'sin_datos') return 'danger'
  return 'warning'
}

function TraceabilityBlock({ value }: { value: ReportTraceability }) {
  return (
    <section className="panel">
      <div className="section-heading"><div><h2>Trazabilidad</h2><p>{value.tipo_reporte}</p></div><Badge label={value.estado} tone="positive" /></div>
      <div className="list-stack">
        <div className="list-row"><span>Fuentes</span><strong>{value.fuentes.join(', ')}</strong></div>
        {Object.entries(value.controles).map(([key, entry]) => (
          <div className="list-row" key={key}><span>{key}</span><strong>{String(entry)}</strong></div>
        ))}
      </div>
    </section>
  )
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
  handleFetchCompanyCandidatesSummary,
  reportingCompanyProgressDraft,
  setReportingCompanyProgressDraft,
  handleFetchCompanyProgressSummary,
  reportingCompanyReviewPackageDraft,
  setReportingCompanyReviewPackageDraft,
  handleFetchCompanyReviewPackageSummary,
  reportingMigrationDraft,
  setReportingMigrationDraft,
  handleFetchMigrationSummary,
  reportingFinancialSummary,
  reportingPartnerSummary,
  reportingBooksSummary,
  reportingAnnualSummary,
  reportingCompanyCandidatesSummary,
  reportingCompanyProgressSummary,
  reportingCompanyReviewPackageSummary,
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
  handleFetchCompanyCandidatesSummary: (event: FormEvent<HTMLFormElement>) => Promise<void>
  reportingCompanyProgressDraft: ReportingCompanyProgressDraft
  setReportingCompanyProgressDraft: Dispatch<SetStateAction<ReportingCompanyProgressDraft>>
  handleFetchCompanyProgressSummary: (event: FormEvent<HTMLFormElement>) => Promise<void>
  reportingCompanyReviewPackageDraft: ReportingCompanyReviewPackageDraft
  setReportingCompanyReviewPackageDraft: Dispatch<SetStateAction<ReportingCompanyReviewPackageDraft>>
  handleFetchCompanyReviewPackageSummary: (event: FormEvent<HTMLFormElement>) => Promise<void>
  reportingMigrationDraft: ReportingMigrationDraft
  setReportingMigrationDraft: Dispatch<SetStateAction<ReportingMigrationDraft>>
  handleFetchMigrationSummary: (event: FormEvent<HTMLFormElement>) => Promise<void>
  reportingFinancialSummary: ReportingFinancialSummary | null
  reportingPartnerSummary: ReportingPartnerSummary | null
  reportingBooksSummary: ReportingBooksSummary | null
  reportingAnnualSummary: ReportingAnnualSummary | null
  reportingCompanyCandidatesSummary: ReportingCompanyCandidatesSummary | null
  reportingCompanyProgressSummary: ReportingCompanyProgressSummary | null
  reportingCompanyReviewPackageSummary: ReportingCompanyReviewPackageSummary | null
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

          <section className="panel">
            <div className="section-heading"><div><h2>Candidatos contables</h2><p>Empresas y años con señales internas para medir primero.</p></div></div>
            <form className="entity-form" onSubmit={handleFetchCompanyCandidatesSummary}>
              <button type="submit" className="button-primary" disabled={isSubmitting}>Cargar candidatos</button>
            </form>
          </section>

          <section className="panel">
            <div className="section-heading"><div><h2>Progreso contable empresa</h2><p>Cierres, balances, F29, renta anual y dossier por año comercial.</p></div></div>
            <form className="entity-form" onSubmit={handleFetchCompanyProgressSummary}>
              <select value={reportingCompanyProgressDraft.empresa_id} onChange={(event) => setReportingCompanyProgressDraft((current) => ({ ...current, empresa_id: event.target.value }))}>
                <option value="">Selecciona empresa</option>
                {empresas.map((item) => (
                  <option key={item.id} value={item.id}>{item.razon_social}</option>
                ))}
              </select>
              <input placeholder="Año comercial" value={reportingCompanyProgressDraft.fiscal_year} onChange={(event) => setReportingCompanyProgressDraft((current) => ({ ...current, fiscal_year: event.target.value }))} />
              <button type="submit" className="button-primary" disabled={isSubmitting || !reportingCompanyProgressDraft.empresa_id}>Cargar progreso</button>
            </form>
          </section>

          <section className="panel">
            <div className="section-heading"><div><h2>Paquete de revisión</h2><p>Progreso interno y manifiesto bancario/leasing redactado.</p></div></div>
            <form className="entity-form" onSubmit={handleFetchCompanyReviewPackageSummary}>
              <select value={reportingCompanyReviewPackageDraft.empresa_id} onChange={(event) => setReportingCompanyReviewPackageDraft((current) => ({ ...current, empresa_id: event.target.value }))}>
                <option value="">Selecciona empresa</option>
                {empresas.map((item) => (
                  <option key={item.id} value={item.id}>{item.razon_social}</option>
                ))}
              </select>
              <input placeholder="Año comercial" value={reportingCompanyReviewPackageDraft.fiscal_year} onChange={(event) => setReportingCompanyReviewPackageDraft((current) => ({ ...current, fiscal_year: event.target.value }))} />
              <textarea rows={8} value={reportingCompanyReviewPackageDraft.bank_support_manifest} onChange={(event) => setReportingCompanyReviewPackageDraft((current) => ({ ...current, bank_support_manifest: event.target.value }))} />
              <button type="submit" className="button-primary" disabled={isSubmitting || !reportingCompanyReviewPackageDraft.empresa_id}>Cargar paquete</button>
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
          <TraceabilityBlock value={reportingFinancialSummary.trazabilidad} />
          <section className="metric-grid">
            <Metric label="Pagos generados" value={count(reportingFinancialSummary.pagos_generados)} tone="neutral" />
            <Metric label="Facturable total" value={reportingFinancialSummary.monto_facturable_total_clp} tone="positive" />
            <Metric label="Cobrado total" value={reportingFinancialSummary.monto_cobrado_total_clp} tone="positive" />
            <Metric label="Eventos posteados" value={count(reportingFinancialSummary.eventos_contables_posteados)} tone="neutral" />
            <Metric label="Asientos" value={count(reportingFinancialSummary.asientos_contables)} tone="neutral" />
            <Metric label="DTE emitidos" value={count(reportingFinancialSummary.dtes_emitidos)} tone="neutral" />
          </section>
          <TableBlock title="Control mensual" subtitle="Cierre, banco, movimientos no resueltos, obligaciones y F29 por empresa." rows={reportingFinancialSummary.control_cierre_mensual.map((item) => ({ id: item.empresa_id, ...item }))} empty="No hay control mensual para este resumen." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa_id)?.razon_social || row.empresa_id },
            { label: 'Control', render: (row) => <Badge label={row.estado_control} tone={row.estado_control === 'listo' ? 'positive' : 'warning'} /> },
            { label: 'Cierre', render: (row) => <Badge label={row.cierre_contable_estado} tone={row.cierre_contable_aprobado ? 'positive' : 'warning'} /> },
            { label: 'Banco', render: (row) => <Badge label={row.banco_cuadrado ? 'cuadrado' : 'bloqueado'} tone={row.banco_cuadrado ? 'positive' : 'danger'} /> },
            { label: 'Mov.', render: (row) => count(row.cuentas_bancarias_con_movimientos) },
            { label: 'Sin resolver', render: (row) => <Badge label={count(row.movimientos_bancarios_sin_resolver)} tone={row.movimientos_bancarios_sin_resolver > 0 ? 'warning' : 'positive'} /> },
            { label: 'Obl.', render: (row) => `${count(row.obligaciones_total)} / ${count(row.obligaciones_pendientes)}` },
            { label: 'F29', render: (row) => <Badge label={row.f29_requerido ? row.f29_estado : 'no_aplica'} tone={row.f29_requerido ? toneFor(row.f29_estado) : 'neutral'} /> },
            { label: 'Bloqueadores', render: (row) => row.bloqueadores_periodo.join(', ') || 'Ninguno' },
          ]} />
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
          <TraceabilityBlock value={reportingBooksSummary.trazabilidad} />
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
          <TraceabilityBlock value={reportingAnnualSummary.trazabilidad} />
          <TableBlock title="Procesos renta anual" subtitle="Resumen consolidado por empresa." rows={reportingAnnualSummary.procesos_renta.map((item) => ({ id: item.empresa_id, ...item }))} empty="No hay procesos de renta para este filtro." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa_id)?.razon_social || row.empresa_id },
            { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
            { label: 'Responsable', render: (row) => row.responsable_revision_ref || 'Sin responsable' },
            { label: 'Preparación', render: (row) => row.fecha_preparacion || 'Sin fecha' },
          ]} />
          <TableBlock title="DDJJ preparadas" subtitle="Paquetes DDJJ por empresa." rows={reportingAnnualSummary.ddjj_preparadas.map((item) => ({ id: item.empresa_id, ...item }))} empty="No hay DDJJ para este resumen." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa_id)?.razon_social || row.empresa_id },
            { label: 'Paquete', render: (row) => row.paquete_ref || 'Sin ref' },
            { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
            { label: 'Responsable', render: (row) => row.responsable_revision_ref || 'Sin responsable' },
          ]} />
          <TableBlock title="F22 preparados" subtitle="Borradores F22 por empresa." rows={reportingAnnualSummary.f22_preparados.map((item) => ({ id: item.empresa_id, ...item }))} empty="No hay F22 para este resumen." columns={[
            { label: 'Empresa', render: (row) => empresaById.get(row.empresa_id)?.razon_social || row.empresa_id },
            { label: 'Borrador', render: (row) => row.borrador_ref || 'Sin ref' },
            { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
            { label: 'Responsable', render: (row) => row.responsable_revision_ref || 'Sin responsable' },
          ]} />
        </>
      ) : null}

      {reportingCompanyCandidatesSummary ? (
        <>
          <TraceabilityBlock value={reportingCompanyCandidatesSummary.trazabilidad} />
          <section className="metric-grid">
            <Metric label="Empresas visibles" value={count(reportingCompanyCandidatesSummary.summary.companies_total)} tone="neutral" />
            <Metric label="Con señales" value={count(reportingCompanyCandidatesSummary.summary.candidate_companies)} tone={reportingCompanyCandidatesSummary.summary.candidate_companies ? 'positive' : 'warning'} />
            <Metric label="Años candidatos" value={count(reportingCompanyCandidatesSummary.summary.candidate_years)} tone="neutral" />
            <Metric label="Régimen no soportado" value={count(reportingCompanyCandidatesSummary.summary.unsupported_fiscal_regime_companies)} tone={reportingCompanyCandidatesSummary.summary.unsupported_fiscal_regime_companies ? 'danger' : 'positive'} />
            <Metric label="Fuentes externas" value={reportingCompanyCandidatesSummary.selection_boundary.uses_external_sources ? 'usa' : 'no usa'} tone={reportingCompanyCandidatesSummary.selection_boundary.uses_external_sources ? 'danger' : 'positive'} />
          </section>
          <TableBlock title="Candidatos para medir" subtitle="Años detectados desde cierres, balances, F29 y procesos anuales internos." rows={reportingCompanyCandidatesSummary.candidates.flatMap((candidate) => (
            candidate.years.map((year) => ({
              id: `${candidate.empresa.id}-${year.fiscal_year}`,
              empresa_id: candidate.empresa.id,
              empresa: candidate.empresa.razon_social,
              fiscal_config_active: candidate.fiscal_config_active,
              fiscal_regime_code: candidate.fiscal_regime_code,
              fiscal_regime_supported: candidate.fiscal_regime_supported,
              fiscal_year: year.fiscal_year,
              tax_year: year.tax_year,
              signal_count: year.signal_count,
              recommended: year.recommended,
              ...year.signals,
            }))
          ))} empty="No hay candidatos con señales contables internas." columns={[
            { label: 'Empresa', render: (row) => row.empresa },
            { label: 'Año', render: (row) => `${row.fiscal_year} / AT ${row.tax_year}` },
            { label: 'Fiscal', render: (row) => <Badge label={!row.fiscal_config_active ? 'faltante' : row.fiscal_regime_supported ? 'soportada' : 'no soportada'} tone={!row.fiscal_config_active ? 'warning' : row.fiscal_regime_supported ? 'positive' : 'danger'} /> },
            { label: 'Señales', render: (row) => <Badge label={count(row.signal_count)} tone={row.recommended ? 'positive' : 'neutral'} /> },
            { label: 'Cierres', render: (row) => count(row.monthly_closes) },
            { label: 'Balances', render: (row) => `${count(row.monthly_balances_squared)} / ${count(row.monthly_balances)}` },
            { label: 'F29', render: (row) => count(row.f29_monthly) },
            { label: 'Anual', render: (row) => `${count(row.annual_processes)} / ${count(row.annual_trial_balance)} / ${count(row.rli_cpt_workbooks)} / ${count(row.annual_dossier)} / ${count(row.annual_export)}` },
            { label: 'Acción', render: (row) => (
              <button type="button" className="button-secondary" onClick={() => {
                const nextDraft = { empresa_id: String(row.empresa_id), fiscal_year: String(row.fiscal_year) }
                setReportingCompanyProgressDraft(nextDraft)
                setReportingCompanyReviewPackageDraft((current) => ({ ...current, ...nextDraft }))
              }}>
                Usar
              </button>
            ) },
          ]} />
        </>
      ) : null}

      {reportingCompanyProgressSummary ? (
        <>
          <TraceabilityBlock value={reportingCompanyProgressSummary.trazabilidad} />
          <section className="metric-grid">
            <Metric label="Empresa" value={reportingCompanyProgressSummary.empresa.razon_social} tone="neutral" />
            <Metric label="Año comercial" value={String(reportingCompanyProgressSummary.fiscal_year)} tone="neutral" />
            <Metric label="AT" value={String(reportingCompanyProgressSummary.tax_year)} tone="neutral" />
            <Metric label="Avance" value={`${reportingCompanyProgressSummary.progress_percent}%`} tone={progressTone(reportingCompanyProgressSummary)} />
            <Metric label="Clasificación" value={reportingCompanyProgressSummary.classification} tone={progressTone(reportingCompanyProgressSummary)} />
            <Metric label="Bloqueos" value={count(reportingCompanyProgressSummary.issue_counts.blocking)} tone={reportingCompanyProgressSummary.issue_counts.blocking ? 'warning' : 'positive'} />
            <Metric label="Régimen" value={reportingCompanyProgressSummary.fiscal_config.regime_code || 'Sin configuración'} tone={!reportingCompanyProgressSummary.fiscal_config.active ? 'warning' : reportingCompanyProgressSummary.fiscal_config.supported ? 'positive' : 'danger'} />
          </section>
          <section className="panel">
            <div className="section-heading">
              <div><h2>Próximo corte</h2><p>{reportingCompanyProgressSummary.empresa.estado}</p></div>
              <Badge label={reportingCompanyProgressSummary.ready_for_company_accounting_review ? 'revisable' : 'no_revisable'} tone={reportingCompanyProgressSummary.ready_for_company_accounting_review ? 'positive' : 'warning'} />
            </div>
            <div className="list-stack">
              <div className="list-row"><span>Siguiente fase bloqueante</span><strong>{reportingCompanyProgressSummary.next_blocking_phase || 'Sin bloqueo'}</strong></div>
              <div className="list-row"><span>Acción permitida</span><strong>{reportingCompanyProgressSummary.review_boundary.allowed_next_action}</strong></div>
              <div className="list-row"><span>Contabilidad autónoma</span><strong>{reportingCompanyProgressSummary.review_boundary.autonomous_accounting ? 'habilitada' : 'bloqueada'}</strong></div>
              <div className="list-row"><span>Cálculo tributario final</span><strong>{reportingCompanyProgressSummary.review_boundary.final_tax_calculation ? 'habilitado' : 'bloqueado'}</strong></div>
              <div className="list-row"><span>Presentación SII</span><strong>{reportingCompanyProgressSummary.review_boundary.sii_submission ? 'habilitada' : 'bloqueada'}</strong></div>
            </div>
          </section>
          <TableBlock title="Fases contables y renta" subtitle="Medición objetiva por empresa y año comercial." rows={Object.entries(reportingCompanyProgressSummary.phases).map(([key, phase]) => ({ id: key, key, ...phase }))} empty="No hay fases para este reporte." columns={[
            { label: 'Fase', render: (row) => row.label },
            { label: 'Estado', render: (row) => <Badge label={row.status} tone={row.ready ? 'positive' : toneFor(row.status)} /> },
            { label: 'Completado', render: (row) => `${count(row.completed)} / ${count(row.expected)}` },
            { label: 'Faltantes', render: (row) => row.missing.map((item) => String(item)).join(', ') || 'Ninguno' },
          ]} />
          <TableBlock title="Bloqueos detectados" subtitle="Condiciones pendientes antes de revisión contable/renta." rows={reportingCompanyProgressSummary.issues.map((item, index) => ({ id: `${item.code}-${index}`, ...item }))} empty="No hay bloqueos para esta empresa/año." columns={[
            { label: 'Código', render: (row) => row.code },
            { label: 'Severidad', render: (row) => <Badge label={row.severity} tone={row.severity === 'blocking' ? 'warning' : 'neutral'} /> },
            { label: 'Conteo', render: (row) => count(row.count) },
            { label: 'Mensaje', render: (row) => row.message },
          ]} />
        </>
      ) : null}

      {reportingCompanyReviewPackageSummary ? (
        <>
          <TraceabilityBlock value={reportingCompanyReviewPackageSummary.trazabilidad} />
          <section className="metric-grid">
            <Metric label="Empresa" value={reportingCompanyReviewPackageSummary.empresa.razon_social} tone="neutral" />
            <Metric label="Año comercial" value={String(reportingCompanyReviewPackageSummary.fiscal_year)} tone="neutral" />
            <Metric label="AT" value={String(reportingCompanyReviewPackageSummary.tax_year)} tone="neutral" />
            <Metric label="Clasificación" value={reportingCompanyReviewPackageSummary.classification} tone={reviewPackageTone(reportingCompanyReviewPackageSummary)} />
            <Metric label="Progreso interno" value={`${reportingCompanyReviewPackageSummary.summary.accounting_progress_percent}%`} tone="neutral" />
            <Metric label="Soporte banco/leasing" value={`${reportingCompanyReviewPackageSummary.summary.bank_support_coverage_percent}%`} tone={reportingCompanyReviewPackageSummary.bank_support_coverage.ready_for_accounting_document_review ? 'positive' : 'warning'} />
            <Metric label="Bloqueos" value={count(reportingCompanyReviewPackageSummary.summary.blocking_issues_total)} tone={reportingCompanyReviewPackageSummary.summary.blocking_issues_total ? 'warning' : 'positive'} />
            <Metric label="Revisión productiva" value={reportingCompanyReviewPackageSummary.ready_for_productive_accounting_review ? 'preparada' : 'pendiente'} tone={reviewPackageTone(reportingCompanyReviewPackageSummary)} />
          </section>
          <section className="panel">
            <div className="section-heading">
              <div><h2>Frontera del paquete</h2><p>{reportingCompanyReviewPackageSummary.schema_version}</p></div>
              <Badge label={reportingCompanyReviewPackageSummary.ready_for_productive_accounting_review ? 'preparado' : 'pendiente'} tone={reviewPackageTone(reportingCompanyReviewPackageSummary)} />
            </div>
            <div className="list-stack">
              <div className="list-row"><span>Integraciones externas</span><strong>{reportingCompanyReviewPackageSummary.boundary.uses_external_integrations ? 'habilitadas' : 'bloqueadas'}</strong></div>
              <div className="list-row"><span>Contabilidad autónoma</span><strong>{reportingCompanyReviewPackageSummary.boundary.autonomous_accounting ? 'habilitada' : 'bloqueada'}</strong></div>
              <div className="list-row"><span>Cálculo tributario final</span><strong>{reportingCompanyReviewPackageSummary.boundary.final_tax_calculation ? 'habilitado' : 'bloqueado'}</strong></div>
              <div className="list-row"><span>Presentación SII</span><strong>{reportingCompanyReviewPackageSummary.boundary.sii_submission ? 'habilitada' : 'bloqueada'}</strong></div>
              <div className="list-row"><span>Revisión responsable</span><strong>{reportingCompanyReviewPackageSummary.boundary.requires_responsible_review ? 'requerida' : 'no requerida'}</strong></div>
              <div className="list-row"><span>Validación experta/oficial</span><strong>{reportingCompanyReviewPackageSummary.boundary.requires_expert_or_official_validation ? 'requerida' : 'no requerida'}</strong></div>
            </div>
          </section>
          <TableBlock title="Cobertura bancaria/leasing" subtitle="Operaciones declaradas en el manifiesto redactado." rows={reportingCompanyReviewPackageSummary.bank_support_coverage.operations.map((item, index) => ({ id: `${item.operation_ref}-${index}`, ...item }))} empty="El manifiesto no declara operaciones bancarias/leasing." columns={[
            { label: 'Operación', render: (row) => row.operation_ref },
            { label: 'Etiqueta', render: (row) => row.label_ref || 'Sin etiqueta' },
            { label: 'Estado', render: (row) => <Badge label={row.status} tone={row.status === 'covered' ? 'positive' : 'warning'} /> },
            { label: 'Adjuntos', render: (row) => count(row.attachments_count) },
            { label: 'Cubiertas', render: (row) => row.covered_categories.join(', ') || 'Ninguna' },
            { label: 'Faltantes', render: (row) => row.missing_categories.join(', ') || 'Ninguna' },
          ]} />
          <TableBlock title="Problemas del paquete" subtitle="Bloqueos y advertencias antes de revisión responsable." rows={[
            ...reportingCompanyReviewPackageSummary.issues.map((item, index) => ({ id: `issue-${index}`, tipo: 'bloqueo', ...item })),
            ...reportingCompanyReviewPackageSummary.warnings.map((item, index) => ({ id: `warning-${index}`, tipo: 'advertencia', ...item })),
          ]} empty="No hay problemas declarados en este paquete." columns={[
            { label: 'Tipo', render: (row) => row.tipo },
            { label: 'Código', render: (row) => row.code },
            { label: 'Severidad', render: (row) => <Badge label={row.severity} tone={row.severity === 'blocking' ? 'warning' : 'neutral'} /> },
            { label: 'Conteo', render: (row) => count(row.count) },
            { label: 'Mensaje', render: (row) => row.message },
          ]} />
          <TableBlock title="Evidencia técnica" subtitle="Hashes derivados del progreso y del manifiesto redactado." rows={Object.entries(reportingCompanyReviewPackageSummary.evidence).map(([key, value]) => ({ id: key, key, value }))} empty="No hay hashes de evidencia para este paquete." columns={[
            { label: 'Clave', render: (row) => row.key },
            { label: 'Hash', render: (row) => row.value },
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
