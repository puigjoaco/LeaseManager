import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock } from '../shared'
import { toneFor } from '../shared-utils'

type ExpedienteDocumental = {
  id: number
  entidad_tipo: string
  entidad_id: string
  estado: string
  owner_operativo: string
}

type PoliticaFirma = {
  id: number
  tipo_documental: string
  requiere_firma_arrendador: boolean
  requiere_firma_arrendatario: boolean
  requiere_codeudor: boolean
  requiere_notaria: boolean
  modo_firma_permitido: string
  estado: string
}

type DocumentoEmitidoItem = {
  id: number
  expediente: number
  tipo_documental: string
  version_plantilla: string
  origen: string
  estado: string
  storage_ref: string
}

type ExpedienteDraft = {
  entidad_tipo: string
  entidad_id: string
  estado: string
  owner_operativo: string
}

type PoliticaFirmaDraft = {
  tipo_documental: string
  requiere_firma_arrendador: boolean
  requiere_firma_arrendatario: boolean
  requiere_codeudor: boolean
  requiere_notaria: boolean
  modo_firma_permitido: string
  estado: string
}

type DocumentoDraft = {
  expediente: string
  tipo_documental: string
  version_plantilla: string
  checksum: string
  fecha_carga: string
  origen: string
  estado: string
  storage_ref: string
  firma_arrendador_registrada: boolean
  firma_arrendatario_registrada: boolean
  firma_codeudor_registrada: boolean
  recepcion_notarial_registrada: boolean
  comprobante_notarial: string
}

type DocumentoFormalizarDraft = {
  documentoId: string
  firma_arrendador_registrada: boolean
  firma_arrendatario_registrada: boolean
  firma_codeudor_registrada: boolean
  recepcion_notarial_registrada: boolean
  comprobante_notarial: string
}

export function DocumentosWorkspace({
  canEditDocumentos,
  editingExpedienteId,
  expedienteDraft,
  setExpedienteDraft,
  handleCreateExpediente,
  cancelEditExpediente,
  politicaFirmaDraft,
  setPoliticaFirmaDraft,
  handleCreatePoliticaFirma,
  documentoDraft,
  setDocumentoDraft,
  handleCreateDocumento,
  documentoFormalizarDraft,
  setDocumentoFormalizarDraft,
  handleFormalizeDocumento,
  expedientes,
  documentosEmitidos,
  filteredExpedientes,
  filteredPoliticasFirma,
  filteredDocumentosEmitidos,
  isSubmitting,
  isLoading,
  startEditExpediente,
  goToDocumentoContext,
}: {
  canEditDocumentos: boolean
  editingExpedienteId: number | null
  expedienteDraft: ExpedienteDraft
  setExpedienteDraft: Dispatch<SetStateAction<ExpedienteDraft>>
  handleCreateExpediente: (event: FormEvent<HTMLFormElement>) => Promise<void>
  cancelEditExpediente: () => void
  politicaFirmaDraft: PoliticaFirmaDraft
  setPoliticaFirmaDraft: Dispatch<SetStateAction<PoliticaFirmaDraft>>
  handleCreatePoliticaFirma: (event: FormEvent<HTMLFormElement>) => Promise<void>
  documentoDraft: DocumentoDraft
  setDocumentoDraft: Dispatch<SetStateAction<DocumentoDraft>>
  handleCreateDocumento: (event: FormEvent<HTMLFormElement>) => Promise<void>
  documentoFormalizarDraft: DocumentoFormalizarDraft
  setDocumentoFormalizarDraft: Dispatch<SetStateAction<DocumentoFormalizarDraft>>
  handleFormalizeDocumento: (event: FormEvent<HTMLFormElement>) => Promise<void>
  expedientes: ExpedienteDocumental[]
  documentosEmitidos: DocumentoEmitidoItem[]
  filteredExpedientes: ExpedienteDocumental[]
  filteredPoliticasFirma: PoliticaFirma[]
  filteredDocumentosEmitidos: DocumentoEmitidoItem[]
  isSubmitting: boolean
  isLoading: boolean
  startEditExpediente: (row: ExpedienteDocumental) => void
  goToDocumentoContext: (documentoId: number) => void
}) {
  const expedienteById = new Map(expedientes.map((item) => [item.id, item]))

  return (
    <>
      {!canEditDocumentos ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Documentos.</div> : null}
      {canEditDocumentos ? (
        <section className="form-grid">
          <section className="panel">
            <div className="section-heading"><div><h2>{editingExpedienteId ? 'Editar expediente' : 'Expediente documental'}</h2><p>Agrupa documentos por entidad operativa.</p></div></div>
            <form className="entity-form" onSubmit={handleCreateExpediente}>
              <select value={expedienteDraft.entidad_tipo} onChange={(event) => setExpedienteDraft((current) => ({ ...current, entidad_tipo: event.target.value }))}>
                <option value="contrato">Contrato</option>
                <option value="arrendatario">Arrendatario</option>
                <option value="manual">Manual</option>
              </select>
              <input placeholder="Entidad ID" value={expedienteDraft.entidad_id} onChange={(event) => setExpedienteDraft((current) => ({ ...current, entidad_id: event.target.value }))} />
              <select value={expedienteDraft.estado} onChange={(event) => setExpedienteDraft((current) => ({ ...current, estado: event.target.value }))}>
                <option value="abierto">Abierto</option>
                <option value="cerrado">Cerrado</option>
                <option value="archivado">Archivado</option>
              </select>
              <input placeholder="Owner operativo" value={expedienteDraft.owner_operativo} onChange={(event) => setExpedienteDraft((current) => ({ ...current, owner_operativo: event.target.value }))} />
              <div className="inline-actions">
                <button type="submit" className="button-primary" disabled={isSubmitting || !expedienteDraft.entidad_id || !expedienteDraft.owner_operativo}>Guardar expediente</button>
                {editingExpedienteId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditExpediente}>Cancelar</button> : null}
              </div>
            </form>
          </section>

          <section className="panel">
            <div className="section-heading"><div><h2>Política de firma</h2><p>Reglas activas por tipo documental.</p></div></div>
            <form className="entity-form" onSubmit={handleCreatePoliticaFirma}>
              <select value={politicaFirmaDraft.tipo_documental} onChange={(event) => setPoliticaFirmaDraft((current) => ({ ...current, tipo_documental: event.target.value }))}>
                <option value="contrato_principal">Contrato principal</option>
                <option value="anexo">Anexo</option>
                <option value="carta_aviso">Carta de aviso</option>
                <option value="liquidacion_garantia">Liquidación de garantía</option>
                <option value="respaldo_tributario">Respaldo tributario</option>
                <option value="comprobante_notarial">Comprobante notarial</option>
                <option value="evidencia_resolucion_manual">Evidencia de resolución manual</option>
              </select>
              <select value={politicaFirmaDraft.modo_firma_permitido} onChange={(event) => setPoliticaFirmaDraft((current) => ({ ...current, modo_firma_permitido: event.target.value }))}>
                <option value="firma_simple">Firma simple</option>
                <option value="firma_avanzada">Firma avanzada</option>
                <option value="mixta">Mixta</option>
                <option value="manual">Manual</option>
              </select>
              <select value={politicaFirmaDraft.estado} onChange={(event) => setPoliticaFirmaDraft((current) => ({ ...current, estado: event.target.value }))}>
                <option value="activa">Activa</option>
                <option value="inactiva">Inactiva</option>
              </select>
              <label className="checkbox-row"><input type="checkbox" checked={politicaFirmaDraft.requiere_firma_arrendador} onChange={(event) => setPoliticaFirmaDraft((current) => ({ ...current, requiere_firma_arrendador: event.target.checked }))} />Firma arrendador</label>
              <label className="checkbox-row"><input type="checkbox" checked={politicaFirmaDraft.requiere_firma_arrendatario} onChange={(event) => setPoliticaFirmaDraft((current) => ({ ...current, requiere_firma_arrendatario: event.target.checked }))} />Firma arrendatario</label>
              <label className="checkbox-row"><input type="checkbox" checked={politicaFirmaDraft.requiere_codeudor} onChange={(event) => setPoliticaFirmaDraft((current) => ({ ...current, requiere_codeudor: event.target.checked }))} />Firma codeudor</label>
              <label className="checkbox-row"><input type="checkbox" checked={politicaFirmaDraft.requiere_notaria} onChange={(event) => setPoliticaFirmaDraft((current) => ({ ...current, requiere_notaria: event.target.checked }))} />Requiere notaría</label>
              <button type="submit" className="button-primary" disabled={isSubmitting}>Guardar política</button>
            </form>
          </section>

          <section className="panel">
            <div className="section-heading"><div><h2>Documento emitido</h2><p>Registro de documento y estado documental.</p></div></div>
            <form className="entity-form" onSubmit={handleCreateDocumento}>
              <select value={documentoDraft.expediente} onChange={(event) => setDocumentoDraft((current) => ({ ...current, expediente: event.target.value }))}>
                <option value="">Selecciona expediente</option>
                {expedientes.map((item) => (
                  <option key={item.id} value={item.id}>{item.entidad_tipo} · {item.entidad_id}</option>
                ))}
              </select>
              <select value={documentoDraft.tipo_documental} onChange={(event) => setDocumentoDraft((current) => ({ ...current, tipo_documental: event.target.value }))}>
                <option value="contrato_principal">Contrato principal</option>
                <option value="anexo">Anexo</option>
                <option value="carta_aviso">Carta de aviso</option>
                <option value="liquidacion_garantia">Liquidación de garantía</option>
                <option value="respaldo_tributario">Respaldo tributario</option>
                <option value="comprobante_notarial">Comprobante notarial</option>
                <option value="evidencia_resolucion_manual">Evidencia de resolución manual</option>
              </select>
              <input placeholder="Versión plantilla" value={documentoDraft.version_plantilla} onChange={(event) => setDocumentoDraft((current) => ({ ...current, version_plantilla: event.target.value }))} />
              <input placeholder="Checksum" value={documentoDraft.checksum} onChange={(event) => setDocumentoDraft((current) => ({ ...current, checksum: event.target.value }))} />
              <input type="datetime-local" value={documentoDraft.fecha_carga} onChange={(event) => setDocumentoDraft((current) => ({ ...current, fecha_carga: event.target.value }))} />
              <select value={documentoDraft.origen} onChange={(event) => setDocumentoDraft((current) => ({ ...current, origen: event.target.value }))}>
                <option value="generado_sistema">Generado por sistema</option>
                <option value="carga_externa_controlada">Carga externa controlada</option>
              </select>
              <select value={documentoDraft.estado} onChange={(event) => setDocumentoDraft((current) => ({ ...current, estado: event.target.value }))}>
                <option value="borrador">Borrador</option>
                <option value="emitido">Emitido</option>
                <option value="archivado">Archivado</option>
                <option value="cancelado">Cancelado</option>
              </select>
              <input placeholder="Storage ref" value={documentoDraft.storage_ref} onChange={(event) => setDocumentoDraft((current) => ({ ...current, storage_ref: event.target.value }))} />
              <button type="submit" className="button-primary" disabled={isSubmitting || !documentoDraft.expediente || !documentoDraft.checksum || !documentoDraft.storage_ref}>Guardar documento</button>
            </form>
          </section>

          <section className="panel">
            <div className="section-heading"><div><h2>Formalizar documento</h2><p>Registro de firmas y comprobante notarial cuando aplique.</p></div></div>
            <form className="entity-form" onSubmit={handleFormalizeDocumento}>
              <select value={documentoFormalizarDraft.documentoId} onChange={(event) => setDocumentoFormalizarDraft((current) => ({ ...current, documentoId: event.target.value }))}>
                <option value="">Selecciona documento</option>
                {documentosEmitidos.map((item) => (
                  <option key={item.id} value={item.id}>{item.tipo_documental} · {item.storage_ref}</option>
                ))}
              </select>
              <select value={documentoFormalizarDraft.comprobante_notarial} onChange={(event) => setDocumentoFormalizarDraft((current) => ({ ...current, comprobante_notarial: event.target.value }))}>
                <option value="">Sin comprobante</option>
                {documentosEmitidos.filter((item) => item.tipo_documental === 'comprobante_notarial').map((item) => (
                  <option key={item.id} value={item.id}>{item.storage_ref}</option>
                ))}
              </select>
              <label className="checkbox-row"><input type="checkbox" checked={documentoFormalizarDraft.firma_arrendador_registrada} onChange={(event) => setDocumentoFormalizarDraft((current) => ({ ...current, firma_arrendador_registrada: event.target.checked }))} />Firma arrendador</label>
              <label className="checkbox-row"><input type="checkbox" checked={documentoFormalizarDraft.firma_arrendatario_registrada} onChange={(event) => setDocumentoFormalizarDraft((current) => ({ ...current, firma_arrendatario_registrada: event.target.checked }))} />Firma arrendatario</label>
              <label className="checkbox-row"><input type="checkbox" checked={documentoFormalizarDraft.firma_codeudor_registrada} onChange={(event) => setDocumentoFormalizarDraft((current) => ({ ...current, firma_codeudor_registrada: event.target.checked }))} />Firma codeudor</label>
              <label className="checkbox-row"><input type="checkbox" checked={documentoFormalizarDraft.recepcion_notarial_registrada} onChange={(event) => setDocumentoFormalizarDraft((current) => ({ ...current, recepcion_notarial_registrada: event.target.checked }))} />Recepción notarial</label>
              <button type="submit" className="button-primary" disabled={isSubmitting || !documentoFormalizarDraft.documentoId}>Formalizar documento</button>
            </form>
          </section>
        </section>
      ) : null}

      <TableBlock title="Expedientes" subtitle="Agrupación documental por entidad operativa." rows={filteredExpedientes} empty="No hay expedientes para este filtro." isLoading={isLoading} loadingLabel="Cargando documentos..." columns={[
        { label: 'Entidad', render: (row) => `${row.entidad_tipo} · ${row.entidad_id}` },
        { label: 'Owner operativo', render: (row) => row.owner_operativo },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Acción', render: (row) => canEditDocumentos ? <button type="button" className="button-ghost inline-action" onClick={() => startEditExpediente(row)}>Editar</button> : 'Solo lectura' },
      ]} />

      <TableBlock title="Políticas de firma" subtitle="Reglas activas por tipo documental." rows={filteredPoliticasFirma} empty="No hay políticas para este filtro." isLoading={isLoading} loadingLabel="Cargando documentos..." columns={[
        { label: 'Tipo documental', render: (row) => row.tipo_documental },
        { label: 'Modo firma', render: (row) => row.modo_firma_permitido },
        { label: 'Arrendador', render: (row) => row.requiere_firma_arrendador ? 'Sí' : 'No' },
        { label: 'Arrendatario', render: (row) => row.requiere_firma_arrendatario ? 'Sí' : 'No' },
        { label: 'Notaría', render: (row) => row.requiere_notaria ? 'Sí' : 'No' },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />

      <TableBlock title="Documentos emitidos" subtitle="Estado documental y storage asociado." rows={filteredDocumentosEmitidos} empty="No hay documentos emitidos para este filtro." isLoading={isLoading} loadingLabel="Cargando documentos..." columns={[
        { label: 'Expediente', render: (row) => `${expedienteById.get(row.expediente)?.entidad_tipo || 'expediente'} · ${expedienteById.get(row.expediente)?.entidad_id || row.expediente}` },
        { label: 'Tipo', render: (row) => row.tipo_documental },
        { label: 'Origen', render: (row) => row.origen },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Storage', render: (row) => row.storage_ref },
        { label: 'Acción', render: (row) => canEditDocumentos ? <div className="inline-actions"><button type="button" className="button-ghost inline-action" onClick={() => setDocumentoFormalizarDraft((current) => ({ ...current, documentoId: String(row.id) }))}>Formalizar</button><button type="button" className="button-ghost inline-action" onClick={() => goToDocumentoContext(row.id)}>Canales</button></div> : 'Solo lectura' },
      ]} />
    </>
  )
}
