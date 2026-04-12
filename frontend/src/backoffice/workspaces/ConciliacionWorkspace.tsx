import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock } from '../shared'

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'

type CuentaItem = { id: number; numero_cuenta: string; owner_display: string }
type ConexionBancariaItem = { id: number; cuenta_recaudadora: number; provider_key: string; credencial_ref: string; scope: string; estado_conexion: string }
type MovimientoBancarioItem = { id: number; fecha_movimiento: string; tipo_movimiento: string; monto: string; descripcion_origen: string; referencia: string; estado_conciliacion: string }
type IngresoDesconocidoItem = { id: number; cuenta_recaudadora: number; fecha_movimiento: string; monto: string; descripcion_origen: string; estado: string; sugerencia_asistida: { payment_candidate_ids?: number[] } }

type ConexionDraft = {
  cuenta_recaudadora: string
  provider_key: string
  credencial_ref: string
  scope: string
  expira_en: string
  estado_conexion: string
  primaria_movimientos: boolean
  primaria_saldos: boolean
  primaria_conectividad: boolean
}

type MovimientoDraft = {
  conexion_bancaria: string
  fecha_movimiento: string
  tipo_movimiento: string
  monto: string
  descripcion_origen: string
  numero_documento: string
  saldo_reportado: string
  referencia: string
  transaction_id_banco: string
  notas_admin: string
}

export function ConciliacionWorkspace({
  canEditConciliacion,
  conexionDraft,
  setConexionDraft,
  handleCreateConexion,
  movimientoDraft,
  setMovimientoDraft,
  handleCreateMovimiento,
  filteredConexiones,
  filteredMovimientos,
  filteredIngresos,
  cuentas,
  conexionesBancarias,
  cuentaById,
  toneFor,
  isSubmitting,
  handleRetryMatch,
}: {
  canEditConciliacion: boolean
  conexionDraft: ConexionDraft
  setConexionDraft: Dispatch<SetStateAction<ConexionDraft>>
  handleCreateConexion: (event: FormEvent<HTMLFormElement>) => Promise<void>
  movimientoDraft: MovimientoDraft
  setMovimientoDraft: Dispatch<SetStateAction<MovimientoDraft>>
  handleCreateMovimiento: (event: FormEvent<HTMLFormElement>) => Promise<void>
  filteredConexiones: ConexionBancariaItem[]
  filteredMovimientos: MovimientoBancarioItem[]
  filteredIngresos: IngresoDesconocidoItem[]
  cuentas: CuentaItem[]
  conexionesBancarias: ConexionBancariaItem[]
  cuentaById: ReadonlyMap<number, CuentaItem>
  toneFor: (value: string) => Tone
  isSubmitting: boolean
  handleRetryMatch: (movimientoId: number) => Promise<void>
}) {
  return (
    <>
      {!canEditConciliacion ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Conciliación.</div> : null}
      <section className="form-grid">
        <section className="panel">
          <div className="section-heading"><div><h2>Conexión bancaria</h2><p>Conecta una cuenta recaudadora al provider operativo.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateConexion}>
            <select value={conexionDraft.cuenta_recaudadora} onChange={(event) => setConexionDraft((current) => ({ ...current, cuenta_recaudadora: event.target.value }))}>
              <option value="">Selecciona cuenta</option>
              {cuentas.map((item) => <option key={item.id} value={item.id}>{item.numero_cuenta} · {item.owner_display}</option>)}
            </select>
            <input placeholder="Provider key" value={conexionDraft.provider_key} onChange={(event) => setConexionDraft((current) => ({ ...current, provider_key: event.target.value }))} />
            <input placeholder="Credencial ref" value={conexionDraft.credencial_ref} onChange={(event) => setConexionDraft((current) => ({ ...current, credencial_ref: event.target.value }))} />
            <input placeholder="Scope" value={conexionDraft.scope} onChange={(event) => setConexionDraft((current) => ({ ...current, scope: event.target.value }))} />
            <input type="datetime-local" value={conexionDraft.expira_en} onChange={(event) => setConexionDraft((current) => ({ ...current, expira_en: event.target.value }))} />
            <select value={conexionDraft.estado_conexion} onChange={(event) => setConexionDraft((current) => ({ ...current, estado_conexion: event.target.value }))}>
              <option value="verificando">Verificando</option>
              <option value="activa">Activa</option>
              <option value="pausada">Pausada</option>
              <option value="inactiva">Inactiva</option>
            </select>
            <label className="checkbox-row"><input type="checkbox" checked={conexionDraft.primaria_movimientos} onChange={(event) => setConexionDraft((current) => ({ ...current, primaria_movimientos: event.target.checked }))} />Primaria movimientos</label>
            <label className="checkbox-row"><input type="checkbox" checked={conexionDraft.primaria_saldos} onChange={(event) => setConexionDraft((current) => ({ ...current, primaria_saldos: event.target.checked }))} />Primaria saldos</label>
            <label className="checkbox-row"><input type="checkbox" checked={conexionDraft.primaria_conectividad} onChange={(event) => setConexionDraft((current) => ({ ...current, primaria_conectividad: event.target.checked }))} />Primaria conectividad</label>
            <button type="submit" className="button-primary" disabled={isSubmitting || !canEditConciliacion || !conexionDraft.cuenta_recaudadora}>Guardar conexión</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Movimiento bancario</h2><p>Ingesta manual para probar match exacto, ingreso desconocido y cargo.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateMovimiento}>
            <select value={movimientoDraft.conexion_bancaria} onChange={(event) => setMovimientoDraft((current) => ({ ...current, conexion_bancaria: event.target.value }))}>
              <option value="">Selecciona conexión</option>
              {conexionesBancarias.map((item) => <option key={item.id} value={item.id}>{item.provider_key} · {cuentaById.get(item.cuenta_recaudadora)?.numero_cuenta || item.cuenta_recaudadora}</option>)}
            </select>
            <input type="date" value={movimientoDraft.fecha_movimiento} onChange={(event) => setMovimientoDraft((current) => ({ ...current, fecha_movimiento: event.target.value }))} />
            <select value={movimientoDraft.tipo_movimiento} onChange={(event) => setMovimientoDraft((current) => ({ ...current, tipo_movimiento: event.target.value }))}>
              <option value="abono">Abono</option>
              <option value="cargo">Cargo</option>
            </select>
            <input placeholder="Monto" value={movimientoDraft.monto} onChange={(event) => setMovimientoDraft((current) => ({ ...current, monto: event.target.value }))} />
            <input placeholder="Descripción origen" value={movimientoDraft.descripcion_origen} onChange={(event) => setMovimientoDraft((current) => ({ ...current, descripcion_origen: event.target.value }))} />
            <input placeholder="Número documento" value={movimientoDraft.numero_documento} onChange={(event) => setMovimientoDraft((current) => ({ ...current, numero_documento: event.target.value }))} />
            <input placeholder="Saldo reportado" value={movimientoDraft.saldo_reportado} onChange={(event) => setMovimientoDraft((current) => ({ ...current, saldo_reportado: event.target.value }))} />
            <input placeholder="Referencia" value={movimientoDraft.referencia} onChange={(event) => setMovimientoDraft((current) => ({ ...current, referencia: event.target.value }))} />
            <input placeholder="Transaction ID banco" value={movimientoDraft.transaction_id_banco} onChange={(event) => setMovimientoDraft((current) => ({ ...current, transaction_id_banco: event.target.value }))} />
            <input placeholder="Notas admin" value={movimientoDraft.notas_admin} onChange={(event) => setMovimientoDraft((current) => ({ ...current, notas_admin: event.target.value }))} />
            <button type="submit" className="button-primary" disabled={isSubmitting || !canEditConciliacion || !movimientoDraft.conexion_bancaria || !movimientoDraft.monto || !movimientoDraft.descripcion_origen}>Guardar movimiento</button>
          </form>
        </section>
      </section>

      <TableBlock title="Conexiones bancarias" subtitle="Providers activos por cuenta recaudadora." rows={filteredConexiones} empty="No hay conexiones bancarias para este filtro." columns={[
        { label: 'Cuenta', render: (row) => cuentaById.get(row.cuenta_recaudadora)?.numero_cuenta || row.cuenta_recaudadora },
        { label: 'Provider', render: (row) => row.provider_key },
        { label: 'Credencial', render: (row) => row.credencial_ref },
        { label: 'Scope', render: (row) => row.scope || 'Sin scope' },
        { label: 'Estado', render: (row) => <Badge label={row.estado_conexion} tone={toneFor(row.estado_conexion)} /> },
      ]} />
      <TableBlock title="Movimientos bancarios" subtitle="Entrada importada y resultado de conciliación." rows={filteredMovimientos} empty="No hay movimientos para este filtro." columns={[
        { label: 'Fecha', render: (row) => row.fecha_movimiento },
        { label: 'Tipo', render: (row) => row.tipo_movimiento },
        { label: 'Monto', render: (row) => row.monto },
        { label: 'Descripción', render: (row) => row.descripcion_origen },
        { label: 'Referencia', render: (row) => row.referencia || 'Sin referencia' },
        { label: 'Estado', render: (row) => <Badge label={row.estado_conciliacion} tone={toneFor(row.estado_conciliacion)} /> },
        { label: 'Acción', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => void handleRetryMatch(row.id)} disabled={isSubmitting || !canEditConciliacion}>Reintentar match</button> },
      ]} />
      <TableBlock title="Ingresos desconocidos" subtitle="Abonos sin match exacto que requieren revisión." rows={filteredIngresos} empty="No hay ingresos desconocidos para este filtro." columns={[
        { label: 'Fecha', render: (row) => row.fecha_movimiento },
        { label: 'Monto', render: (row) => row.monto },
        { label: 'Cuenta', render: (row) => cuentaById.get(row.cuenta_recaudadora)?.numero_cuenta || row.cuenta_recaudadora },
        { label: 'Descripción', render: (row) => row.descripcion_origen },
        { label: 'Sugerencia', render: (row) => row.sugerencia_asistida?.payment_candidate_ids?.length ? `Pagos candidatos: ${row.sugerencia_asistida.payment_candidate_ids.join(', ')}` : 'Sin sugerencia' },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />
    </>
  )
}
