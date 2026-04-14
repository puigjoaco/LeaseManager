import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock, count } from '../shared'

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'

type ValorUFItem = { id: number; fecha: string; valor: string; source_key: string }
type AjusteContratoItem = { id: number; contrato: number; tipo_ajuste: string; monto: string; moneda: string; mes_inicio: string; mes_fin: string; activo: boolean }
type PagoMensualItem = { id: number; contrato: number; mes: number; anio: number; monto_facturable_clp: string; monto_calculado_clp: string; monto_pagado_clp: string; estado_pago: string }
type GarantiaItem = { id: number; contrato: number; monto_pactado: string; monto_recibido: string; saldo_vigente: string; estado_garantia: string }
type HistorialGarantiaItem = { id: number; contrato_id: number; tipo_movimiento: string; monto_clp: string; fecha: string; justificacion: string }
type EstadoCuentaItem = { id: number; arrendatario: number; score_pago: number | null; resumen_operativo: { pagos_abiertos?: number; pagos_atrasados?: number; saldo_total_clp?: string } }
type ContratoItem = { id: number; codigo_contrato: string }
type ArrendatarioItem = { id: number; nombre_razon_social: string }

type UfDraft = { fecha: string; valor: string; source_key: string }
type AjusteDraft = { contrato: string; tipo_ajuste: string; monto: string; moneda: string; mes_inicio: string; mes_fin: string; justificacion: string; activo: boolean }
type PagoDraft = { contrato_id: string; anio: string; mes: string }
type GarantiaDraft = { contrato: string; monto_pactado: string }
type GarantiaMovimientoDraft = { garantiaId: string; tipo_movimiento: string; monto_clp: string; fecha: string; justificacion: string }
type EstadoCuentaDraft = { arrendatario_id: string }

export function CobranzaWorkspace({
  canEditCobranza,
  ufDraft,
  setUfDraft,
  handleCreateUf,
  ajusteDraft,
  setAjusteDraft,
  handleCreateAjuste,
  pagoDraft,
  setPagoDraft,
  handleGeneratePago,
  garantiaDraft,
  setGarantiaDraft,
  handleCreateGarantia,
  garantiaMovimientoDraft,
  setGarantiaMovimientoDraft,
  handleGarantiaMovimiento,
  estadoCuentaDraft,
  setEstadoCuentaDraft,
  handleRebuildEstadoCuenta,
  contratos,
  garantias,
  arrendatarios,
  filteredValoresUf,
  filteredAjustes,
  filteredPagos,
  filteredGarantias,
  filteredHistorialGarantias,
  filteredEstadosCuenta,
  contratoById,
  arrendatarioById,
  toneFor,
  isSubmitting,
  isLoading,
  navigateToConciliacion,
  goToPagoContext,
  canOpenSii,
}: {
  canEditCobranza: boolean
  ufDraft: UfDraft
  setUfDraft: Dispatch<SetStateAction<UfDraft>>
  handleCreateUf: (event: FormEvent<HTMLFormElement>) => Promise<void>
  ajusteDraft: AjusteDraft
  setAjusteDraft: Dispatch<SetStateAction<AjusteDraft>>
  handleCreateAjuste: (event: FormEvent<HTMLFormElement>) => Promise<void>
  pagoDraft: PagoDraft
  setPagoDraft: Dispatch<SetStateAction<PagoDraft>>
  handleGeneratePago: (event: FormEvent<HTMLFormElement>) => Promise<void>
  garantiaDraft: GarantiaDraft
  setGarantiaDraft: Dispatch<SetStateAction<GarantiaDraft>>
  handleCreateGarantia: (event: FormEvent<HTMLFormElement>) => Promise<void>
  garantiaMovimientoDraft: GarantiaMovimientoDraft
  setGarantiaMovimientoDraft: Dispatch<SetStateAction<GarantiaMovimientoDraft>>
  handleGarantiaMovimiento: (event: FormEvent<HTMLFormElement>) => Promise<void>
  estadoCuentaDraft: EstadoCuentaDraft
  setEstadoCuentaDraft: Dispatch<SetStateAction<EstadoCuentaDraft>>
  handleRebuildEstadoCuenta: (event: FormEvent<HTMLFormElement>) => Promise<void>
  contratos: ContratoItem[]
  garantias: GarantiaItem[]
  arrendatarios: ArrendatarioItem[]
  filteredValoresUf: ValorUFItem[]
  filteredAjustes: AjusteContratoItem[]
  filteredPagos: PagoMensualItem[]
  filteredGarantias: GarantiaItem[]
  filteredHistorialGarantias: HistorialGarantiaItem[]
  filteredEstadosCuenta: EstadoCuentaItem[]
  contratoById: ReadonlyMap<number, ContratoItem>
  arrendatarioById: ReadonlyMap<number, ArrendatarioItem>
  toneFor: (value: string) => Tone
  isSubmitting: boolean
  isLoading: boolean
  navigateToConciliacion: (row: PagoMensualItem) => void
  goToPagoContext: (pagoId: number) => void
  canOpenSii: boolean
}) {
  return (
    <>
      {!canEditCobranza ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Cobranza.</div> : null}
      <section className="form-grid">
        <section className="panel">
          <div className="section-heading"><div><h2>Valor UF</h2><p>Registro diario mínimo para contratos en UF.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateUf}>
            <input type="date" value={ufDraft.fecha} onChange={(event) => setUfDraft((current) => ({ ...current, fecha: event.target.value }))} />
            <input placeholder="Valor UF" value={ufDraft.valor} onChange={(event) => setUfDraft((current) => ({ ...current, valor: event.target.value }))} />
            <input placeholder="Source key" value={ufDraft.source_key} onChange={(event) => setUfDraft((current) => ({ ...current, source_key: event.target.value }))} />
            <button type="submit" className="button-primary" disabled={isSubmitting || !canEditCobranza || !ufDraft.valor}>Guardar UF</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Ajuste de contrato</h2><p>Cargos o descuentos vigentes por rango mensual.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateAjuste}>
            <select value={ajusteDraft.contrato} onChange={(event) => setAjusteDraft((current) => ({ ...current, contrato: event.target.value }))}>
              <option value="">Selecciona contrato</option>
              {contratos.map((item) => <option key={item.id} value={item.id}>{item.codigo_contrato}</option>)}
            </select>
            <input placeholder="Tipo ajuste" value={ajusteDraft.tipo_ajuste} onChange={(event) => setAjusteDraft((current) => ({ ...current, tipo_ajuste: event.target.value }))} />
            <input placeholder="Monto" value={ajusteDraft.monto} onChange={(event) => setAjusteDraft((current) => ({ ...current, monto: event.target.value }))} />
            <select value={ajusteDraft.moneda} onChange={(event) => setAjusteDraft((current) => ({ ...current, moneda: event.target.value }))}>
              <option value="CLP">CLP</option>
              <option value="UF">UF</option>
            </select>
            <input type="date" value={ajusteDraft.mes_inicio} onChange={(event) => setAjusteDraft((current) => ({ ...current, mes_inicio: event.target.value }))} />
            <input type="date" value={ajusteDraft.mes_fin} onChange={(event) => setAjusteDraft((current) => ({ ...current, mes_fin: event.target.value }))} />
            <input placeholder="Justificación" value={ajusteDraft.justificacion} onChange={(event) => setAjusteDraft((current) => ({ ...current, justificacion: event.target.value }))} />
            <label className="checkbox-row"><input type="checkbox" checked={ajusteDraft.activo} onChange={(event) => setAjusteDraft((current) => ({ ...current, activo: event.target.checked }))} />Activo</label>
            <button type="submit" className="button-primary" disabled={isSubmitting || !canEditCobranza || !ajusteDraft.contrato || !ajusteDraft.monto}>Guardar ajuste</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Generar pago mensual</h2><p>Usa el período vigente, UF y ajustes activos del contrato.</p></div></div>
          <form className="entity-form" onSubmit={handleGeneratePago}>
            <select value={pagoDraft.contrato_id} onChange={(event) => setPagoDraft((current) => ({ ...current, contrato_id: event.target.value }))}>
              <option value="">Selecciona contrato</option>
              {contratos.map((item) => <option key={item.id} value={item.id}>{item.codigo_contrato}</option>)}
            </select>
            <input placeholder="Año" value={pagoDraft.anio} onChange={(event) => setPagoDraft((current) => ({ ...current, anio: event.target.value }))} />
            <input placeholder="Mes" value={pagoDraft.mes} onChange={(event) => setPagoDraft((current) => ({ ...current, mes: event.target.value }))} />
            <button type="submit" className="button-primary" disabled={isSubmitting || !canEditCobranza || !pagoDraft.contrato_id}>Generar pago</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Garantía contractual</h2><p>Alta de garantía y movimientos principales.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateGarantia}>
            <select value={garantiaDraft.contrato} onChange={(event) => setGarantiaDraft((current) => ({ ...current, contrato: event.target.value }))}>
              <option value="">Selecciona contrato</option>
              {contratos.map((item) => <option key={item.id} value={item.id}>{item.codigo_contrato}</option>)}
            </select>
            <input placeholder="Monto pactado" value={garantiaDraft.monto_pactado} onChange={(event) => setGarantiaDraft((current) => ({ ...current, monto_pactado: event.target.value }))} />
            <button type="submit" className="button-primary" disabled={isSubmitting || !canEditCobranza || !garantiaDraft.contrato || !garantiaDraft.monto_pactado}>Guardar garantía</button>
          </form>
          <form className="entity-form subform" onSubmit={handleGarantiaMovimiento}>
            <select value={garantiaMovimientoDraft.garantiaId} onChange={(event) => setGarantiaMovimientoDraft((current) => ({ ...current, garantiaId: event.target.value }))}>
              <option value="">Selecciona garantía</option>
              {garantias.map((item) => <option key={item.id} value={item.id}>{contratoById.get(item.contrato)?.codigo_contrato || item.contrato}</option>)}
            </select>
            <select value={garantiaMovimientoDraft.tipo_movimiento} onChange={(event) => setGarantiaMovimientoDraft((current) => ({ ...current, tipo_movimiento: event.target.value }))}>
              <option value="deposito">Depósito</option>
              <option value="devolucion_parcial">Devolución parcial</option>
              <option value="devolucion_total">Devolución total</option>
              <option value="retencion_parcial">Retención parcial</option>
              <option value="retencion_total">Retención total</option>
            </select>
            <input placeholder="Monto movimiento" value={garantiaMovimientoDraft.monto_clp} onChange={(event) => setGarantiaMovimientoDraft((current) => ({ ...current, monto_clp: event.target.value }))} />
            <input type="date" value={garantiaMovimientoDraft.fecha} onChange={(event) => setGarantiaMovimientoDraft((current) => ({ ...current, fecha: event.target.value }))} />
            <input placeholder="Justificación" value={garantiaMovimientoDraft.justificacion} onChange={(event) => setGarantiaMovimientoDraft((current) => ({ ...current, justificacion: event.target.value }))} />
            <button type="submit" className="button-secondary" disabled={isSubmitting || !canEditCobranza || !garantiaMovimientoDraft.garantiaId || !garantiaMovimientoDraft.monto_clp}>Registrar movimiento</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Estado de cuenta</h2><p>Reconstrucción del resumen operativo por arrendatario.</p></div></div>
          <form className="entity-form" onSubmit={handleRebuildEstadoCuenta}>
            <select value={estadoCuentaDraft.arrendatario_id} onChange={(event) => setEstadoCuentaDraft({ arrendatario_id: event.target.value })}>
              <option value="">Selecciona arrendatario</option>
              {arrendatarios.map((item) => <option key={item.id} value={item.id}>{item.nombre_razon_social}</option>)}
            </select>
            <button type="submit" className="button-primary" disabled={isSubmitting || !canEditCobranza || !estadoCuentaDraft.arrendatario_id}>Recalcular estado</button>
          </form>
        </section>
      </section>

      <TableBlock title="Valores UF" subtitle="Fuente de conversión mensual para contratos en UF." rows={filteredValoresUf} empty="No hay valores UF para este filtro." isLoading={isLoading} loadingLabel="Cargando cobranza..." columns={[
        { label: 'Fecha', render: (row) => row.fecha },
        { label: 'Valor', render: (row) => row.valor },
        { label: 'Source', render: (row) => row.source_key },
      ]} />
      <TableBlock title="Ajustes de contrato" subtitle="Ajustes activos y programados por contrato." rows={filteredAjustes} empty="No hay ajustes para este filtro." isLoading={isLoading} loadingLabel="Cargando cobranza..." columns={[
        { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
        { label: 'Tipo', render: (row) => row.tipo_ajuste },
        { label: 'Monto', render: (row) => `${row.monto} ${row.moneda}` },
        { label: 'Rango', render: (row) => `${row.mes_inicio} → ${row.mes_fin}` },
        { label: 'Activo', render: (row) => <Badge label={row.activo ? 'activo' : 'inactivo'} tone={row.activo ? 'positive' : 'danger'} /> },
      ]} />
      <TableBlock title="Pagos mensuales" subtitle="Cobro calculado, estado y distribución económica." rows={filteredPagos} empty="No hay pagos para este filtro." isLoading={isLoading} loadingLabel="Cargando cobranza..." columns={[
        { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
        { label: 'Periodo', render: (row) => `${row.mes}/${row.anio}` },
        { label: 'Facturable', render: (row) => row.monto_facturable_clp },
        { label: 'Calculado', render: (row) => row.monto_calculado_clp },
        { label: 'Pagado', render: (row) => row.monto_pagado_clp },
        { label: 'Estado', render: (row) => <Badge label={row.estado_pago} tone={toneFor(row.estado_pago)} /> },
        { label: 'Siguiente paso', render: (row) => <div className="inline-actions"><button type="button" className="button-ghost inline-action" onClick={() => navigateToConciliacion(row)}>Conciliar</button>{canOpenSii ? <button type="button" className="button-ghost inline-action" onClick={() => goToPagoContext(row.id)}>DTE</button> : null}</div> },
      ]} />
      <TableBlock title="Garantías" subtitle="Saldos y estado actual de cada contrato." rows={filteredGarantias} empty="No hay garantías para este filtro." isLoading={isLoading} loadingLabel="Cargando cobranza..." columns={[
        { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
        { label: 'Pactado', render: (row) => row.monto_pactado },
        { label: 'Recibido', render: (row) => row.monto_recibido },
        { label: 'Saldo', render: (row) => row.saldo_vigente },
        { label: 'Estado', render: (row) => <Badge label={row.estado_garantia} tone={toneFor(row.estado_garantia)} /> },
      ]} />
      <TableBlock title="Historial de garantías" subtitle="Movimientos auditables sobre depósitos, devoluciones y retenciones." rows={filteredHistorialGarantias} empty="No hay movimientos de garantía para este filtro." isLoading={isLoading} loadingLabel="Cargando cobranza..." columns={[
        { label: 'Contrato', render: (row) => contratoById.get(row.contrato_id)?.codigo_contrato || row.contrato_id },
        { label: 'Tipo', render: (row) => row.tipo_movimiento },
        { label: 'Monto', render: (row) => row.monto_clp },
        { label: 'Fecha', render: (row) => row.fecha },
        { label: 'Justificación', render: (row) => row.justificacion || 'Sin nota' },
      ]} />
      <TableBlock title="Estado de cuenta" subtitle="Resumen operativo consolidado por arrendatario." rows={filteredEstadosCuenta} empty="No hay estados de cuenta para este filtro." isLoading={isLoading} loadingLabel="Cargando cobranza..." columns={[
        { label: 'Arrendatario', render: (row) => arrendatarioById.get(row.arrendatario)?.nombre_razon_social || row.arrendatario },
        { label: 'Pagos abiertos', render: (row) => count(row.resumen_operativo.pagos_abiertos) },
        { label: 'Pagos atrasados', render: (row) => count(row.resumen_operativo.pagos_atrasados) },
        { label: 'Saldo total', render: (row) => row.resumen_operativo.saldo_total_clp || '0.00' },
        { label: 'Score', render: (row) => row.score_pago ?? 'Sin score' },
      ]} />
    </>
  )
}
