import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock } from '../shared'
import { stamp, toneFor } from '../shared-utils'

type EmpresaItem = { id: number; razon_social: string }
type SocioItem = { id: number; nombre: string }

type PoliticaRetencionItem = {
  id: number
  categoria_dato: string
  evento_inicio: string
  plazo_minimo_anos: number
  permite_borrado_logico: boolean
  permite_purga_fisica: boolean
  requiere_hold: boolean
  estado: string
}

type ExportacionSensibleItem = {
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

type ExportacionPreview = {
  id: number
  export_kind: string
  payload_hash: string
  payload: unknown
} | null

type PoliticaRetencionDraft = {
  categoria_dato: string
  evento_inicio: string
  plazo_minimo_anos: string
  permite_borrado_logico: boolean
  permite_purga_fisica: boolean
  requiere_hold: boolean
  estado: string
}

type ExportacionPrepareDraft = {
  categoria_dato: string
  export_kind: string
  motivo: string
  hold_activo: boolean
  anio: string
  mes: string
  anio_tributario: string
  empresa_id: string
  socio_id: string
  periodo: string
}

export function ComplianceWorkspace({
  canEditCompliance,
  politicaRetencionDraft,
  setPoliticaRetencionDraft,
  handleCreatePoliticaRetencion,
  exportacionPrepareDraft,
  setExportacionPrepareDraft,
  handlePrepareExportacion,
  filteredCompliancePolicies,
  filteredComplianceExports,
  complianceExportPreview,
  handleViewExportacionContenido,
  handleRevokeExportacion,
  empresas,
  socios,
  isSubmitting,
}: {
  canEditCompliance: boolean
  politicaRetencionDraft: PoliticaRetencionDraft
  setPoliticaRetencionDraft: Dispatch<SetStateAction<PoliticaRetencionDraft>>
  handleCreatePoliticaRetencion: (event: FormEvent<HTMLFormElement>) => Promise<void>
  exportacionPrepareDraft: ExportacionPrepareDraft
  setExportacionPrepareDraft: Dispatch<SetStateAction<ExportacionPrepareDraft>>
  handlePrepareExportacion: (event: FormEvent<HTMLFormElement>) => Promise<void>
  filteredCompliancePolicies: PoliticaRetencionItem[]
  filteredComplianceExports: ExportacionSensibleItem[]
  complianceExportPreview: ExportacionPreview
  handleViewExportacionContenido: (exportId: number) => Promise<void>
  handleRevokeExportacion: (exportId: number) => Promise<void>
  empresas: EmpresaItem[]
  socios: SocioItem[]
  isSubmitting: boolean
}) {
  const requiresCompany = ['financiero_mensual', 'libros_periodo', 'tributario_anual'].includes(exportacionPrepareDraft.export_kind)
  const requiresPartner = exportacionPrepareDraft.export_kind === 'socio_resumen'
  const requiresMonth = exportacionPrepareDraft.export_kind === 'financiero_mensual'
  const requiresAnnual = exportacionPrepareDraft.export_kind === 'tributario_anual'
  const requiresPeriod = exportacionPrepareDraft.export_kind === 'libros_periodo'

  return (
    <>
      {!canEditCompliance ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Compliance.</div> : null}

      {canEditCompliance ? (
        <section className="form-grid">
          <section className="panel">
            <div className="section-heading"><div><h2>Política de retención</h2><p>Baseline de conservación por categoría sensible.</p></div></div>
            <form className="entity-form" onSubmit={handleCreatePoliticaRetencion}>
              <select value={politicaRetencionDraft.categoria_dato} onChange={(event) => setPoliticaRetencionDraft((current) => ({ ...current, categoria_dato: event.target.value }))}>
                <option value="operativo">Operativo</option>
                <option value="financiero">Financiero</option>
                <option value="tributario">Tributario</option>
                <option value="documental_sensible">Documental sensible</option>
                <option value="secreto">Secreto</option>
              </select>
              <input placeholder="Evento inicio" value={politicaRetencionDraft.evento_inicio} onChange={(event) => setPoliticaRetencionDraft((current) => ({ ...current, evento_inicio: event.target.value }))} />
              <input placeholder="Plazo mínimo (años)" value={politicaRetencionDraft.plazo_minimo_anos} onChange={(event) => setPoliticaRetencionDraft((current) => ({ ...current, plazo_minimo_anos: event.target.value }))} />
              <select value={politicaRetencionDraft.estado} onChange={(event) => setPoliticaRetencionDraft((current) => ({ ...current, estado: event.target.value }))}>
                <option value="activa">Activa</option>
                <option value="inactiva">Inactiva</option>
              </select>
              <label className="checkbox-row"><input type="checkbox" checked={politicaRetencionDraft.permite_borrado_logico} onChange={(event) => setPoliticaRetencionDraft((current) => ({ ...current, permite_borrado_logico: event.target.checked }))} />Permite borrado lógico</label>
              <label className="checkbox-row"><input type="checkbox" checked={politicaRetencionDraft.permite_purga_fisica} onChange={(event) => setPoliticaRetencionDraft((current) => ({ ...current, permite_purga_fisica: event.target.checked }))} />Permite purga física</label>
              <label className="checkbox-row"><input type="checkbox" checked={politicaRetencionDraft.requiere_hold} onChange={(event) => setPoliticaRetencionDraft((current) => ({ ...current, requiere_hold: event.target.checked }))} />Requiere hold</label>
              <button type="submit" className="button-primary" disabled={isSubmitting || !politicaRetencionDraft.evento_inicio || !politicaRetencionDraft.plazo_minimo_anos}>Guardar política</button>
            </form>
          </section>

          <section className="panel">
            <div className="section-heading"><div><h2>Preparar exportación</h2><p>Genera un payload cifrado desde reporting o dashboard.</p></div></div>
            <form className="entity-form" onSubmit={handlePrepareExportacion}>
              <select value={exportacionPrepareDraft.categoria_dato} onChange={(event) => setExportacionPrepareDraft((current) => ({ ...current, categoria_dato: event.target.value }))}>
                <option value="operativo">Operativo</option>
                <option value="financiero">Financiero</option>
                <option value="tributario">Tributario</option>
                <option value="documental_sensible">Documental sensible</option>
                <option value="secreto">Secreto</option>
              </select>
              <select value={exportacionPrepareDraft.export_kind} onChange={(event) => setExportacionPrepareDraft((current) => ({ ...current, export_kind: event.target.value }))}>
                <option value="dashboard_operativo">Dashboard operativo</option>
                <option value="financiero_mensual">Financiero mensual</option>
                <option value="tributario_anual">Tributario anual</option>
                <option value="socio_resumen">Resumen socio</option>
                <option value="libros_periodo">Libros por período</option>
              </select>
              <input placeholder="Motivo" value={exportacionPrepareDraft.motivo} onChange={(event) => setExportacionPrepareDraft((current) => ({ ...current, motivo: event.target.value }))} />
              {requiresCompany ? (
                <select value={exportacionPrepareDraft.empresa_id} onChange={(event) => setExportacionPrepareDraft((current) => ({ ...current, empresa_id: event.target.value }))}>
                  <option value="">Selecciona empresa</option>
                  {empresas.map((item) => <option key={item.id} value={item.id}>{item.razon_social}</option>)}
                </select>
              ) : null}
              {requiresPartner ? (
                <select value={exportacionPrepareDraft.socio_id} onChange={(event) => setExportacionPrepareDraft((current) => ({ ...current, socio_id: event.target.value }))}>
                  <option value="">Selecciona socio</option>
                  {socios.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
                </select>
              ) : null}
              {requiresMonth ? (
                <>
                  <input placeholder="Año" value={exportacionPrepareDraft.anio} onChange={(event) => setExportacionPrepareDraft((current) => ({ ...current, anio: event.target.value }))} />
                  <input placeholder="Mes" value={exportacionPrepareDraft.mes} onChange={(event) => setExportacionPrepareDraft((current) => ({ ...current, mes: event.target.value }))} />
                </>
              ) : null}
              {requiresAnnual ? (
                <input placeholder="Año tributario" value={exportacionPrepareDraft.anio_tributario} onChange={(event) => setExportacionPrepareDraft((current) => ({ ...current, anio_tributario: event.target.value }))} />
              ) : null}
              {requiresPeriod ? (
                <input placeholder="Período YYYY-MM" value={exportacionPrepareDraft.periodo} onChange={(event) => setExportacionPrepareDraft((current) => ({ ...current, periodo: event.target.value }))} />
              ) : null}
              <label className="checkbox-row"><input type="checkbox" checked={exportacionPrepareDraft.hold_activo} onChange={(event) => setExportacionPrepareDraft((current) => ({ ...current, hold_activo: event.target.checked }))} />Hold activo</label>
              <button
                type="submit"
                className="button-primary"
                disabled={
                  isSubmitting
                  || !exportacionPrepareDraft.motivo
                  || (requiresCompany && !exportacionPrepareDraft.empresa_id)
                  || (requiresPartner && !exportacionPrepareDraft.socio_id)
                  || (requiresMonth && (!exportacionPrepareDraft.anio || !exportacionPrepareDraft.mes))
                  || (requiresAnnual && !exportacionPrepareDraft.anio_tributario)
                  || (requiresPeriod && (!exportacionPrepareDraft.empresa_id || !exportacionPrepareDraft.periodo))
                }
              >
                Preparar exportación
              </button>
            </form>
          </section>

          <section className="panel">
            <div className="section-heading"><div><h2>Contenido exportado</h2><p>Payload descifrado de la exportación seleccionada.</p></div></div>
            {complianceExportPreview ? (
              <>
                <div className="list-stack">
                  <div className="list-row"><span>Export</span><strong>{complianceExportPreview.export_kind}</strong></div>
                  <div className="list-row"><span>Hash</span><strong>{complianceExportPreview.payload_hash}</strong></div>
                </div>
                <pre className="json-block">{JSON.stringify(complianceExportPreview.payload, null, 2)}</pre>
              </>
            ) : (
              <div className="empty-state">Selecciona una exportación para ver su contenido.</div>
            )}
          </section>
        </section>
      ) : null}

      <TableBlock
        title="Políticas de retención"
        subtitle="Reglas activas por categoría sensible."
        rows={filteredCompliancePolicies}
        empty="No hay políticas de retención para este filtro."
        columns={[
          { label: 'Categoría', render: (row) => row.categoria_dato },
          { label: 'Evento inicio', render: (row) => row.evento_inicio },
          { label: 'Plazo', render: (row) => `${row.plazo_minimo_anos} años` },
          { label: 'Hold', render: (row) => row.requiere_hold ? 'Sí' : 'No' },
          { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        ]}
      />

      <TableBlock
        title="Exportaciones sensibles"
        subtitle="Payloads cifrados, expiración y acciones manuales."
        rows={filteredComplianceExports}
        empty="No hay exportaciones sensibles para este filtro."
        columns={[
          { label: 'Categoría', render: (row) => row.categoria_dato },
          { label: 'Tipo', render: (row) => row.export_kind },
          { label: 'Ref', render: (row) => row.encrypted_ref || row.payload_hash.slice(0, 12) },
          { label: 'Expira', render: (row) => stamp(row.expires_at) },
          { label: 'Hold', render: (row) => row.hold_activo ? 'Sí' : 'No' },
          { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
          {
            label: 'Acción',
            render: (row) => (
              <div className="inline-actions">
                <button type="button" className="button-ghost inline-action" onClick={() => void handleViewExportacionContenido(row.id)}>Ver</button>
                <button type="button" className="button-ghost inline-action" onClick={() => void handleRevokeExportacion(row.id)} disabled={row.estado !== 'preparada'}>Revocar</button>
              </div>
            ),
          },
        ]}
      />
    </>
  )
}
