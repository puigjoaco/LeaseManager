import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock } from '../shared'

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'
type ContactoPagoItem = { id: number; arrendatario?: number; arrendatario_display?: string; nombre: string; rol_operativo: string; email: string; telefono: string; evidencia_autorizacion_ref: string; es_principal: boolean; estado: string }
type ArrendatarioItem = { id: number; nombre_razon_social: string; rut: string; tipo_arrendatario: string; email: string; telefono: string; domicilio_notificaciones: string; estado_contacto: string; nacionalidad: string; estado_civil: string; profesion: string; whatsapp_opt_in: boolean; whatsapp_opt_in_evidencia_ref: string; whatsapp_bloqueado: boolean; whatsapp_bloqueo_motivo: string; whatsapp_bloqueo_evidencia_ref: string; whatsapp_bloqueado_at: string | null; whatsapp_rehabilitacion_ref: string; whatsapp_rehabilitado_at: string | null; contactos_pago?: ContactoPagoItem[] }
type MandatoItem = { id: number; propiedad_codigo: string; propietario_display: string }
type IdentidadItem = { id: number; canal: string; remitente_visible: string; direccion_o_numero: string; estado: string }
type PoliticaFirmaItem = { id: number; tipo_documental: string; estado: string }
type ContratoItem = { id: number; codigo_contrato: string; mandato_operacion: number; arrendatario: number; identidad_envio_override: number | null; identidad_envio_override_display: string | null; politica_documental: number | null; politica_documental_tipo: string | null; politica_documental_estado: string | null; fecha_inicio: string; fecha_fin_vigente: string; fecha_entrega: string | null; entrega_llaves_autorizacion_ref: string; entrega_llaves_autorizacion_motivo: string; fecha_registro_operativo: string | null; terminacion_anticipada_prorrata_ref: string; terminacion_anticipada_prorrata_motivo: string; requiere_notificacion_manual_retroactiva: boolean; alerta_notificacion_manual_retroactiva: string; dia_pago_mensual: number; plazo_notificacion_termino_dias: number; dias_prealerta_admin: number; estado: string; tiene_tramos: boolean; tiene_gastos_comunes: boolean; snapshot_representante_legal: { nombre?: string; rut?: string }; contrato_propiedades_detail: Array<{ propiedad: number; propiedad_codigo: string; propiedad_direccion: string; rol_en_contrato: string }>; periodos_contractuales_detail: Array<{ numero_periodo: number; fecha_inicio: string; fecha_fin: string; monto_base: string; moneda_base: string; tipo_periodo: string; origen_periodo: string; politica_base_renovacion_ref: string; politica_base_renovacion_motivo: string }>; codeudores_solidarios_detail: Array<{ id: number; snapshot_identidad: { nombre?: string; rut?: string }; fecha_inclusion: string; estado: string }> }
type AvisoItem = { id: number; contrato: number; fecha_efectiva: string; causal: string; estado: string; resolucion_conflicto_renovacion_ref: string; resolucion_conflicto_renovacion_motivo: string; registrado_at: string | null; fecha_limite_registro_oportuno: string | null; registrado_fuera_plazo: boolean; alerta_registro_fuera_plazo: string }

type ArrendatarioDraft = { tipo_arrendatario: string; nombre_razon_social: string; rut: string; email: string; telefono: string; domicilio_notificaciones: string; estado_contacto: string; nacionalidad: string; estado_civil: string; profesion: string; whatsapp_opt_in: boolean; whatsapp_opt_in_evidencia_ref: string; whatsapp_bloqueado: boolean; whatsapp_bloqueo_motivo: string; whatsapp_bloqueo_evidencia_ref: string; whatsapp_rehabilitacion_ref: string }
type ContactoPagoDraft = { arrendatario: string; nombre: string; rol_operativo: string; email: string; telefono: string; evidencia_autorizacion_ref: string; es_principal: boolean; estado: string }
type ContratoDraft = { codigo_contrato: string; mandato_operacion: string; arrendatario: string; identidad_envio_override: string; politica_documental: string; fecha_inicio: string; fecha_fin_vigente: string; fecha_entrega: string; entrega_llaves_autorizacion_ref: string; entrega_llaves_autorizacion_motivo: string; representante_legal_nombre: string; representante_legal_rut: string; terminacion_anticipada_prorrata_ref: string; terminacion_anticipada_prorrata_motivo: string; dia_pago_mensual: string; plazo_notificacion_termino_dias: string; dias_prealerta_admin: string; estado: string; tiene_tramos: boolean; tiene_gastos_comunes: boolean; monto_base: string; moneda_base: string; tipo_periodo: string; origen_periodo: string }
type AvisoDraft = { contrato: string; fecha_efectiva: string; causal: string; estado: string; resolucion_conflicto_renovacion_ref: string; resolucion_conflicto_renovacion_motivo: string }

export function ContratosWorkspace({
  canEditContratos,
  editingArrendatarioId,
  arrendatarioDraft,
  setArrendatarioDraft,
  handleCreateArrendatario,
  cancelEditArrendatario,
  contactoPagoDraft,
  setContactoPagoDraft,
  handleCreateContactoPago,
  editingContratoId,
  contratoDraft,
  setContratoDraft,
  handleCreateContrato,
  cancelEditContrato,
  avisoDraft,
  setAvisoDraft,
  handleCreateAviso,
  mandatos,
  identidades,
  politicasFirma,
  arrendatarios,
  contratos,
  filteredArrendatarios,
  filteredContratos,
  filteredAvisos,
  arrendatarioById,
  mandatoById,
  contratoById,
  toneFor,
  isSubmitting,
  isLoading,
  startEditArrendatario,
  startEditContrato,
  goToArrendatarioContext,
  goToContratoContext,
  prepareExpedienteForContract,
}: {
  canEditContratos: boolean
  editingArrendatarioId: number | null
  arrendatarioDraft: ArrendatarioDraft
  setArrendatarioDraft: Dispatch<SetStateAction<ArrendatarioDraft>>
  handleCreateArrendatario: (event: FormEvent<HTMLFormElement>) => Promise<void>
  cancelEditArrendatario: () => void
  contactoPagoDraft: ContactoPagoDraft
  setContactoPagoDraft: Dispatch<SetStateAction<ContactoPagoDraft>>
  handleCreateContactoPago: (event: FormEvent<HTMLFormElement>) => Promise<void>
  editingContratoId: number | null
  contratoDraft: ContratoDraft
  setContratoDraft: Dispatch<SetStateAction<ContratoDraft>>
  handleCreateContrato: (event: FormEvent<HTMLFormElement>) => Promise<void>
  cancelEditContrato: () => void
  avisoDraft: AvisoDraft
  setAvisoDraft: Dispatch<SetStateAction<AvisoDraft>>
  handleCreateAviso: (event: FormEvent<HTMLFormElement>) => Promise<void>
  mandatos: MandatoItem[]
  identidades: IdentidadItem[]
  politicasFirma: PoliticaFirmaItem[]
  arrendatarios: ArrendatarioItem[]
  contratos: ContratoItem[]
  filteredArrendatarios: ArrendatarioItem[]
  filteredContratos: ContratoItem[]
  filteredAvisos: AvisoItem[]
  arrendatarioById: ReadonlyMap<number, ArrendatarioItem>
  mandatoById: ReadonlyMap<number, MandatoItem>
  contratoById: ReadonlyMap<number, ContratoItem>
  toneFor: (value: string) => Tone
  isSubmitting: boolean
  isLoading: boolean
  startEditArrendatario: (row: ArrendatarioItem) => void
  startEditContrato: (row: ContratoItem) => void
  goToArrendatarioContext: (arrendatarioId: number) => void
  goToContratoContext: (contratoId: number) => void
  prepareExpedienteForContract: (row: ContratoItem) => void
}) {
  const contractPolicies = politicasFirma.filter((item) => item.tipo_documental === 'contrato_principal' && item.estado === 'activa')
  const requiresDocumentPolicy = contratoDraft.estado === 'vigente' || contratoDraft.estado === 'futuro'
  const requiresTerminationProrationTrace = contratoDraft.estado === 'terminado_anticipadamente'
  const selectedContractTenant = arrendatarios.find((item) => item.id === Number(contratoDraft.arrendatario))
  const isCompanyContractTenant = selectedContractTenant?.tipo_arrendatario === 'empresa'
  const showCompanyRepresentativeFields = Boolean(isCompanyContractTenant || contratoDraft.representante_legal_nombre || contratoDraft.representante_legal_rut)
  const requiresCompanyRepresentative = Boolean(isCompanyContractTenant && (contratoDraft.estado === 'vigente' || contratoDraft.estado === 'futuro'))
  const paymentContacts = arrendatarios.flatMap((tenant) => (tenant.contactos_pago ?? []).map((contact) => ({ ...contact, arrendatario: contact.arrendatario ?? tenant.id, arrendatario_display: contact.arrendatario_display || tenant.nombre_razon_social })))
  const activePaymentContacts = (tenant: ArrendatarioItem) => (tenant.contactos_pago ?? []).filter((contact) => contact.estado === 'activo')

  function representativeSnapshotBadge(row: ContratoItem) {
    const tenant = arrendatarioById.get(row.arrendatario)
    if (tenant?.tipo_arrendatario !== 'empresa') {
      return <Badge label="no aplica" tone="neutral" />
    }
    return row.snapshot_representante_legal?.nombre && row.snapshot_representante_legal?.rut
      ? <Badge label="snapshot" tone="positive" />
      : <Badge label="pendiente" tone="warning" />
  }

  function paymentContactBadge(row: ArrendatarioItem) {
    const activeContacts = activePaymentContacts(row)
    if (activeContacts.some((contact) => contact.es_principal)) {
      return <Badge label="principal" tone="positive" />
    }
    if (activeContacts.length > 0) {
      return <Badge label="activo" tone="positive" />
    }
    return <Badge label="pendiente" tone="warning" />
  }

  return (
    <>
      {!canEditContratos ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Contratos.</div> : null}
      <section className="form-grid">
        <section className="panel">
          <div className="section-heading"><div><h2>{editingArrendatarioId ? 'Editar arrendatario' : 'Alta rápida de arrendatario'}</h2><p>Base mínima para contratar sobre mandatos ya activos.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateArrendatario}>
            <select value={arrendatarioDraft.tipo_arrendatario} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, tipo_arrendatario: event.target.value }))}><option value="persona_natural">Persona natural</option><option value="empresa">Empresa</option></select>
            <input placeholder="Nombre o razón social" value={arrendatarioDraft.nombre_razon_social} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, nombre_razon_social: event.target.value }))} />
            <input placeholder="RUT" value={arrendatarioDraft.rut} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, rut: event.target.value }))} />
            <input placeholder="Email" value={arrendatarioDraft.email} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, email: event.target.value }))} />
            <input placeholder="Teléfono" value={arrendatarioDraft.telefono} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, telefono: event.target.value }))} />
            <input placeholder="Domicilio de notificaciones" value={arrendatarioDraft.domicilio_notificaciones} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, domicilio_notificaciones: event.target.value }))} />
            <select value={arrendatarioDraft.estado_contacto} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, estado_contacto: event.target.value }))}><option value="pendiente">Pendiente</option><option value="activo">Activo</option><option value="inactivo">Inactivo</option></select>
            <input placeholder="Nacionalidad" value={arrendatarioDraft.nacionalidad} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, nacionalidad: event.target.value }))} />
            <select value={arrendatarioDraft.estado_civil} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, estado_civil: event.target.value }))}>
              <option value="">Estado civil</option>
              <option value="soltero">Soltero</option>
              <option value="casado">Casado</option>
              <option value="divorciado">Divorciado</option>
              <option value="viudo">Viudo</option>
              <option value="conviviente_civil">Conviviente civil</option>
              <option value="otro">Otro</option>
            </select>
            <input placeholder="Profesión u oficio" value={arrendatarioDraft.profesion} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, profesion: event.target.value }))} />
            <label className="checkbox-row"><input type="checkbox" checked={arrendatarioDraft.whatsapp_opt_in} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, whatsapp_opt_in: event.target.checked }))} />Opt-in WhatsApp</label>
            <input placeholder="Evidencia opt-in WhatsApp" value={arrendatarioDraft.whatsapp_opt_in_evidencia_ref} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, whatsapp_opt_in_evidencia_ref: event.target.value }))} />
            <label className="checkbox-row"><input type="checkbox" checked={arrendatarioDraft.whatsapp_bloqueado} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, whatsapp_bloqueado: event.target.checked }))} />WhatsApp bloqueado</label>
            {arrendatarioDraft.whatsapp_bloqueado ? (
              <>
                <input placeholder="Motivo bloqueo WhatsApp" value={arrendatarioDraft.whatsapp_bloqueo_motivo} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, whatsapp_bloqueo_motivo: event.target.value }))} />
                <input placeholder="Evidencia bloqueo WhatsApp" value={arrendatarioDraft.whatsapp_bloqueo_evidencia_ref} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, whatsapp_bloqueo_evidencia_ref: event.target.value }))} />
              </>
            ) : null}
            {!arrendatarioDraft.whatsapp_bloqueado ? <input placeholder="Referencia rehabilitación WhatsApp" value={arrendatarioDraft.whatsapp_rehabilitacion_ref} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, whatsapp_rehabilitacion_ref: event.target.value }))} /> : null}
            <div className="inline-actions">
              <button type="submit" className="button-primary" disabled={isSubmitting || !canEditContratos}>{editingArrendatarioId ? 'Guardar cambios' : 'Guardar arrendatario'}</button>
              {editingArrendatarioId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditArrendatario}>Cancelar</button> : null}
            </div>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Contacto de pago</h2><p>Cobertura estructurada requerida para contratos vigentes o futuros.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateContactoPago}>
            <select value={contactoPagoDraft.arrendatario} onChange={(event) => setContactoPagoDraft((current) => ({ ...current, arrendatario: event.target.value }))}>
              <option value="">Selecciona arrendatario</option>
              {arrendatarios.map((item) => <option key={item.id} value={item.id}>{item.nombre_razon_social}</option>)}
            </select>
            <input placeholder="Nombre contacto pago" value={contactoPagoDraft.nombre} onChange={(event) => setContactoPagoDraft((current) => ({ ...current, nombre: event.target.value }))} />
            <input placeholder="Rol operativo" value={contactoPagoDraft.rol_operativo} onChange={(event) => setContactoPagoDraft((current) => ({ ...current, rol_operativo: event.target.value }))} />
            <input placeholder="Email pago" value={contactoPagoDraft.email} onChange={(event) => setContactoPagoDraft((current) => ({ ...current, email: event.target.value }))} />
            <input placeholder="Teléfono pago" value={contactoPagoDraft.telefono} onChange={(event) => setContactoPagoDraft((current) => ({ ...current, telefono: event.target.value }))} />
            <input placeholder="Evidencia autorización" value={contactoPagoDraft.evidencia_autorizacion_ref} onChange={(event) => setContactoPagoDraft((current) => ({ ...current, evidencia_autorizacion_ref: event.target.value }))} />
            <label className="checkbox-row"><input type="checkbox" checked={contactoPagoDraft.es_principal} onChange={(event) => setContactoPagoDraft((current) => ({ ...current, es_principal: event.target.checked }))} />Principal</label>
            <select value={contactoPagoDraft.estado} onChange={(event) => setContactoPagoDraft((current) => ({ ...current, estado: event.target.value }))}><option value="activo">Activo</option><option value="inactivo">Inactivo</option></select>
            <button type="submit" className="button-primary" disabled={isSubmitting || !canEditContratos || !contactoPagoDraft.arrendatario || !contactoPagoDraft.nombre.trim() || (!contactoPagoDraft.email.trim() && !contactoPagoDraft.telefono.trim())}>Guardar contacto pago</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>{editingContratoId ? 'Editar contrato' : 'Alta rápida de contrato'}</h2><p>Contrato simple con una propiedad principal y un primer período.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateContrato}>
            <input placeholder="Código contrato" value={contratoDraft.codigo_contrato} onChange={(event) => setContratoDraft((current) => ({ ...current, codigo_contrato: event.target.value }))} disabled={editingContratoId != null} />
            <select value={contratoDraft.mandato_operacion} onChange={(event) => setContratoDraft((current) => ({ ...current, mandato_operacion: event.target.value }))}>
              <option value="">Selecciona mandato</option>
              {mandatos.map((item) => <option key={item.id} value={item.id}>{item.propiedad_codigo} · {item.propietario_display}</option>)}
            </select>
            <select value={contratoDraft.arrendatario} onChange={(event) => setContratoDraft((current) => ({ ...current, arrendatario: event.target.value }))} disabled={editingContratoId != null}>
              <option value="">Selecciona arrendatario</option>
              {arrendatarios.map((item) => <option key={item.id} value={item.id}>{item.nombre_razon_social}</option>)}
            </select>
            <select value={contratoDraft.identidad_envio_override} onChange={(event) => setContratoDraft((current) => ({ ...current, identidad_envio_override: event.target.value }))}>
              <option value="">Identidad por mandato</option>
              {identidades.filter((item) => item.estado === 'activa').map((item) => <option key={item.id} value={item.id}>{item.canal} · {item.remitente_visible}</option>)}
            </select>
            <select value={contratoDraft.politica_documental} onChange={(event) => setContratoDraft((current) => ({ ...current, politica_documental: event.target.value }))}>
              <option value="">Política documental</option>
              {contractPolicies.map((item) => <option key={item.id} value={item.id}>Contrato principal · {item.estado}</option>)}
            </select>
            <input type="date" value={contratoDraft.fecha_inicio} onChange={(event) => setContratoDraft((current) => ({ ...current, fecha_inicio: event.target.value }))} />
            <input type="date" value={contratoDraft.fecha_fin_vigente} onChange={(event) => setContratoDraft((current) => ({ ...current, fecha_fin_vigente: event.target.value }))} />
            <input type="date" value={contratoDraft.fecha_entrega} onChange={(event) => setContratoDraft((current) => ({ ...current, fecha_entrega: event.target.value }))} />
            <input placeholder="Ref. autorización entrega" value={contratoDraft.entrega_llaves_autorizacion_ref} onChange={(event) => setContratoDraft((current) => ({ ...current, entrega_llaves_autorizacion_ref: event.target.value }))} />
            <input placeholder="Motivo autorización entrega" value={contratoDraft.entrega_llaves_autorizacion_motivo} onChange={(event) => setContratoDraft((current) => ({ ...current, entrega_llaves_autorizacion_motivo: event.target.value }))} />
            {showCompanyRepresentativeFields ? (
              <>
                <input placeholder="Representante legal" value={contratoDraft.representante_legal_nombre} onChange={(event) => setContratoDraft((current) => ({ ...current, representante_legal_nombre: event.target.value }))} />
                <input placeholder="RUT representante legal" value={contratoDraft.representante_legal_rut} onChange={(event) => setContratoDraft((current) => ({ ...current, representante_legal_rut: event.target.value }))} />
              </>
            ) : null}
            <input placeholder="Monto base" value={contratoDraft.monto_base} onChange={(event) => setContratoDraft((current) => ({ ...current, monto_base: event.target.value }))} />
            <select value={contratoDraft.moneda_base} onChange={(event) => setContratoDraft((current) => ({ ...current, moneda_base: event.target.value }))}><option value="CLP">CLP</option><option value="UF">UF</option></select>
            <select value={contratoDraft.estado} onChange={(event) => setContratoDraft((current) => ({ ...current, estado: event.target.value }))}><option value="vigente">Vigente</option><option value="pendiente_activacion">Pendiente activación</option><option value="futuro">Futuro</option><option value="terminado_anticipadamente">Terminado anticipadamente</option></select>
            {requiresTerminationProrationTrace ? (
              <>
                <input placeholder="Ref. prorrata término anticipado" value={contratoDraft.terminacion_anticipada_prorrata_ref} onChange={(event) => setContratoDraft((current) => ({ ...current, terminacion_anticipada_prorrata_ref: event.target.value }))} />
                <input placeholder="Criterio prorrata término anticipado" value={contratoDraft.terminacion_anticipada_prorrata_motivo} onChange={(event) => setContratoDraft((current) => ({ ...current, terminacion_anticipada_prorrata_motivo: event.target.value }))} />
              </>
            ) : null}
            <input placeholder="Día pago mensual" value={contratoDraft.dia_pago_mensual} onChange={(event) => setContratoDraft((current) => ({ ...current, dia_pago_mensual: event.target.value }))} />
            <input placeholder="Plazo aviso término" value={contratoDraft.plazo_notificacion_termino_dias} onChange={(event) => setContratoDraft((current) => ({ ...current, plazo_notificacion_termino_dias: event.target.value }))} />
            <input placeholder="Prealerta admin" value={contratoDraft.dias_prealerta_admin} onChange={(event) => setContratoDraft((current) => ({ ...current, dias_prealerta_admin: event.target.value }))} />
            <label className="checkbox-row"><input type="checkbox" checked={contratoDraft.tiene_tramos} onChange={(event) => setContratoDraft((current) => ({ ...current, tiene_tramos: event.target.checked }))} />Tiene tramos</label>
            <label className="checkbox-row"><input type="checkbox" checked={contratoDraft.tiene_gastos_comunes} onChange={(event) => setContratoDraft((current) => ({ ...current, tiene_gastos_comunes: event.target.checked }))} />Tiene gastos comunes</label>
            <div className="inline-actions">
              <button type="submit" className="button-primary" disabled={isSubmitting || !canEditContratos || !contratoDraft.codigo_contrato || !contratoDraft.mandato_operacion || !contratoDraft.arrendatario || !contratoDraft.monto_base || (requiresDocumentPolicy && !contratoDraft.politica_documental) || (requiresCompanyRepresentative && (!contratoDraft.representante_legal_nombre.trim() || !contratoDraft.representante_legal_rut.trim())) || (requiresTerminationProrationTrace && (!contratoDraft.terminacion_anticipada_prorrata_ref || !contratoDraft.terminacion_anticipada_prorrata_motivo))}>{editingContratoId ? 'Guardar cambios' : 'Guardar contrato'}</button>
              {editingContratoId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditContrato}>Cancelar</button> : null}
            </div>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Alta rápida de aviso de término</h2><p>Base para contratos futuros y no renovación.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateAviso}>
            <select value={avisoDraft.contrato} onChange={(event) => setAvisoDraft((current) => ({ ...current, contrato: event.target.value }))}>
              <option value="">Selecciona contrato</option>
              {contratos.map((item) => <option key={item.id} value={item.id}>{item.codigo_contrato}</option>)}
            </select>
            <input type="date" value={avisoDraft.fecha_efectiva} onChange={(event) => setAvisoDraft((current) => ({ ...current, fecha_efectiva: event.target.value }))} />
            <input placeholder="Causal" value={avisoDraft.causal} onChange={(event) => setAvisoDraft((current) => ({ ...current, causal: event.target.value }))} />
            <input placeholder="Ref. resolución renovación" value={avisoDraft.resolucion_conflicto_renovacion_ref} onChange={(event) => setAvisoDraft((current) => ({ ...current, resolucion_conflicto_renovacion_ref: event.target.value }))} />
            <input placeholder="Motivo resolución renovación" value={avisoDraft.resolucion_conflicto_renovacion_motivo} onChange={(event) => setAvisoDraft((current) => ({ ...current, resolucion_conflicto_renovacion_motivo: event.target.value }))} />
            <select value={avisoDraft.estado} onChange={(event) => setAvisoDraft((current) => ({ ...current, estado: event.target.value }))}><option value="registrado">Registrado</option><option value="borrador">Borrador</option></select>
            <button type="submit" className="button-primary" disabled={isSubmitting || !canEditContratos || !avisoDraft.contrato || !avisoDraft.causal}>Guardar aviso</button>
          </form>
        </section>
      </section>

      <TableBlock title="Arrendatarios" subtitle="Base actual de contraparte contractual." rows={filteredArrendatarios} empty="No hay arrendatarios para este filtro." isLoading={isLoading} loadingLabel="Cargando contratos..." columns={[
        { label: 'Nombre', render: (row) => row.nombre_razon_social },
        { label: 'RUT', render: (row) => row.rut },
        { label: 'Tipo', render: (row) => row.tipo_arrendatario.replaceAll('_', ' ') },
        { label: 'Perfil doc.', render: (row) => row.nacionalidad || row.estado_civil || row.profesion ? <Badge label="perfil" tone="positive" /> : <Badge label="pendiente" tone="warning" /> },
        { label: 'Contacto', render: (row) => row.email || row.telefono || 'Sin dato' },
        { label: 'Pago', render: (row) => paymentContactBadge(row) },
        { label: 'WhatsApp', render: (row) => row.whatsapp_bloqueado ? <Badge label={row.whatsapp_bloqueado_at ? 'bloqueado trazado' : 'bloqueado'} tone="danger" /> : row.whatsapp_rehabilitado_at ? <Badge label="rehabilitado" tone="positive" /> : row.whatsapp_opt_in ? <Badge label="opt-in" tone="positive" /> : <Badge label="sin opt-in" tone="warning" /> },
        { label: 'Estado', render: (row) => <Badge label={row.estado_contacto} tone={toneFor(row.estado_contacto)} /> },
        { label: 'Editar', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditArrendatario(row)}>Editar</button> },
        { label: 'Siguiente paso', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => goToArrendatarioContext(row.id)}>Estado de cuenta</button> },
      ]} />
      <TableBlock title="Contratos" subtitle="Contratos cargados sobre mandatos ya vigentes." rows={filteredContratos} empty="No hay contratos para este filtro." isLoading={isLoading} loadingLabel="Cargando contratos..." columns={[
        { label: 'Código', render: (row) => row.codigo_contrato },
        { label: 'Arrendatario', render: (row) => arrendatarioById.get(row.arrendatario)?.nombre_razon_social || row.arrendatario },
        { label: 'Mandato', render: (row) => mandatoById.get(row.mandato_operacion)?.propiedad_codigo || row.mandato_operacion },
        { label: 'Identidad', render: (row) => row.identidad_envio_override_display || 'Mandato' },
        { label: 'Política', render: (row) => row.politica_documental_tipo === 'contrato_principal' && row.politica_documental_estado === 'activa' ? <Badge label="contrato" tone="positive" /> : <Badge label="pendiente" tone="warning" /> },
        { label: 'Rep. legal', render: (row) => representativeSnapshotBadge(row) },
        { label: 'Propiedad', render: (row) => row.contrato_propiedades_detail[0] ? `${row.contrato_propiedades_detail[0].propiedad_codigo} · ${row.contrato_propiedades_detail[0].propiedad_direccion}` : 'Sin propiedad' },
        { label: 'Periodo', render: (row) => `${row.fecha_inicio} → ${row.fecha_fin_vigente}` },
        { label: 'Retroactivo', render: (row) => row.requiere_notificacion_manual_retroactiva ? <Badge label="aviso manual" tone="warning" /> : <Badge label="sin alerta" tone="neutral" /> },
        { label: 'Entrega', render: (row) => row.fecha_entrega ? row.entrega_llaves_autorizacion_ref ? <Badge label="autorizada" tone="positive" /> : <Badge label="registrada" tone="neutral" /> : <Badge label="pendiente" tone="neutral" /> },
        { label: 'Renovación', render: (row) => row.periodos_contractuales_detail.some((periodo) => periodo.politica_base_renovacion_ref) ? <Badge label="política base" tone="positive" /> : <Badge label="base tramo" tone="neutral" /> },
        { label: 'Prorrata', render: (row) => row.terminacion_anticipada_prorrata_ref ? <Badge label="trazada" tone="positive" /> : row.estado === 'terminado_anticipadamente' ? <Badge label="sin traza" tone="warning" /> : <Badge label="no aplica" tone="neutral" /> },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Editar', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditContrato(row)}>Editar</button> },
        { label: 'Siguiente paso', render: (row) => <div className="inline-actions"><button type="button" className="button-ghost inline-action" onClick={() => goToContratoContext(row.id)}>Cobranza</button><button type="button" className="button-ghost inline-action" onClick={() => prepareExpedienteForContract(row)}>Documentos</button></div> },
      ]} />
      <TableBlock title="Contactos de pago" subtitle="Contactos activos e históricos por arrendatario." rows={paymentContacts} empty="No hay contactos de pago para este filtro." isLoading={isLoading} loadingLabel="Cargando contratos..." columns={[
        { label: 'Arrendatario', render: (row) => row.arrendatario_display || arrendatarioById.get(row.arrendatario || 0)?.nombre_razon_social || row.arrendatario || 'Sin arrendatario' },
        { label: 'Nombre', render: (row) => row.nombre },
        { label: 'Rol', render: (row) => row.rol_operativo.replaceAll('_', ' ') },
        { label: 'Contacto', render: (row) => row.email || row.telefono || 'Sin dato' },
        { label: 'Evidencia', render: (row) => row.evidencia_autorizacion_ref || 'Sin ref' },
        { label: 'Principal', render: (row) => row.es_principal ? <Badge label="principal" tone="positive" /> : <Badge label="secundario" tone="neutral" /> },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />
      <TableBlock title="Avisos de término" subtitle="Base para no renovación y contratos futuros." rows={filteredAvisos} empty="No hay avisos para este filtro." isLoading={isLoading} loadingLabel="Cargando contratos..." columns={[
        { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
        { label: 'Fecha efectiva', render: (row) => row.fecha_efectiva },
        { label: 'Registro', render: (row) => row.registrado_fuera_plazo ? <Badge label="fuera plazo" tone="warning" /> : <Badge label={row.registrado_at ? 'oportuno' : 'sin timestamp'} tone={row.registrado_at ? 'neutral' : 'danger'} /> },
        { label: 'Registrado', render: (row) => row.registrado_at ? row.registrado_at.slice(0, 10) : 'Sin timestamp' },
        { label: 'Resolución', render: (row) => row.resolucion_conflicto_renovacion_ref ? <Badge label="renovación resuelta" tone="positive" /> : <Badge label="sin ref" tone="neutral" /> },
        { label: 'Causal', render: (row) => row.causal },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />
    </>
  )
}
