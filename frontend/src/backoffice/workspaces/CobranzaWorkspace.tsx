import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock } from '../shared'
import { count } from '../shared-utils'

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'

type ValorUFItem = { id: number; fecha: string; valor: string; source_key: string; evidencia_ref: string; motivo_carga: string; responsable_ref: string }
type AjusteContratoItem = { id: number; contrato: number; tipo_ajuste: string; monto: string; moneda: string; mes_inicio: string; mes_fin: string; activo: boolean }
type DistribucionPagoItem = { id: number; beneficiario_tipo: string; beneficiario_id: number; beneficiario_display: string; porcentaje_snapshot: string; monto_devengado_clp: string; monto_facturable_clp: string; monto_conciliado_clp: string; requiere_dte: boolean }
type PagoMensualItem = { id: number; contrato: number; mes: number; anio: number; monto_facturable_clp: string; monto_calculado_clp: string; monto_efecto_codigo_efectivo_clp: string; moneda_calculo: string; uf_fecha_usada: string | null; uf_valor_usado: string | null; uf_source_key: string; monto_pagado_clp: string; fecha_vencimiento: string; fecha_pago_webpay: string | null; estado_pago: string; dias_mora: number; resolucion_pago_excepcional_ref: string; resolucion_pago_excepcional_motivo: string; distribuciones_detail: DistribucionPagoItem[] }
type GateCobroExternoItem = { id: number; capacidad_key: string; provider_key: string; estado_gate: string; restricciones_operativas: Record<string, unknown>; evidencia_ref: string }
type IntentoPagoWebPayItem = { id: number; pago_mensual: number; gate_cobro: number; provider_key: string; monto_clp_snapshot: string; buy_order: string; session_id?: string; return_url_ref?: string; estado: string; motivo_bloqueo: string; external_ref: string; fecha_pago_webpay: string | null; confirmado_at?: string | null; provider_payload?: Record<string, unknown> }
type RepactacionDeudaItem = { id: number; arrendatario: number; contrato_origen: number; deuda_total_original: string; cantidad_cuotas: number; monto_cuota: string; saldo_pendiente: string; estado: string; excepcion_parcial_ref: string; excepcion_parcial_motivo: string; es_repactacion_parcial: boolean; tiene_excepcion_parcial: boolean }
type CodigoCobroResidualItem = { id: number; referencia_visible: string; arrendatario: number; contrato_origen: number; saldo_actual: string; estado: string; fecha_activacion: string }
type GarantiaItem = { id: number; contrato: number; monto_pactado: string; monto_recibido: string; saldo_vigente: string; brecha_garantia_clp: string; exceso_garantia_clp: string; garantia_incompleta: boolean; garantia_parcial_aceptada: boolean; aceptacion_parcial_ref: string; resolucion_exceso_garantia: string; resolucion_exceso_garantia_ref: string; resolucion_exceso_garantia_motivo: string; tiene_resolucion_exceso_garantia: boolean; estado_garantia: string }
type HistorialGarantiaItem = { id: number; contrato_id: number; tipo_movimiento: string; monto_clp: string; fecha: string; justificacion: string }
type EstadoCuentaItem = {
  id: number
  arrendatario: number
  score_pago: number | null
  observaciones: string
  resumen_operativo: {
    pagos_abiertos?: number
    pagos_atrasados?: number
    repactaciones_activas?: number
    cobranzas_residuales_activas?: number
    score_pago_porcentaje?: number | null
    score_meses_evaluados?: number
    score_pagos_en_plazo?: number
    score_pagos_fuera_plazo?: number
    score_meses_sin_registro_operativo?: number
    saldo_total_clp?: string
  }
}
type ContratoItem = { id: number; codigo_contrato: string }
type ArrendatarioItem = { id: number; nombre_razon_social: string }

type UfDraft = { fecha: string; valor: string; source_key: string; evidencia_ref: string; motivo_carga: string; responsable_ref: string }
type AjusteDraft = { contrato: string; tipo_ajuste: string; monto: string; moneda: string; mes_inicio: string; mes_fin: string; justificacion: string; activo: boolean }
type PagoDraft = { contrato_id: string; anio: string; mes: string }
type MoraDraft = { fecha_corte: string }
type GarantiaDraft = { contrato: string; monto_pactado: string }
type GarantiaMovimientoDraft = { garantiaId: string; tipo_movimiento: string; monto_clp: string; fecha: string; justificacion: string; resolucion_exceso_garantia: string; resolucion_exceso_garantia_ref: string; resolucion_exceso_garantia_motivo: string }
type GarantiaTraceDraft = { garantiaId: string; aceptacion_parcial_ref: string; resolucion_exceso_garantia: string; resolucion_exceso_garantia_ref: string; resolucion_exceso_garantia_motivo: string }
type EstadoCuentaDraft = { arrendatario_id: string }
type WebpayPrepareDraft = { pago_mensual: string; gate_cobro: string; provider_key: string; return_url_ref: string }
type WebpayConfirmDraft = { intento_id: string; external_ref: string; fecha_pago_webpay: string }

const UF_SOURCE_OPTIONS = [
  { value: 'UF.BancoCentral', label: 'Banco Central' },
  { value: 'UF.CMF', label: 'CMF' },
  { value: 'UF.MiIndicador', label: 'MiIndicador' },
  { value: 'UF.CargaManualExtraordinaria', label: 'Carga manual' },
]
const REDACTED_SENSITIVE_REFERENCE = '<redacted-sensitive-reference>'

function editableReference(value?: string) {
  return value === REDACTED_SENSITIVE_REFERENCE ? '' : value || ''
}

function formatPayload(value?: Record<string, unknown>) {
  if (!value || Object.keys(value).length === 0) return '-'
  return JSON.stringify(value)
}

function formatDistribuciones(items?: DistribucionPagoItem[]) {
  if (!items || items.length === 0) return 'Sin distribucion'
  return items
    .map((item) => `${item.beneficiario_display} ${item.porcentaje_snapshot}% dev ${item.monto_devengado_clp} fact ${item.monto_facturable_clp}${item.requiere_dte ? ' DTE' : ''}`)
    .join(' | ')
}

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
  moraDraft,
  setMoraDraft,
  handleRefreshMora,
  garantiaDraft,
  setGarantiaDraft,
  handleCreateGarantia,
  garantiaMovimientoDraft,
  setGarantiaMovimientoDraft,
  handleGarantiaMovimiento,
  garantiaTraceDraft,
  setGarantiaTraceDraft,
  handleUpdateGarantiaTrace,
  estadoCuentaDraft,
  setEstadoCuentaDraft,
  handleRebuildEstadoCuenta,
  webpayPrepareDraft,
  setWebpayPrepareDraft,
  handlePrepareWebpayIntent,
  webpayConfirmDraft,
  setWebpayConfirmDraft,
  handleConfirmWebpayIntent,
  contratos,
  pagos,
  gatesCobro,
  intentosWebPay,
  repactaciones,
  codigosResiduales,
  garantias,
  arrendatarios,
  filteredValoresUf,
  filteredAjustes,
  filteredPagos,
  filteredGatesCobro,
  filteredIntentosWebPay,
  filteredRepactaciones,
  filteredCodigosResiduales,
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
  moraDraft: MoraDraft
  setMoraDraft: Dispatch<SetStateAction<MoraDraft>>
  handleRefreshMora: (event: FormEvent<HTMLFormElement>) => Promise<void>
  garantiaDraft: GarantiaDraft
  setGarantiaDraft: Dispatch<SetStateAction<GarantiaDraft>>
  handleCreateGarantia: (event: FormEvent<HTMLFormElement>) => Promise<void>
  garantiaMovimientoDraft: GarantiaMovimientoDraft
  setGarantiaMovimientoDraft: Dispatch<SetStateAction<GarantiaMovimientoDraft>>
  handleGarantiaMovimiento: (event: FormEvent<HTMLFormElement>) => Promise<void>
  garantiaTraceDraft: GarantiaTraceDraft
  setGarantiaTraceDraft: Dispatch<SetStateAction<GarantiaTraceDraft>>
  handleUpdateGarantiaTrace: (event: FormEvent<HTMLFormElement>) => Promise<void>
  estadoCuentaDraft: EstadoCuentaDraft
  setEstadoCuentaDraft: Dispatch<SetStateAction<EstadoCuentaDraft>>
  handleRebuildEstadoCuenta: (event: FormEvent<HTMLFormElement>) => Promise<void>
  webpayPrepareDraft: WebpayPrepareDraft
  setWebpayPrepareDraft: Dispatch<SetStateAction<WebpayPrepareDraft>>
  handlePrepareWebpayIntent: (event: FormEvent<HTMLFormElement>) => Promise<void>
  webpayConfirmDraft: WebpayConfirmDraft
  setWebpayConfirmDraft: Dispatch<SetStateAction<WebpayConfirmDraft>>
  handleConfirmWebpayIntent: (event: FormEvent<HTMLFormElement>) => Promise<void>
  contratos: ContratoItem[]
  pagos: PagoMensualItem[]
  gatesCobro: GateCobroExternoItem[]
  intentosWebPay: IntentoPagoWebPayItem[]
  repactaciones: RepactacionDeudaItem[]
  codigosResiduales: CodigoCobroResidualItem[]
  garantias: GarantiaItem[]
  arrendatarios: ArrendatarioItem[]
  filteredValoresUf: ValorUFItem[]
  filteredAjustes: AjusteContratoItem[]
  filteredPagos: PagoMensualItem[]
  filteredGatesCobro: GateCobroExternoItem[]
  filteredIntentosWebPay: IntentoPagoWebPayItem[]
  filteredRepactaciones: RepactacionDeudaItem[]
  filteredCodigosResiduales: CodigoCobroResidualItem[]
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
  const ufRequiresManualTrace = ufDraft.source_key.trim() === 'UF.CargaManualExtraordinaria'
  const ufTraceMissing = ufRequiresManualTrace && (!ufDraft.evidencia_ref.trim() || !ufDraft.motivo_carga.trim() || !ufDraft.responsable_ref.trim())
  const guaranteeExcessTraceFields = [
    garantiaTraceDraft.resolucion_exceso_garantia.trim(),
    garantiaTraceDraft.resolucion_exceso_garantia_ref.trim(),
    garantiaTraceDraft.resolucion_exceso_garantia_motivo.trim(),
  ]
  const guaranteeExcessTraceIncomplete = guaranteeExcessTraceFields.some(Boolean) && !guaranteeExcessTraceFields.every(Boolean)
  const pagoById = new Map(pagos.map((item) => [item.id, item]))
  const webpayGates = gatesCobro.filter((item) => item.capacidad_key === 'WebPay.IntentoPago')
  const preparedWebpayIntents = intentosWebPay.filter((item) => item.estado === 'preparado')
  const repactacionesActivas = repactaciones.filter((item) => item.estado === 'activa').length
  const residualesActivos = codigosResiduales.filter((item) => item.estado === 'activa').length

  return (
    <>
      {!canEditCobranza ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Cobranza.</div> : null}
      <section className="form-grid">
        <section className="panel">
          <div className="section-heading"><div><h2>Valor UF</h2><p>Registro diario mínimo para contratos en UF.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateUf}>
            <input type="date" value={ufDraft.fecha} onChange={(event) => setUfDraft((current) => ({ ...current, fecha: event.target.value }))} />
            <input placeholder="Valor UF" value={ufDraft.valor} onChange={(event) => setUfDraft((current) => ({ ...current, valor: event.target.value }))} />
            <select value={ufDraft.source_key} onChange={(event) => setUfDraft((current) => ({ ...current, source_key: event.target.value }))}>
              {UF_SOURCE_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
            <input placeholder="Evidencia UF" value={ufDraft.evidencia_ref} onChange={(event) => setUfDraft((current) => ({ ...current, evidencia_ref: event.target.value }))} />
            <input placeholder="Motivo UF" value={ufDraft.motivo_carga} onChange={(event) => setUfDraft((current) => ({ ...current, motivo_carga: event.target.value }))} />
            <input placeholder="Responsable UF" value={ufDraft.responsable_ref} onChange={(event) => setUfDraft((current) => ({ ...current, responsable_ref: event.target.value }))} />
            <button type="submit" className="button-primary" disabled={isSubmitting || !canEditCobranza || !ufDraft.valor || ufTraceMissing}>Guardar UF</button>
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
          <div className="section-heading"><div><h2>Refrescar mora</h2><p>Marca pagos vencidos abiertos como atrasados y recalcula estados de cuenta.</p></div></div>
          <form className="entity-form" onSubmit={handleRefreshMora}>
            <input type="date" value={moraDraft.fecha_corte} onChange={(event) => setMoraDraft({ fecha_corte: event.target.value })} />
            <button type="submit" className="button-primary" disabled={isSubmitting || !canEditCobranza || !moraDraft.fecha_corte}>Refrescar mora</button>
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
            <select value={garantiaMovimientoDraft.resolucion_exceso_garantia} onChange={(event) => setGarantiaMovimientoDraft((current) => ({ ...current, resolucion_exceso_garantia: event.target.value }))}>
              <option value="">Sin exceso</option>
              <option value="clasificar">Clasificar exceso</option>
              <option value="devolver">Devolver exceso</option>
              <option value="regularizar">Regularizar exceso</option>
              <option value="bloquear">Bloquear exceso</option>
            </select>
            <input placeholder="Ref. exceso no sensible" value={garantiaMovimientoDraft.resolucion_exceso_garantia_ref} onChange={(event) => setGarantiaMovimientoDraft((current) => ({ ...current, resolucion_exceso_garantia_ref: event.target.value }))} />
            <input placeholder="Motivo exceso" value={garantiaMovimientoDraft.resolucion_exceso_garantia_motivo} onChange={(event) => setGarantiaMovimientoDraft((current) => ({ ...current, resolucion_exceso_garantia_motivo: event.target.value }))} />
            <button type="submit" className="button-secondary" disabled={isSubmitting || !canEditCobranza || !garantiaMovimientoDraft.garantiaId || !garantiaMovimientoDraft.monto_clp}>Registrar movimiento</button>
          </form>
          <form className="entity-form subform" onSubmit={handleUpdateGarantiaTrace}>
            <select
              value={garantiaTraceDraft.garantiaId}
              onChange={(event) => {
                const selected = garantias.find((item) => String(item.id) === event.target.value)
                setGarantiaTraceDraft({
                  garantiaId: event.target.value,
                  aceptacion_parcial_ref: editableReference(selected?.aceptacion_parcial_ref),
                  resolucion_exceso_garantia: selected?.resolucion_exceso_garantia || '',
                  resolucion_exceso_garantia_ref: editableReference(selected?.resolucion_exceso_garantia_ref),
                  resolucion_exceso_garantia_motivo: editableReference(selected?.resolucion_exceso_garantia_motivo),
                })
              }}
            >
              <option value="">Selecciona garantía a trazar</option>
              {garantias.map((item) => <option key={item.id} value={item.id}>{contratoById.get(item.contrato)?.codigo_contrato || item.contrato}</option>)}
            </select>
            <input placeholder="Aceptación parcial ref" value={garantiaTraceDraft.aceptacion_parcial_ref} onChange={(event) => setGarantiaTraceDraft((current) => ({ ...current, aceptacion_parcial_ref: event.target.value }))} />
            <select value={garantiaTraceDraft.resolucion_exceso_garantia} onChange={(event) => setGarantiaTraceDraft((current) => ({ ...current, resolucion_exceso_garantia: event.target.value }))}>
              <option value="">Sin exceso</option>
              <option value="clasificar">Clasificar exceso</option>
              <option value="devolver">Devolver exceso</option>
              <option value="regularizar">Regularizar exceso</option>
              <option value="bloquear">Bloquear exceso</option>
            </select>
            <input placeholder="Ref. exceso no sensible" value={garantiaTraceDraft.resolucion_exceso_garantia_ref} onChange={(event) => setGarantiaTraceDraft((current) => ({ ...current, resolucion_exceso_garantia_ref: event.target.value }))} />
            <input placeholder="Motivo exceso" value={garantiaTraceDraft.resolucion_exceso_garantia_motivo} onChange={(event) => setGarantiaTraceDraft((current) => ({ ...current, resolucion_exceso_garantia_motivo: event.target.value }))} />
            <button type="submit" className="button-secondary" disabled={isSubmitting || !canEditCobranza || !garantiaTraceDraft.garantiaId || guaranteeExcessTraceIncomplete}>Actualizar trazabilidad</button>
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

        <section className="panel">
          <div className="section-heading"><div><h2>WebPay local</h2><p>Preparación controlada y confirmación manual sin proveedor externo.</p></div></div>
          <form className="entity-form" onSubmit={handlePrepareWebpayIntent}>
            <select value={webpayPrepareDraft.pago_mensual} onChange={(event) => setWebpayPrepareDraft((current) => ({ ...current, pago_mensual: event.target.value }))}>
              <option value="">Selecciona pago</option>
              {pagos.map((item) => <option key={item.id} value={item.id}>{contratoById.get(item.contrato)?.codigo_contrato || item.contrato} · {item.mes}/{item.anio} · {item.estado_pago}</option>)}
            </select>
            <select value={webpayPrepareDraft.gate_cobro} onChange={(event) => setWebpayPrepareDraft((current) => ({ ...current, gate_cobro: event.target.value }))}>
              <option value="">Gate por provider</option>
              {webpayGates.map((item) => <option key={item.id} value={item.id}>{item.provider_key} · {item.estado_gate}</option>)}
            </select>
            <input placeholder="Provider" value={webpayPrepareDraft.provider_key} onChange={(event) => setWebpayPrepareDraft((current) => ({ ...current, provider_key: event.target.value }))} />
            <input placeholder="Return ref no sensible" value={webpayPrepareDraft.return_url_ref} onChange={(event) => setWebpayPrepareDraft((current) => ({ ...current, return_url_ref: event.target.value }))} />
            <button type="submit" className="button-primary" disabled={isSubmitting || !canEditCobranza || !webpayPrepareDraft.pago_mensual || !webpayPrepareDraft.return_url_ref}>Preparar intento</button>
          </form>
          <form className="entity-form subform" onSubmit={handleConfirmWebpayIntent}>
            <select value={webpayConfirmDraft.intento_id} onChange={(event) => setWebpayConfirmDraft((current) => ({ ...current, intento_id: event.target.value }))}>
              <option value="">Selecciona intento preparado</option>
              {preparedWebpayIntents.map((item) => {
                const pago = pagoById.get(item.pago_mensual)
                const label = pago ? `${contratoById.get(pago.contrato)?.codigo_contrato || pago.contrato} · ${pago.mes}/${pago.anio}` : `Pago ${item.pago_mensual}`
                return <option key={item.id} value={item.id}>{label} · {item.buy_order || item.id}</option>
              })}
            </select>
            <input placeholder="External ref no sensible" value={webpayConfirmDraft.external_ref} onChange={(event) => setWebpayConfirmDraft((current) => ({ ...current, external_ref: event.target.value }))} />
            <input type="date" value={webpayConfirmDraft.fecha_pago_webpay} onChange={(event) => setWebpayConfirmDraft((current) => ({ ...current, fecha_pago_webpay: event.target.value }))} />
            <button type="submit" className="button-secondary" disabled={isSubmitting || !canEditCobranza || !webpayConfirmDraft.intento_id || !webpayConfirmDraft.external_ref || !webpayConfirmDraft.fecha_pago_webpay}>Confirmar manual</button>
          </form>
        </section>
      </section>

      <TableBlock title="Valores UF" subtitle="Fuente de conversión mensual para contratos en UF." rows={filteredValoresUf} empty="No hay valores UF para este filtro." isLoading={isLoading} loadingLabel="Cargando cobranza..." columns={[
        { label: 'Fecha', render: (row) => row.fecha },
        { label: 'Valor', render: (row) => row.valor },
        { label: 'Source', render: (row) => row.source_key },
        { label: 'Evidencia', render: (row) => row.evidencia_ref || '-' },
        { label: 'Responsable', render: (row) => row.responsable_ref || '-' },
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
        { label: 'Distribución', render: (row) => formatDistribuciones(row.distribuciones_detail) },
        { label: 'Efecto código', render: (row) => row.monto_efecto_codigo_efectivo_clp },
        { label: 'UF usada', render: (row) => row.moneda_calculo === 'UF' ? `${row.uf_valor_usado || '-'} · ${row.uf_fecha_usada || '-'} · ${row.uf_source_key || '-'}` : row.moneda_calculo },
        { label: 'Pagado', render: (row) => row.monto_pagado_clp },
        { label: 'Vence', render: (row) => row.fecha_vencimiento },
        { label: 'WebPay', render: (row) => row.fecha_pago_webpay || '-' },
        { label: 'Estado', render: (row) => <Badge label={row.estado_pago} tone={toneFor(row.estado_pago)} /> },
        { label: 'Resolución', render: (row) => row.resolucion_pago_excepcional_ref || row.resolucion_pago_excepcional_motivo || 'Sin resolución' },
        { label: 'Mora', render: (row) => count(row.dias_mora) },
        { label: 'Siguiente paso', render: (row) => <div className="inline-actions"><button type="button" className="button-ghost inline-action" onClick={() => navigateToConciliacion(row)}>Conciliar</button>{canOpenSii ? <button type="button" className="button-ghost inline-action" onClick={() => goToPagoContext(row.id)}>DTE</button> : null}</div> },
      ]} />
      <TableBlock title="Gates WebPay" subtitle="Estado local de la capacidad WebPay.IntentoPago y evidencia no sensible." rows={filteredGatesCobro} empty="No hay gates WebPay para este filtro." isLoading={isLoading} loadingLabel="Cargando cobranza..." columns={[
        { label: 'Capacidad', render: (row) => row.capacidad_key },
        { label: 'Provider', render: (row) => row.provider_key },
        { label: 'Estado', render: (row) => <Badge label={row.estado_gate} tone={toneFor(row.estado_gate)} /> },
        { label: 'Evidencia', render: (row) => row.evidencia_ref || '-' },
        { label: 'Restricciones', render: (row) => formatPayload(row.restricciones_operativas) },
      ]} />
      <TableBlock title="Intentos WebPay" subtitle="Intentos locales preparados, bloqueados o confirmados manualmente." rows={filteredIntentosWebPay} empty="No hay intentos WebPay para este filtro." isLoading={isLoading} loadingLabel="Cargando cobranza..." columns={[
        { label: 'Pago', render: (row) => {
          const pago = pagoById.get(row.pago_mensual)
          return pago ? `${contratoById.get(pago.contrato)?.codigo_contrato || pago.contrato} · ${pago.mes}/${pago.anio}` : row.pago_mensual
        } },
        { label: 'Provider', render: (row) => row.provider_key },
        { label: 'Monto', render: (row) => row.monto_clp_snapshot },
        { label: 'Buy order', render: (row) => row.buy_order || '-' },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Return ref', render: (row) => row.return_url_ref || '-' },
        { label: 'Motivo', render: (row) => row.motivo_bloqueo || '-' },
        { label: 'External ref', render: (row) => row.external_ref || '-' },
        { label: 'Fecha pago', render: (row) => row.fecha_pago_webpay || '-' },
        { label: 'Payload', render: (row) => formatPayload(row.provider_payload) },
      ]} />
      <TableBlock title="Repactaciones" subtitle={`${count(repactacionesActivas)} planes activos; coherencia saldo/estado y excepciones parciales.`} rows={filteredRepactaciones} empty="No hay repactaciones para este filtro." isLoading={isLoading} loadingLabel="Cargando cobranza..." columns={[
        { label: 'Arrendatario', render: (row) => arrendatarioById.get(row.arrendatario)?.nombre_razon_social || row.arrendatario },
        { label: 'Contrato', render: (row) => contratoById.get(row.contrato_origen)?.codigo_contrato || row.contrato_origen },
        { label: 'Deuda original', render: (row) => row.deuda_total_original },
        { label: 'Plan', render: (row) => `${count(row.cantidad_cuotas)} x ${row.monto_cuota}` },
        { label: 'Saldo', render: (row) => row.saldo_pendiente },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Parcial', render: (row) => row.es_repactacion_parcial ? <Badge label={row.tiene_excepcion_parcial ? 'con excepción' : 'sin excepción'} tone={row.tiene_excepcion_parcial ? 'warning' : 'danger'} /> : <Badge label="total" /> },
        { label: 'Excepción', render: (row) => row.excepcion_parcial_ref || row.excepcion_parcial_motivo || '-' },
      ]} />
      <TableBlock title="Códigos residuales" subtitle={`${count(residualesActivos)} cobros residuales activos con referencia CCR controlada.`} rows={filteredCodigosResiduales} empty="No hay códigos residuales para este filtro." isLoading={isLoading} loadingLabel="Cargando cobranza..." columns={[
        { label: 'Referencia', render: (row) => row.referencia_visible },
        { label: 'Arrendatario', render: (row) => arrendatarioById.get(row.arrendatario)?.nombre_razon_social || row.arrendatario },
        { label: 'Contrato origen', render: (row) => contratoById.get(row.contrato_origen)?.codigo_contrato || row.contrato_origen },
        { label: 'Saldo', render: (row) => row.saldo_actual },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Activación', render: (row) => row.fecha_activacion },
      ]} />
      <TableBlock title="Garantías" subtitle="Saldos y estado actual de cada contrato." rows={filteredGarantias} empty="No hay garantías para este filtro." isLoading={isLoading} loadingLabel="Cargando cobranza..." columns={[
        { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
        { label: 'Pactado', render: (row) => row.monto_pactado },
        { label: 'Recibido', render: (row) => row.monto_recibido },
        { label: 'Saldo', render: (row) => row.saldo_vigente },
        { label: 'Cobertura', render: (row) => row.garantia_incompleta ? <Badge label="incompleta" tone="warning" /> : row.garantia_parcial_aceptada ? <Badge label="parcial aceptada" tone="positive" /> : Number(row.exceso_garantia_clp) > 0 ? <Badge label={row.tiene_resolucion_exceso_garantia ? 'exceso resuelto' : 'exceso pendiente'} tone={row.tiene_resolucion_exceso_garantia ? 'warning' : 'danger'} /> : <Badge label="regular" tone="neutral" /> },
        { label: 'Aceptación parcial', render: (row) => row.aceptacion_parcial_ref || (row.garantia_incompleta ? 'pendiente' : '-') },
        { label: 'Exceso', render: (row) => Number(row.exceso_garantia_clp) > 0 ? `${row.exceso_garantia_clp} · ${row.resolucion_exceso_garantia || 'sin resolución'} · ${row.resolucion_exceso_garantia_ref || 'sin ref'} · ${row.resolucion_exceso_garantia_motivo || 'sin motivo'}` : '0.00' },
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
        { label: 'Repactaciones', render: (row) => count(row.resumen_operativo.repactaciones_activas) },
        { label: 'Residuales', render: (row) => count(row.resumen_operativo.cobranzas_residuales_activas) },
        { label: 'Meses eval.', render: (row) => count(row.resumen_operativo.score_meses_evaluados) },
        { label: 'En plazo', render: (row) => count(row.resumen_operativo.score_pagos_en_plazo) },
        { label: 'Fuera plazo', render: (row) => count(row.resumen_operativo.score_pagos_fuera_plazo) },
        { label: 'Sin registro', render: (row) => count(row.resumen_operativo.score_meses_sin_registro_operativo) },
        { label: 'Saldo total', render: (row) => row.resumen_operativo.saldo_total_clp || '0.00' },
        { label: 'Score', render: (row) => {
          const score = row.score_pago ?? row.resumen_operativo.score_pago_porcentaje
          return score === null || score === undefined ? 'Sin score' : `${score}%`
        } },
        { label: 'Observaciones', render: (row) => row.observaciones || '-' },
      ]} />
    </>
  )
}
