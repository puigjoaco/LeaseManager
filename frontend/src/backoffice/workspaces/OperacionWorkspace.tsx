import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock } from '../shared'

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'
type OwnerOption = { tipo: string; id: number; label: string }
type CuentaItem = { id: number; institucion: string; numero_cuenta: string; tipo_cuenta: string; owner_tipo: string; owner_id: number; owner_display: string; titular_nombre: string; titular_rut: string; moneda_operativa: string; estado_operativo: string }
type IdentidadItem = { id: number; canal: string; remitente_visible: string; direccion_o_numero: string; owner_tipo: string; owner_display: string; estado: string }
type MandatoItem = {
  id: number
  propiedad_id: number
  propiedad_codigo: string
  propietario_tipo: string
  propietario_id: number
  propietario_display: string
  administrador_operativo_tipo: string
  administrador_operativo_id: number
  administrador_operativo_display: string
  recaudador_tipo: string
  recaudador_id: number
  recaudador_display: string
  entidad_facturadora_id: number | null
  entidad_facturadora_display: string | null
  cuenta_recaudadora_id: number
  cuenta_recaudadora_display: string
  tipo_relacion_operativa: string
  autoriza_recaudacion: boolean
  autoriza_facturacion: boolean
  autoriza_comunicacion: boolean
  vigencia_desde: string
  vigencia_hasta: string | null
  estado: string
}
type PropiedadOption = { id: number; codigo_propiedad: string; direccion: string }

type CuentaDraft = { institucion: string; numero_cuenta: string; tipo_cuenta: string; titular_nombre: string; titular_rut: string; moneda_operativa: string; estado_operativo: string; owner_tipo: string; owner_id: string }
type MandatoDraft = { propiedad_id: string; propietario_tipo: string; propietario_id: string; administrador_operativo_tipo: string; administrador_operativo_id: string; recaudador_tipo: string; recaudador_id: string; entidad_facturadora_id: string; cuenta_recaudadora_id: string; tipo_relacion_operativa: string; autoriza_recaudacion: boolean; autoriza_facturacion: boolean; autoriza_comunicacion: boolean; vigencia_desde: string; vigencia_hasta: string; estado: string }

export function OperacionWorkspace({
  canEditOperacion,
  editingCuentaId,
  cuentaDraft,
  setCuentaDraft,
  handleCreateCuenta,
  cancelEditCuenta,
  editingMandatoId,
  mandatoDraft,
  setMandatoDraft,
  handleCreateMandato,
  cancelEditMandato,
  simpleOwners,
  patrimonioOwners,
  propiedades,
  cuentas,
  filteredCuentas,
  filteredIdentidades,
  filteredMandatos,
  toneFor,
  isSubmitting,
  startEditCuenta,
  startEditMandato,
  goToCuentaConciliacion,
  goToMandatoContext,
}: {
  canEditOperacion: boolean
  editingCuentaId: number | null
  cuentaDraft: CuentaDraft
  setCuentaDraft: Dispatch<SetStateAction<CuentaDraft>>
  handleCreateCuenta: (event: FormEvent<HTMLFormElement>) => Promise<void>
  cancelEditCuenta: () => void
  editingMandatoId: number | null
  mandatoDraft: MandatoDraft
  setMandatoDraft: Dispatch<SetStateAction<MandatoDraft>>
  handleCreateMandato: (event: FormEvent<HTMLFormElement>) => Promise<void>
  cancelEditMandato: () => void
  simpleOwners: OwnerOption[]
  patrimonioOwners: OwnerOption[]
  propiedades: PropiedadOption[]
  cuentas: CuentaItem[]
  filteredCuentas: CuentaItem[]
  filteredIdentidades: IdentidadItem[]
  filteredMandatos: MandatoItem[]
  toneFor: (value: string) => Tone
  isSubmitting: boolean
  startEditCuenta: (row: CuentaItem) => void
  startEditMandato: (row: MandatoItem) => void
  goToCuentaConciliacion: (cuentaId: number, numeroCuenta: string) => void
  goToMandatoContext: (mandatoId: number) => void
}) {
  return (
    <>
      {!canEditOperacion ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Operación.</div> : null}
      <section className="form-grid">
        <section className="panel">
          <div className="section-heading"><div><h2>{editingCuentaId ? 'Editar cuenta' : 'Alta rápida de cuenta'}</h2><p>Cuenta recaudadora con owner bancario explícito.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateCuenta}>
            <input placeholder="Institución" value={cuentaDraft.institucion} onChange={(event) => setCuentaDraft((current) => ({ ...current, institucion: event.target.value }))} />
            <input placeholder="Número de cuenta" value={cuentaDraft.numero_cuenta} onChange={(event) => setCuentaDraft((current) => ({ ...current, numero_cuenta: event.target.value }))} />
            <input placeholder="Titular" value={cuentaDraft.titular_nombre} onChange={(event) => setCuentaDraft((current) => ({ ...current, titular_nombre: event.target.value }))} />
            <input placeholder="RUT titular" value={cuentaDraft.titular_rut} onChange={(event) => setCuentaDraft((current) => ({ ...current, titular_rut: event.target.value }))} />
            <select value={cuentaDraft.tipo_cuenta} onChange={(event) => setCuentaDraft((current) => ({ ...current, tipo_cuenta: event.target.value }))}><option value="corriente">Corriente</option><option value="vista">Vista</option><option value="ahorro">Ahorro</option></select>
            <select value={cuentaDraft.moneda_operativa} onChange={(event) => setCuentaDraft((current) => ({ ...current, moneda_operativa: event.target.value }))}><option value="CLP">CLP</option><option value="UF">UF</option></select>
            <select value={cuentaDraft.estado_operativo} onChange={(event) => setCuentaDraft((current) => ({ ...current, estado_operativo: event.target.value }))}><option value="activa">Activa</option><option value="pausada">Pausada</option><option value="inactiva">Inactiva</option></select>
            <select value={`${cuentaDraft.owner_tipo}:${cuentaDraft.owner_id}`} onChange={(event) => { const [tipo, id] = event.target.value.split(':'); setCuentaDraft((current) => ({ ...current, owner_tipo: tipo, owner_id: id || '' })) }}>
              <option value="">Selecciona owner</option>
              {simpleOwners.map((owner) => <option key={`${owner.tipo}:${owner.id}`} value={`${owner.tipo}:${owner.id}`}>{owner.label} · {owner.tipo}</option>)}
            </select>
            <div className="inline-actions">
              <button type="submit" className="button-primary" disabled={isSubmitting || !canEditOperacion || !cuentaDraft.owner_id}>{editingCuentaId ? 'Guardar cambios' : 'Guardar cuenta'}</button>
              {editingCuentaId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditCuenta}>Cancelar</button> : null}
            </div>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>{editingMandatoId ? 'Editar mandato' : 'Alta rápida de mandato'}</h2><p>Separación explícita entre propietario, administrador, recaudador y facturadora.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateMandato}>
            <select value={mandatoDraft.propiedad_id} onChange={(event) => setMandatoDraft((current) => ({ ...current, propiedad_id: event.target.value }))}>
              <option value="">Selecciona propiedad</option>
              {propiedades.map((item) => <option key={item.id} value={item.id}>{item.codigo_propiedad} · {item.direccion}</option>)}
            </select>
            <select value={`${mandatoDraft.propietario_tipo}:${mandatoDraft.propietario_id}`} onChange={(event) => { const [tipo, id] = event.target.value.split(':'); setMandatoDraft((current) => ({ ...current, propietario_tipo: tipo, propietario_id: id || '' })) }}>
              <option value="">Selecciona propietario</option>
              {patrimonioOwners.map((owner) => <option key={`prop-${owner.tipo}:${owner.id}`} value={`${owner.tipo}:${owner.id}`}>{owner.label} · {owner.tipo}</option>)}
            </select>
            <select value={`${mandatoDraft.administrador_operativo_tipo}:${mandatoDraft.administrador_operativo_id}`} onChange={(event) => { const [tipo, id] = event.target.value.split(':'); setMandatoDraft((current) => ({ ...current, administrador_operativo_tipo: tipo, administrador_operativo_id: id || '' })) }}>
              <option value="">Selecciona administrador</option>
              {simpleOwners.map((owner) => <option key={`admin-${owner.tipo}:${owner.id}`} value={`${owner.tipo}:${owner.id}`}>{owner.label} · {owner.tipo}</option>)}
            </select>
            <select value={`${mandatoDraft.recaudador_tipo}:${mandatoDraft.recaudador_id}`} onChange={(event) => { const [tipo, id] = event.target.value.split(':'); setMandatoDraft((current) => ({ ...current, recaudador_tipo: tipo, recaudador_id: id || '' })) }}>
              <option value="">Selecciona recaudador</option>
              {simpleOwners.map((owner) => <option key={`rec-${owner.tipo}:${owner.id}`} value={`${owner.tipo}:${owner.id}`}>{owner.label} · {owner.tipo}</option>)}
            </select>
            <select value={mandatoDraft.entidad_facturadora_id} onChange={(event) => setMandatoDraft((current) => ({ ...current, entidad_facturadora_id: event.target.value }))}>
              <option value="">Sin facturadora</option>
              {simpleOwners.filter((owner) => owner.tipo === 'empresa').map((owner) => <option key={`fact-${owner.id}`} value={owner.id}>{owner.label}</option>)}
            </select>
            <select value={mandatoDraft.cuenta_recaudadora_id} onChange={(event) => setMandatoDraft((current) => ({ ...current, cuenta_recaudadora_id: event.target.value }))}>
              <option value="">Selecciona cuenta</option>
              {cuentas.map((item) => <option key={item.id} value={item.id}>{item.numero_cuenta} · {item.owner_display}</option>)}
            </select>
            <input placeholder="Tipo relación operativa" value={mandatoDraft.tipo_relacion_operativa} onChange={(event) => setMandatoDraft((current) => ({ ...current, tipo_relacion_operativa: event.target.value }))} />
            <input type="date" value={mandatoDraft.vigencia_desde} onChange={(event) => setMandatoDraft((current) => ({ ...current, vigencia_desde: event.target.value }))} />
            <select value={mandatoDraft.estado} onChange={(event) => setMandatoDraft((current) => ({ ...current, estado: event.target.value }))}><option value="activa">Activa</option><option value="inactiva">Inactiva</option><option value="borrador">Borrador</option></select>
            <label className="checkbox-row"><input type="checkbox" checked={mandatoDraft.autoriza_recaudacion} onChange={(event) => setMandatoDraft((current) => ({ ...current, autoriza_recaudacion: event.target.checked }))} />Autoriza recaudación</label>
            <label className="checkbox-row"><input type="checkbox" checked={mandatoDraft.autoriza_facturacion} onChange={(event) => setMandatoDraft((current) => ({ ...current, autoriza_facturacion: event.target.checked }))} />Autoriza facturación</label>
            <label className="checkbox-row"><input type="checkbox" checked={mandatoDraft.autoriza_comunicacion} onChange={(event) => setMandatoDraft((current) => ({ ...current, autoriza_comunicacion: event.target.checked }))} />Autoriza comunicación</label>
            <div className="inline-actions">
              <button type="submit" className="button-primary" disabled={isSubmitting || !canEditOperacion || !mandatoDraft.propiedad_id || !mandatoDraft.propietario_id || !mandatoDraft.administrador_operativo_id || !mandatoDraft.recaudador_id || !mandatoDraft.cuenta_recaudadora_id}>{editingMandatoId ? 'Guardar cambios' : 'Guardar mandato'}</button>
              {editingMandatoId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditMandato}>Cancelar</button> : null}
            </div>
          </form>
        </section>
      </section>

      <TableBlock title="Cuentas recaudadoras" subtitle="Ownership bancario operativo." rows={filteredCuentas} empty="No hay cuentas para este filtro." columns={[
        { label: 'Cuenta', render: (row) => `${row.institucion} · ${row.numero_cuenta}` },
        { label: 'Owner', render: (row) => `${row.owner_display} · ${row.owner_tipo}` },
        { label: 'Moneda', render: (row) => row.moneda_operativa },
        { label: 'Estado', render: (row) => <Badge label={row.estado_operativo} tone={toneFor(row.estado_operativo)} /> },
        { label: 'Editar', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditCuenta(row)}>Editar</button> },
        { label: 'Siguiente paso', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => goToCuentaConciliacion(row.id, row.numero_cuenta)}>Conectar banco</button> },
      ]} />
      <TableBlock title="Identidades de envío" subtitle="Canales autorizados para salida." rows={filteredIdentidades} empty="No hay identidades para este filtro." columns={[
        { label: 'Remitente', render: (row) => row.remitente_visible },
        { label: 'Canal', render: (row) => row.canal.replaceAll('_', ' ') },
        { label: 'Destino', render: (row) => row.direccion_o_numero },
        { label: 'Owner', render: (row) => `${row.owner_display} · ${row.owner_tipo}` },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />
      <TableBlock title="Mandatos operativos" subtitle="Separación entre propietario, administrador, recaudador y facturadora." rows={filteredMandatos} empty="No hay mandatos para este filtro." columns={[
        { label: 'Propiedad', render: (row) => row.propiedad_codigo },
        { label: 'Propietario', render: (row) => row.propietario_display },
        { label: 'Administrador', render: (row) => row.administrador_operativo_display },
        { label: 'Recaudador', render: (row) => row.recaudador_display },
        { label: 'Facturadora', render: (row) => row.entidad_facturadora_display || 'Sin facturadora' },
        { label: 'Cuenta', render: (row) => row.cuenta_recaudadora_display },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Editar', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditMandato(row)}>Editar</button> },
        { label: 'Siguiente paso', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => goToMandatoContext(row.id)}>Crear contrato</button> },
      ]} />
    </>
  )
}
