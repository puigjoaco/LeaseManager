import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock, toneFor, stamp } from '../shared'

type AuditEventItem = {
  id: number
  actor_user_display: string
  event_type: string
  severity: string
  entity_type: string
  entity_id: string
  summary: string
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

type ManualResolutionDraft = {
  status: string
  rationale: string
  pago_mensual_id: string
}

export function AuditWorkspace({
  effectiveRole,
  canEditAudit,
  auditHeading,
  activeManualResolution,
  editingManualResolutionId,
  manualResolutionDraft,
  setManualResolutionDraft,
  handleUpdateManualResolution,
  cancelEditManualResolution,
  filteredAuditEvents,
  filteredManualResolutions,
  startEditManualResolution,
  isSubmitting,
  isLoading,
}: {
  effectiveRole: string
  canEditAudit: boolean
  auditHeading: { title: string; subtitle: string }
  activeManualResolution: ManualResolutionItem | null
  editingManualResolutionId: string | null
  manualResolutionDraft: ManualResolutionDraft
  setManualResolutionDraft: Dispatch<SetStateAction<ManualResolutionDraft>>
  handleUpdateManualResolution: (event: FormEvent<HTMLFormElement>) => Promise<void>
  cancelEditManualResolution: () => void
  filteredAuditEvents: AuditEventItem[]
  filteredManualResolutions: ManualResolutionItem[]
  startEditManualResolution: (row: ManualResolutionItem) => void
  isSubmitting: boolean
  isLoading: boolean
}) {
  const isUnknownIncomeResolution = activeManualResolution?.category === 'conciliacion.ingreso_desconocido'
  const candidatePaymentIds = Array.isArray(activeManualResolution?.metadata?.payment_candidate_ids)
    ? activeManualResolution.metadata.payment_candidate_ids.join(', ')
    : ''

  return (
    <>
      {!canEditAudit ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Audit.</div> : null}
      {canEditAudit ? (
        <section className="form-grid">
          <section className="panel">
            <div className="section-heading"><div><h2>{editingManualResolutionId ? 'Editar resolución manual' : 'Cola de resolución manual'}</h2><p>{auditHeading.subtitle}</p></div></div>
            {activeManualResolution ? (
              <div className="list-stack">
                <div className="list-row"><span>Categoría</span><strong>{activeManualResolution.category}</strong></div>
                <div className="list-row"><span>Scope</span><strong>{activeManualResolution.scope_type} · {activeManualResolution.scope_reference}</strong></div>
                <div className="list-row"><span>Resumen</span><strong>{activeManualResolution.summary}</strong></div>
              </div>
            ) : (
              <div className="empty-state compact">Selecciona una resolución desde la tabla para actualizar su estado o rationale.</div>
            )}
            <form className="entity-form subform" onSubmit={handleUpdateManualResolution}>
              <select value={manualResolutionDraft.status} onChange={(event) => setManualResolutionDraft((current) => ({ ...current, status: event.target.value }))}>
                <option value="open">Open</option>
                <option value="in_review">In review</option>
                <option value="resolved">Resolved</option>
              </select>
              <input placeholder="Rationale" value={manualResolutionDraft.rationale} onChange={(event) => setManualResolutionDraft((current) => ({ ...current, rationale: event.target.value }))} />
              {isUnknownIncomeResolution ? (
                <>
                  <input
                    placeholder="Pago mensual ID"
                    value={manualResolutionDraft.pago_mensual_id}
                    onChange={(event) => setManualResolutionDraft((current) => ({ ...current, pago_mensual_id: event.target.value }))}
                  />
                  {candidatePaymentIds ? <div className="empty-state compact">Candidatos sugeridos: {candidatePaymentIds}</div> : null}
                </>
              ) : null}
              <div className="inline-actions">
                <button type="submit" className="button-primary" disabled={isSubmitting || !editingManualResolutionId}>Guardar resolución</button>
                {editingManualResolutionId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditManualResolution}>Cancelar</button> : null}
              </div>
            </form>
          </section>
          <section className="panel">
            <div className="section-heading"><div><h2>Metadata</h2><p>Contexto crudo de la resolución seleccionada.</p></div></div>
            {activeManualResolution ? (
              <pre className="json-block">{JSON.stringify(activeManualResolution.metadata, null, 2)}</pre>
            ) : (
              <div className="empty-state">No hay resolución seleccionada.</div>
            )}
          </section>
        </section>
      ) : null}

      {effectiveRole !== 'OperadorDeCartera' ? (
        <TableBlock title="Eventos auditables" subtitle="Trazabilidad reciente del sistema." rows={filteredAuditEvents} empty="No hay eventos auditables para este filtro." isLoading={isLoading} loadingLabel="Cargando audit..." columns={[
          { label: 'Fecha', render: (row) => stamp(row.created_at) },
          { label: 'Severidad', render: (row) => <Badge label={row.severity} tone={toneFor(row.severity)} /> },
          { label: 'Evento', render: (row) => row.event_type },
          { label: 'Entidad', render: (row) => `${row.entity_type}${row.entity_id ? ` · ${row.entity_id}` : ''}` },
          { label: 'Actor', render: (row) => row.actor_user_display || 'Sistema' },
          { label: 'Resumen', render: (row) => row.summary },
        ]} />
      ) : null}

      {effectiveRole !== 'RevisorFiscalExterno' ? (
        <TableBlock title="Resoluciones manuales" subtitle="Backlog manual y estado de cierre." rows={filteredManualResolutions} empty="No hay resoluciones manuales para este filtro." isLoading={isLoading} loadingLabel="Cargando audit..." columns={[
          { label: 'Estado', render: (row) => <Badge label={row.status} tone={toneFor(row.status)} /> },
          { label: 'Categoría', render: (row) => row.category },
          { label: 'Scope', render: (row) => `${row.scope_type} · ${row.scope_reference}` },
          { label: 'Resumen', render: (row) => row.summary },
          { label: 'Solicitado por', render: (row) => row.requested_by_display || 'Sistema' },
          { label: 'Resuelto por', render: (row) => row.resolved_by_display || 'Pendiente' },
          { label: 'Acción', render: (row) => canEditAudit ? <button type="button" className="button-ghost inline-action" onClick={() => startEditManualResolution(row)}>Editar</button> : 'Solo lectura' },
        ]} />
      ) : null}
    </>
  )
}
