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
  requiere_nacionalidad_arrendatario: boolean
  requiere_estado_civil_arrendatario: boolean
  requiere_profesion_arrendatario: boolean
  requiere_notaria: boolean
  modo_firma_permitido: string
  estado: string
}

type PlantillaDocumental = {
  id: number
  tipo_documental: string
  version_plantilla: string
  plantilla_ref: string
  checksum_plantilla: string
  descripcion: string
  estado: string
}

type DocumentoEmitidoItem = {
  id: number
  expediente: number
  tipo_documental: string
  version_plantilla: string
  checksum: string
  fecha_carga: string
  usuario: number | null
  origen: string
  estado: string
  storage_ref: string
  firma_arrendador_registrada: boolean
  firma_arrendatario_registrada: boolean
  firma_codeudor_registrada: boolean
  recepcion_notarial_registrada: boolean
  evidencia_formalizacion_ref: string
  comprobante_notarial: number | null
  documento_origen: number | null
  correccion_ref: string
}

type ExpedienteItem = {
  id: string
  source_model: 'documento_emitido' | 'archivo_expediente'
  source_id: number
  expediente: number
  clase: string
  categoria: string
  subcategoria: string
  titulo_operativo: string
  descripcion_objetiva: string
  extension: string
  mime_type: string
  checksum_sha256: string
  size_bytes: number | null
  storage_ref: string
  origen_auditoria: string
  estado: string
  duplicate_of: string | null
  fecha: string | null
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
  requiere_nacionalidad_arrendatario: boolean
  requiere_estado_civil_arrendatario: boolean
  requiere_profesion_arrendatario: boolean
  requiere_notaria: boolean
  modo_firma_permitido: string
  estado: string
}

type PlantillaDocumentalDraft = {
  tipo_documental: string
  version_plantilla: string
  plantilla_ref: string
  checksum_plantilla: string
  descripcion: string
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
  documento_origen: string
  correccion_ref: string
}

type DocumentoFormalizarDraft = {
  documentoId: string
  firma_arrendador_registrada: boolean
  firma_arrendatario_registrada: boolean
  firma_codeudor_registrada: boolean
  recepcion_notarial_registrada: boolean
  evidencia_formalizacion_ref: string
  comprobante_notarial: string
}

type DocumentoGeneratedPdfDraft = {
  expediente: string
  tipo_documental: string
  version_plantilla: string
  titulo: string
  lineas_text: string
}

type DocumentoGeneratedPdfPreview = {
  pdf_sha256: string
  pdf_size_bytes: number
  storage_ref_preview: string
  preview_ref: string
}

function isPdfStorageRef(value: string) {
  return value.trim().toLowerCase().split('?', 1)[0].split('#', 1)[0].endsWith('.pdf')
}

function isDocumentChecksum(value: string) {
  return /^(sha256:)?[0-9a-f]{64}$/i.test(value.trim())
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
  plantillaDocumentalDraft,
  setPlantillaDocumentalDraft,
  handleCreatePlantillaDocumental,
  documentoDraft,
  setDocumentoDraft,
  handleCreateDocumento,
  documentoFormalizarDraft,
  setDocumentoFormalizarDraft,
  handleFormalizeDocumento,
  generatedPdfDraft,
  setGeneratedPdfDraft,
  generatedPdfPreview,
  clearGeneratedPdfPreview,
  handlePreviewGeneratedPdf,
  handleGenerateGeneratedPdf,
  expedientes,
  plantillasDocumentales,
  documentosEmitidos,
  expedienteItems,
  filteredExpedientes,
  filteredPoliticasFirma,
  filteredPlantillasDocumentales,
  filteredExpedienteItems,
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
  plantillaDocumentalDraft: PlantillaDocumentalDraft
  setPlantillaDocumentalDraft: Dispatch<SetStateAction<PlantillaDocumentalDraft>>
  handleCreatePlantillaDocumental: (event: FormEvent<HTMLFormElement>) => Promise<void>
  documentoDraft: DocumentoDraft
  setDocumentoDraft: Dispatch<SetStateAction<DocumentoDraft>>
  handleCreateDocumento: (event: FormEvent<HTMLFormElement>) => Promise<void>
  documentoFormalizarDraft: DocumentoFormalizarDraft
  setDocumentoFormalizarDraft: Dispatch<SetStateAction<DocumentoFormalizarDraft>>
  handleFormalizeDocumento: (event: FormEvent<HTMLFormElement>) => Promise<void>
  generatedPdfDraft: DocumentoGeneratedPdfDraft
  setGeneratedPdfDraft: Dispatch<SetStateAction<DocumentoGeneratedPdfDraft>>
  generatedPdfPreview: DocumentoGeneratedPdfPreview | null
  clearGeneratedPdfPreview: () => void
  handlePreviewGeneratedPdf: (event: FormEvent<HTMLFormElement>) => Promise<void>
  handleGenerateGeneratedPdf: () => Promise<void>
  expedientes: ExpedienteDocumental[]
  plantillasDocumentales: PlantillaDocumental[]
  documentosEmitidos: DocumentoEmitidoItem[]
  expedienteItems: ExpedienteItem[]
  filteredExpedientes: ExpedienteDocumental[]
  filteredPoliticasFirma: PoliticaFirma[]
  filteredPlantillasDocumentales: PlantillaDocumental[]
  filteredExpedienteItems: ExpedienteItem[]
  isSubmitting: boolean
  isLoading: boolean
  startEditExpediente: (row: ExpedienteDocumental) => void
  goToDocumentoContext: (documentoId: number) => void
}) {
  const expedienteById = new Map(expedientes.map((item) => [item.id, item]))
  const expedienteItemsTotal = expedienteItems.length
  const activeTemplateOptions = plantillasDocumentales.filter((item) =>
    item.estado === 'activa' && item.tipo_documental === documentoDraft.tipo_documental,
  )
  const generatedTemplateOptions = plantillasDocumentales.filter((item) =>
    item.estado === 'activa' && item.tipo_documental === generatedPdfDraft.tipo_documental,
  )
  const selectedGeneratedTemplate = generatedTemplateOptions.some(
    (item) => item.version_plantilla === generatedPdfDraft.version_plantilla,
  )
  const notaryReceiptOptions = documentosEmitidos.filter((item) =>
    item.tipo_documental === 'comprobante_notarial'
    && ['emitido', 'formalizado', 'archivado'].includes(item.estado)
    && isPdfStorageRef(item.storage_ref),
  )
  const correctiveOriginOptions = documentosEmitidos.filter((item) =>
    item.estado === 'formalizado'
    && item.expediente === Number(documentoDraft.expediente)
    && item.tipo_documental === documentoDraft.tipo_documental,
  )
  const correctionRequiresRef = Boolean(documentoDraft.documento_origen) && !documentoDraft.correccion_ref.trim()
  const generatedPdfReady = Boolean(
    generatedPdfDraft.expediente
    && selectedGeneratedTemplate
    && generatedPdfDraft.titulo.trim()
    && generatedPdfDraft.lineas_text.trim(),
  )

  function updateGeneratedPdfDraft(patch: Partial<DocumentoGeneratedPdfDraft>) {
    clearGeneratedPdfPreview()
    setGeneratedPdfDraft((current) => ({ ...current, ...patch }))
  }

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
              <label className="checkbox-row"><input type="checkbox" checked={politicaFirmaDraft.requiere_nacionalidad_arrendatario} onChange={(event) => setPoliticaFirmaDraft((current) => ({ ...current, requiere_nacionalidad_arrendatario: event.target.checked }))} />Nacionalidad arrendatario</label>
              <label className="checkbox-row"><input type="checkbox" checked={politicaFirmaDraft.requiere_estado_civil_arrendatario} onChange={(event) => setPoliticaFirmaDraft((current) => ({ ...current, requiere_estado_civil_arrendatario: event.target.checked }))} />Estado civil arrendatario</label>
              <label className="checkbox-row"><input type="checkbox" checked={politicaFirmaDraft.requiere_profesion_arrendatario} onChange={(event) => setPoliticaFirmaDraft((current) => ({ ...current, requiere_profesion_arrendatario: event.target.checked }))} />Profesión arrendatario</label>
              <label className="checkbox-row"><input type="checkbox" checked={politicaFirmaDraft.requiere_notaria} onChange={(event) => setPoliticaFirmaDraft((current) => ({ ...current, requiere_notaria: event.target.checked }))} />Requiere notaría</label>
              <button type="submit" className="button-primary" disabled={isSubmitting}>Guardar política</button>
            </form>
          </section>

          <section className="panel">
            <div className="section-heading"><div><h2>Plantilla documental</h2><p>Versiones activas para emitir PDF.</p></div></div>
            <form className="entity-form" onSubmit={handleCreatePlantillaDocumental}>
              <select value={plantillaDocumentalDraft.tipo_documental} onChange={(event) => setPlantillaDocumentalDraft((current) => ({ ...current, tipo_documental: event.target.value }))}>
                <option value="contrato_principal">Contrato principal</option>
                <option value="anexo">Anexo</option>
                <option value="carta_aviso">Carta de aviso</option>
                <option value="liquidacion_garantia">Liquidación de garantía</option>
                <option value="respaldo_tributario">Respaldo tributario</option>
                <option value="comprobante_notarial">Comprobante notarial</option>
                <option value="evidencia_resolucion_manual">Evidencia de resolución manual</option>
              </select>
              <input placeholder="Versión plantilla" value={plantillaDocumentalDraft.version_plantilla} onChange={(event) => setPlantillaDocumentalDraft((current) => ({ ...current, version_plantilla: event.target.value }))} />
              <input placeholder="Plantilla ref" value={plantillaDocumentalDraft.plantilla_ref} onChange={(event) => setPlantillaDocumentalDraft((current) => ({ ...current, plantilla_ref: event.target.value }))} />
              <input placeholder="Checksum plantilla" value={plantillaDocumentalDraft.checksum_plantilla} onChange={(event) => setPlantillaDocumentalDraft((current) => ({ ...current, checksum_plantilla: event.target.value }))} />
              <input placeholder="Descripción" value={plantillaDocumentalDraft.descripcion} onChange={(event) => setPlantillaDocumentalDraft((current) => ({ ...current, descripcion: event.target.value }))} />
              <select value={plantillaDocumentalDraft.estado} onChange={(event) => setPlantillaDocumentalDraft((current) => ({ ...current, estado: event.target.value }))}>
                <option value="activa">Activa</option>
                <option value="inactiva">Inactiva</option>
              </select>
              <button type="submit" className="button-primary" disabled={isSubmitting || !plantillaDocumentalDraft.version_plantilla.trim() || !plantillaDocumentalDraft.plantilla_ref.trim() || !isDocumentChecksum(plantillaDocumentalDraft.checksum_plantilla)}>Guardar plantilla</button>
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
              <select value={documentoDraft.version_plantilla} onChange={(event) => setDocumentoDraft((current) => ({ ...current, version_plantilla: event.target.value }))}>
                {activeTemplateOptions.length === 0 ? <option value={documentoDraft.version_plantilla}>{documentoDraft.version_plantilla || 'Sin plantilla activa'}</option> : null}
                {activeTemplateOptions.map((item) => (
                  <option key={item.id} value={item.version_plantilla}>{item.version_plantilla}</option>
                ))}
              </select>
              <input placeholder="Checksum SHA-256" value={documentoDraft.checksum} onChange={(event) => setDocumentoDraft((current) => ({ ...current, checksum: event.target.value }))} />
              <input type="datetime-local" value={documentoDraft.fecha_carga} onChange={(event) => setDocumentoDraft((current) => ({ ...current, fecha_carga: event.target.value }))} />
              <select value={documentoDraft.origen} onChange={(event) => setDocumentoDraft((current) => ({ ...current, origen: event.target.value }))}>
                <option value="carga_externa_controlada">Carga externa controlada</option>
              </select>
              <select value={documentoDraft.estado} onChange={(event) => setDocumentoDraft((current) => ({ ...current, estado: event.target.value }))}>
                <option value="borrador">Borrador</option>
                <option value="emitido">Emitido</option>
                <option value="archivado">Archivado</option>
                <option value="cancelado">Cancelado</option>
              </select>
              <input placeholder="Storage ref PDF" value={documentoDraft.storage_ref} onChange={(event) => setDocumentoDraft((current) => ({ ...current, storage_ref: event.target.value }))} />
              <select value={documentoDraft.documento_origen} onChange={(event) => setDocumentoDraft((current) => ({ ...current, documento_origen: event.target.value }))}>
                <option value="">Sin documento origen</option>
                {correctiveOriginOptions.map((item) => (
                  <option key={item.id} value={item.id}>{item.version_plantilla} · {item.storage_ref}</option>
                ))}
              </select>
              <input placeholder="Ref corrección" value={documentoDraft.correccion_ref} onChange={(event) => setDocumentoDraft((current) => ({ ...current, correccion_ref: event.target.value }))} />
              <button type="submit" className="button-primary" disabled={isSubmitting || !documentoDraft.expediente || !isDocumentChecksum(documentoDraft.checksum) || !isPdfStorageRef(documentoDraft.storage_ref) || correctionRequiresRef}>Guardar documento</button>
            </form>
          </section>

          <section className="panel">
            <div className="section-heading"><div><h2>PDF generado</h2><p>Emisión local con preview auditada.</p></div></div>
            <form className="entity-form" onSubmit={handlePreviewGeneratedPdf}>
              <select value={generatedPdfDraft.expediente} onChange={(event) => updateGeneratedPdfDraft({ expediente: event.target.value })}>
                <option value="">Selecciona expediente</option>
                {expedientes.map((item) => (
                  <option key={item.id} value={item.id}>{item.entidad_tipo} · {item.entidad_id}</option>
                ))}
              </select>
              <select value={generatedPdfDraft.tipo_documental} onChange={(event) => updateGeneratedPdfDraft({ tipo_documental: event.target.value, version_plantilla: '' })}>
                <option value="contrato_principal">Contrato principal</option>
                <option value="anexo">Anexo</option>
                <option value="carta_aviso">Carta de aviso</option>
                <option value="liquidacion_garantia">Liquidación de garantía</option>
                <option value="respaldo_tributario">Respaldo tributario</option>
                <option value="comprobante_notarial">Comprobante notarial</option>
                <option value="evidencia_resolucion_manual">Evidencia de resolución manual</option>
              </select>
              <select value={generatedPdfDraft.version_plantilla} onChange={(event) => updateGeneratedPdfDraft({ version_plantilla: event.target.value })}>
                <option value="">Selecciona plantilla activa</option>
                {generatedTemplateOptions.length === 0 ? <option value="" disabled>Sin plantilla activa</option> : null}
                {generatedTemplateOptions.map((item) => (
                  <option key={item.id} value={item.version_plantilla}>{item.version_plantilla}</option>
                ))}
              </select>
              <input placeholder="Título PDF" value={generatedPdfDraft.titulo} onChange={(event) => updateGeneratedPdfDraft({ titulo: event.target.value })} />
              <textarea rows={4} placeholder="Líneas de contenido operativo" value={generatedPdfDraft.lineas_text} onChange={(event) => updateGeneratedPdfDraft({ lineas_text: event.target.value })} />
              {generatedPdfPreview ? (
                <div className="inline-actions">
                  <Badge label="preview auditada" tone="positive" />
                  <span>{generatedPdfPreview.pdf_sha256.slice(0, 12)} · {generatedPdfPreview.pdf_size_bytes} bytes</span>
                  <span>{generatedPdfPreview.storage_ref_preview}</span>
                </div>
              ) : null}
              <div className="inline-actions">
                <button type="submit" className="button-primary" disabled={isSubmitting || !generatedPdfReady}>Previsualizar PDF</button>
                <button type="button" className="button-ghost inline-action" onClick={() => void handleGenerateGeneratedPdf()} disabled={isSubmitting || !generatedPdfReady || !generatedPdfPreview}>Emitir PDF</button>
              </div>
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
                {notaryReceiptOptions.map((item) => (
                  <option key={item.id} value={item.id}>{item.storage_ref}</option>
                ))}
              </select>
              <label className="checkbox-row"><input type="checkbox" checked={documentoFormalizarDraft.firma_arrendador_registrada} onChange={(event) => setDocumentoFormalizarDraft((current) => ({ ...current, firma_arrendador_registrada: event.target.checked }))} />Firma arrendador</label>
              <label className="checkbox-row"><input type="checkbox" checked={documentoFormalizarDraft.firma_arrendatario_registrada} onChange={(event) => setDocumentoFormalizarDraft((current) => ({ ...current, firma_arrendatario_registrada: event.target.checked }))} />Firma arrendatario</label>
              <label className="checkbox-row"><input type="checkbox" checked={documentoFormalizarDraft.firma_codeudor_registrada} onChange={(event) => setDocumentoFormalizarDraft((current) => ({ ...current, firma_codeudor_registrada: event.target.checked }))} />Firma codeudor</label>
              <label className="checkbox-row"><input type="checkbox" checked={documentoFormalizarDraft.recepcion_notarial_registrada} onChange={(event) => setDocumentoFormalizarDraft((current) => ({ ...current, recepcion_notarial_registrada: event.target.checked }))} />Recepción notarial</label>
              <input placeholder="Evidencia formalización" value={documentoFormalizarDraft.evidencia_formalizacion_ref} onChange={(event) => setDocumentoFormalizarDraft((current) => ({ ...current, evidencia_formalizacion_ref: event.target.value }))} />
              <button type="submit" className="button-primary" disabled={isSubmitting || !documentoFormalizarDraft.documentoId || !documentoFormalizarDraft.evidencia_formalizacion_ref.trim()}>Formalizar documento</button>
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
        { label: 'Perfil PN', render: (row) => row.requiere_nacionalidad_arrendatario || row.requiere_estado_civil_arrendatario || row.requiere_profesion_arrendatario ? 'Sí' : 'No' },
        { label: 'Notaría', render: (row) => row.requiere_notaria ? 'Sí' : 'No' },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />

      <TableBlock title="Plantillas documentales" subtitle="Versiones controladas para emisión PDF." rows={filteredPlantillasDocumentales} empty="No hay plantillas para este filtro." isLoading={isLoading} loadingLabel="Cargando documentos..." columns={[
        { label: 'Tipo documental', render: (row) => row.tipo_documental },
        { label: 'Versión', render: (row) => row.version_plantilla },
        { label: 'Plantilla', render: (row) => row.plantilla_ref },
        { label: 'Checksum', render: (row) => row.checksum_plantilla.slice(0, 12) },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />

      <TableBlock title="Expediente integral" subtitle={`${expedienteItemsTotal} documentos y evidencias únicos en el orden final.`} rows={filteredExpedienteItems} empty="No hay documentos ni evidencias para este filtro." isLoading={isLoading} loadingLabel="Cargando expediente integral..." columns={[
        { label: 'Expediente', render: (row) => `${expedienteById.get(row.expediente)?.entidad_tipo || 'expediente'} · ${expedienteById.get(row.expediente)?.entidad_id || row.expediente}` },
        { label: 'Clase', render: (row) => row.clase === 'pdf_canonico' ? 'PDF canónico' : 'Evidencia' },
        { label: 'Categoría', render: (row) => row.categoria },
        { label: 'Subcategoría', render: (row) => row.subcategoria || '-' },
        { label: 'Título', render: (row) => row.titulo_operativo },
        { label: 'Ext', render: (row) => row.extension },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Origen', render: (row) => row.origen_auditoria },
        { label: 'Storage', render: (row) => row.storage_ref },
        { label: 'Acción', render: (row) => row.source_model === 'documento_emitido' && canEditDocumentos ? <div className="inline-actions"><button type="button" className="button-ghost inline-action" onClick={() => setDocumentoFormalizarDraft((current) => ({ ...current, documentoId: String(row.source_id) }))}>Formalizar</button><button type="button" className="button-ghost inline-action" onClick={() => goToDocumentoContext(row.source_id)}>Canales</button></div> : 'En expediente' },
      ]} />
    </>
  )
}
