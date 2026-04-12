import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock } from '../shared'

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'
type ArrendatarioItem = { id: number; nombre_razon_social: string; rut: string; tipo_arrendatario: string; email: string; telefono: string; domicilio_notificaciones: string; estado_contacto: string; whatsapp_bloqueado: boolean }
type MandatoItem = { id: number; propiedad_codigo: string; propietario_display: string }
type ContratoItem = { id: number; codigo_contrato: string; mandato_operacion: number; arrendatario: number; fecha_inicio: string; fecha_fin_vigente: string; fecha_entrega: string | null; dia_pago_mensual: number; plazo_notificacion_termino_dias: number; dias_prealerta_admin: number; estado: string; tiene_tramos: boolean; tiene_gastos_comunes: boolean; contrato_propiedades_detail: Array<{ propiedad: number; propiedad_codigo: string; propiedad_direccion: string; rol_en_contrato: string }>; periodos_contractuales_detail: Array<{ numero_periodo: number; fecha_inicio: string; fecha_fin: string; monto_base: string; moneda_base: string; tipo_periodo: string; origen_periodo: string }> }
type AvisoItem = { id: number; contrato: number; fecha_efectiva: string; causal: string; estado: string }

type ArrendatarioDraft = { tipo_arrendatario: string; nombre_razon_social: string; rut: string; email: string; telefono: string; domicilio_notificaciones: string; estado_contacto: string; whatsapp_bloqueado: boolean }
type ContratoDraft = { codigo_contrato: string; mandato_operacion: string; arrendatario: string; fecha_inicio: string; fecha_fin_vigente: string; fecha_entrega: string; dia_pago_mensual: string; plazo_notificacion_termino_dias: string; dias_prealerta_admin: string; estado: string; tiene_tramos: boolean; tiene_gastos_comunes: boolean; monto_base: string; moneda_base: string; tipo_periodo: string; origen_periodo: string }
type AvisoDraft = { contrato: string; fecha_efectiva: string; causal: string; estado: string }

export function ContratosWorkspace({
  canEditContratos,
  editingArrendatarioId,
  arrendatarioDraft,
  setArrendatarioDraft,
  handleCreateArrendatario,
  cancelEditArrendatario,
  editingContratoId,
  contratoDraft,
  setContratoDraft,
  handleCreateContrato,
  cancelEditContrato,
  avisoDraft,
  setAvisoDraft,
  handleCreateAviso,
  mandatos,
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
  editingContratoId: number | null
  contratoDraft: ContratoDraft
  setContratoDraft: Dispatch<SetStateAction<ContratoDraft>>
  handleCreateContrato: (event: FormEvent<HTMLFormElement>) => Promise<void>
  cancelEditContrato: () => void
  avisoDraft: AvisoDraft
  setAvisoDraft: Dispatch<SetStateAction<AvisoDraft>>
  handleCreateAviso: (event: FormEvent<HTMLFormElement>) => Promise<void>
  mandatos: MandatoItem[]
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
  startEditArrendatario: (row: ArrendatarioItem) => void
  startEditContrato: (row: ContratoItem) => void
  goToArrendatarioContext: (arrendatarioId: number) => void
  goToContratoContext: (contratoId: number) => void
  prepareExpedienteForContract: (row: ContratoItem) => void
}) {
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
            <label className="checkbox-row"><input type="checkbox" checked={arrendatarioDraft.whatsapp_bloqueado} onChange={(event) => setArrendatarioDraft((current) => ({ ...current, whatsapp_bloqueado: event.target.checked }))} />WhatsApp bloqueado</label>
            <div className="inline-actions">
              <button type="submit" className="button-primary" disabled={isSubmitting || !canEditContratos}>{editingArrendatarioId ? 'Guardar cambios' : 'Guardar arrendatario'}</button>
              {editingArrendatarioId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditArrendatario}>Cancelar</button> : null}
            </div>
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
            <input type="date" value={contratoDraft.fecha_inicio} onChange={(event) => setContratoDraft((current) => ({ ...current, fecha_inicio: event.target.value }))} />
            <input type="date" value={contratoDraft.fecha_fin_vigente} onChange={(event) => setContratoDraft((current) => ({ ...current, fecha_fin_vigente: event.target.value }))} />
            <input type="date" value={contratoDraft.fecha_entrega} onChange={(event) => setContratoDraft((current) => ({ ...current, fecha_entrega: event.target.value }))} />
            <input placeholder="Monto base" value={contratoDraft.monto_base} onChange={(event) => setContratoDraft((current) => ({ ...current, monto_base: event.target.value }))} />
            <select value={contratoDraft.moneda_base} onChange={(event) => setContratoDraft((current) => ({ ...current, moneda_base: event.target.value }))}><option value="CLP">CLP</option><option value="UF">UF</option></select>
            <select value={contratoDraft.estado} onChange={(event) => setContratoDraft((current) => ({ ...current, estado: event.target.value }))}><option value="vigente">Vigente</option><option value="pendiente_activacion">Pendiente activación</option><option value="futuro">Futuro</option></select>
            <input placeholder="Día pago mensual" value={contratoDraft.dia_pago_mensual} onChange={(event) => setContratoDraft((current) => ({ ...current, dia_pago_mensual: event.target.value }))} />
            <input placeholder="Plazo aviso término" value={contratoDraft.plazo_notificacion_termino_dias} onChange={(event) => setContratoDraft((current) => ({ ...current, plazo_notificacion_termino_dias: event.target.value }))} />
            <input placeholder="Prealerta admin" value={contratoDraft.dias_prealerta_admin} onChange={(event) => setContratoDraft((current) => ({ ...current, dias_prealerta_admin: event.target.value }))} />
            <label className="checkbox-row"><input type="checkbox" checked={contratoDraft.tiene_tramos} onChange={(event) => setContratoDraft((current) => ({ ...current, tiene_tramos: event.target.checked }))} />Tiene tramos</label>
            <label className="checkbox-row"><input type="checkbox" checked={contratoDraft.tiene_gastos_comunes} onChange={(event) => setContratoDraft((current) => ({ ...current, tiene_gastos_comunes: event.target.checked }))} />Tiene gastos comunes</label>
            <div className="inline-actions">
              <button type="submit" className="button-primary" disabled={isSubmitting || !canEditContratos || !contratoDraft.codigo_contrato || !contratoDraft.mandato_operacion || !contratoDraft.arrendatario || !contratoDraft.monto_base}>{editingContratoId ? 'Guardar cambios' : 'Guardar contrato'}</button>
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
            <select value={avisoDraft.estado} onChange={(event) => setAvisoDraft((current) => ({ ...current, estado: event.target.value }))}><option value="registrado">Registrado</option><option value="borrador">Borrador</option></select>
            <button type="submit" className="button-primary" disabled={isSubmitting || !canEditContratos || !avisoDraft.contrato || !avisoDraft.causal}>Guardar aviso</button>
          </form>
        </section>
      </section>

      <TableBlock title="Arrendatarios" subtitle="Base actual de contraparte contractual." rows={filteredArrendatarios} empty="No hay arrendatarios para este filtro." columns={[
        { label: 'Nombre', render: (row) => row.nombre_razon_social },
        { label: 'RUT', render: (row) => row.rut },
        { label: 'Tipo', render: (row) => row.tipo_arrendatario.replaceAll('_', ' ') },
        { label: 'Contacto', render: (row) => row.email || row.telefono || 'Sin dato' },
        { label: 'Estado', render: (row) => <Badge label={row.estado_contacto} tone={toneFor(row.estado_contacto)} /> },
        { label: 'Editar', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditArrendatario(row)}>Editar</button> },
        { label: 'Siguiente paso', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => goToArrendatarioContext(row.id)}>Estado de cuenta</button> },
      ]} />
      <TableBlock title="Contratos" subtitle="Contratos cargados sobre mandatos ya vigentes." rows={filteredContratos} empty="No hay contratos para este filtro." columns={[
        { label: 'Código', render: (row) => row.codigo_contrato },
        { label: 'Arrendatario', render: (row) => arrendatarioById.get(row.arrendatario)?.nombre_razon_social || row.arrendatario },
        { label: 'Mandato', render: (row) => mandatoById.get(row.mandato_operacion)?.propiedad_codigo || row.mandato_operacion },
        { label: 'Propiedad', render: (row) => row.contrato_propiedades_detail[0] ? `${row.contrato_propiedades_detail[0].propiedad_codigo} · ${row.contrato_propiedades_detail[0].propiedad_direccion}` : 'Sin propiedad' },
        { label: 'Periodo', render: (row) => `${row.fecha_inicio} → ${row.fecha_fin_vigente}` },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Editar', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditContrato(row)}>Editar</button> },
        { label: 'Siguiente paso', render: (row) => <div className="inline-actions"><button type="button" className="button-ghost inline-action" onClick={() => goToContratoContext(row.id)}>Cobranza</button><button type="button" className="button-ghost inline-action" onClick={() => prepareExpedienteForContract(row)}>Documentos</button></div> },
      ]} />
      <TableBlock title="Avisos de término" subtitle="Base para no renovación y contratos futuros." rows={filteredAvisos} empty="No hay avisos para este filtro." columns={[
        { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
        { label: 'Fecha efectiva', render: (row) => row.fecha_efectiva },
        { label: 'Causal', render: (row) => row.causal },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />
    </>
  )
}
