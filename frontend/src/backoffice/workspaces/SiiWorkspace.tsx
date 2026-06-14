import { useMemo, useState, type Dispatch, type FormEvent, type SetStateAction } from 'react'

import { Badge, TableBlock } from '../shared'

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'

type EmpresaItem = { id: number; razon_social: string }
type PagoItem = { id: number; contrato: number; mes: number; anio: number; estado_pago?: string; tiene_distribucion_facturable?: boolean; distribuciones_detail?: Array<{ requiere_dte: boolean }> }
type ContratoItem = { id: number; codigo_contrato: string }
type CapacidadSiiItem = {
  id: number
  empresa: number
  capacidad_key: string
  evidencia_ref: string
  prueba_flujo_ref: string
  autorizacion_ambiente_ref: string
  regla_fiscal_ref: string
  ambiente: string
  estado_gate: string
}
type DteEmitidoItem = { id: number; empresa: number; contrato: number; pago_mensual: number; monto_neto_clp: string; estado_dte: string; sii_track_id: string }
type F29PreparacionItem = { id: number; empresa: number; capacidad_tributaria: number; anio: number; mes: number; estado_preparacion: string; borrador_ref: string; responsable_revision_ref: string; observaciones: string }
type ProcesoRentaAnualItem = { id: number; empresa: number; anio_tributario: number; estado: string; fecha_preparacion: string | null; responsable_revision_ref: string }
type DdjjPreparacionItem = { id: number; empresa: number; anio_tributario: number; estado_preparacion: string; paquete_ref: string; responsable_revision_ref: string; observaciones: string }
type F22PreparacionItem = { id: number; empresa: number; anio_tributario: number; estado_preparacion: string; borrador_ref: string; responsable_revision_ref: string; observaciones: string }

type CapacidadSiiDraft = {
  empresa: string
  capacidad_key: string
  certificado_ref: string
  evidencia_ref: string
  prueba_flujo_ref: string
  autorizacion_ambiente_ref: string
  regla_fiscal_ref: string
  ambiente: string
  estado_gate: string
}

type DteDraft = {
  pago_mensual_id: string
  tipo_dte: string
}

type F29Draft = {
  empresa_id: string
  anio: string
  mes: string
}

type AnnualDraft = {
  empresa_id: string
  anio_tributario: string
}

type F29ReviewDraft = {
  item_id: string
  estado_preparacion: string
  borrador_ref: string
  responsable_revision_ref: string
  observaciones: string
}

type AnnualReviewKind = 'ddjj' | 'f22'

type AnnualReviewDraft = {
  artifact_kind: AnnualReviewKind
  item_id: string
  estado_preparacion: string
  ref_value: string
  responsable_revision_ref: string
  observaciones: string
}

type AnnualReviewOption = {
  id: string
  label: string
  refValue: string
  responsableRevisionRef: string
  observaciones: string
}

const initialAnnualReviewDraft: AnnualReviewDraft = {
  artifact_kind: 'ddjj',
  item_id: '',
  estado_preparacion: 'aprobado_para_presentacion',
  ref_value: '',
  responsable_revision_ref: '',
  observaciones: '',
}

const initialF29ReviewDraft: F29ReviewDraft = {
  item_id: '',
  estado_preparacion: 'aprobado_para_presentacion',
  borrador_ref: '',
  responsable_revision_ref: '',
  observaciones: '',
}

export function SiiWorkspace({
  canEditSii,
  capacidadSiiDraft,
  setCapacidadSiiDraft,
  handleCreateCapacidadSii,
  dteDraft,
  setDteDraft,
  handleGenerateDte,
  f29Draft,
  setF29Draft,
  handleGenerateF29,
  annualDraft,
  setAnnualDraft,
  handleGenerateAnnual,
  empresas,
  pagos,
  contratoById,
  filteredCapacidadesSii,
  filteredDtes,
  filteredF29s,
  filteredProcesosAnuales,
  filteredDdjjs,
  filteredF22s,
  empresaById,
  capacidadSiiById,
  toneFor,
  isSubmitting,
  isLoading,
  handleSiiStatusUpdate,
  onViewReporting,
}: {
  canEditSii: boolean
  capacidadSiiDraft: CapacidadSiiDraft
  setCapacidadSiiDraft: Dispatch<SetStateAction<CapacidadSiiDraft>>
  handleCreateCapacidadSii: (event: FormEvent<HTMLFormElement>) => Promise<void>
  dteDraft: DteDraft
  setDteDraft: Dispatch<SetStateAction<DteDraft>>
  handleGenerateDte: (event: FormEvent<HTMLFormElement>) => Promise<void>
  f29Draft: F29Draft
  setF29Draft: Dispatch<SetStateAction<F29Draft>>
  handleGenerateF29: (event: FormEvent<HTMLFormElement>) => Promise<void>
  annualDraft: AnnualDraft
  setAnnualDraft: Dispatch<SetStateAction<AnnualDraft>>
  handleGenerateAnnual: (event: FormEvent<HTMLFormElement>) => Promise<void>
  empresas: EmpresaItem[]
  pagos: PagoItem[]
  contratoById: ReadonlyMap<number, ContratoItem>
  filteredCapacidadesSii: CapacidadSiiItem[]
  filteredDtes: DteEmitidoItem[]
  filteredF29s: F29PreparacionItem[]
  filteredProcesosAnuales: ProcesoRentaAnualItem[]
  filteredDdjjs: DdjjPreparacionItem[]
  filteredF22s: F22PreparacionItem[]
  empresaById: ReadonlyMap<number, EmpresaItem>
  capacidadSiiById: ReadonlyMap<number, CapacidadSiiItem>
  toneFor: (value: string) => Tone
  isSubmitting: boolean
  isLoading: boolean
  handleSiiStatusUpdate: (path: string, body: Record<string, unknown>, successMessage: string) => Promise<boolean>
  onViewReporting: (companyId: number) => void
}) {
  const pagosElegiblesDte = pagos.filter((item) => {
    const tieneDistribucionFacturable = item.tiene_distribucion_facturable ?? Boolean(item.distribuciones_detail?.some((detail) => detail.requiere_dte))
    const estadoPago = item.estado_pago ?? ''
    return tieneDistribucionFacturable && ['pagado', 'pagado_via_repactacion', 'pagado_por_acuerdo_termino'].includes(estadoPago)
  })
  const [f29ReviewDraft, setF29ReviewDraft] = useState<F29ReviewDraft>(initialF29ReviewDraft)
  const [annualReviewDraft, setAnnualReviewDraft] = useState<AnnualReviewDraft>(initialAnnualReviewDraft)
  const selectedF29Review = filteredF29s.find((item) => String(item.id) === f29ReviewDraft.item_id)
  const f29ReviewNeedsResponsable = f29ReviewDraft.estado_preparacion !== 'preparado'
  const canSubmitF29Review = Boolean(selectedF29Review)
    && (!f29ReviewNeedsResponsable || (
      f29ReviewDraft.borrador_ref.trim().length > 0
      && f29ReviewDraft.responsable_revision_ref.trim().length > 0
    ))
  const annualReviewOptions = useMemo<AnnualReviewOption[]>(() => {
    const rows = annualReviewDraft.artifact_kind === 'ddjj' ? filteredDdjjs : filteredF22s
    return rows.map((item) => {
      const isDdjj = annualReviewDraft.artifact_kind === 'ddjj'
      const refValue = isDdjj ? (item as DdjjPreparacionItem).paquete_ref : (item as F22PreparacionItem).borrador_ref
      return {
        id: String(item.id),
        label: `${empresaById.get(item.empresa)?.razon_social || item.empresa} · AT ${item.anio_tributario} · ${item.estado_preparacion}`,
        refValue: refValue || '',
        responsableRevisionRef: item.responsable_revision_ref || '',
        observaciones: item.observaciones || '',
      }
    })
  }, [annualReviewDraft.artifact_kind, empresaById, filteredDdjjs, filteredF22s])
  const selectedAnnualReviewOption = annualReviewOptions.find((item) => item.id === annualReviewDraft.item_id)
  const annualReviewNeedsResponsable = annualReviewDraft.estado_preparacion !== 'preparado'
  const canSubmitAnnualReview = Boolean(selectedAnnualReviewOption)
    && (!annualReviewNeedsResponsable || (
      annualReviewDraft.ref_value.trim().length > 0
      && annualReviewDraft.responsable_revision_ref.trim().length > 0
    ))

  function setAnnualReviewKind(value: AnnualReviewKind) {
    setAnnualReviewDraft({ ...initialAnnualReviewDraft, artifact_kind: value })
  }

  function loadF29Review(item: F29PreparacionItem) {
    setF29ReviewDraft({
      item_id: String(item.id),
      estado_preparacion: item.estado_preparacion === 'preparado' ? 'aprobado_para_presentacion' : item.estado_preparacion,
      borrador_ref: item.borrador_ref || '',
      responsable_revision_ref: item.responsable_revision_ref || '',
      observaciones: item.observaciones || '',
    })
  }

  async function handleF29ReviewSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditSii || !canSubmitF29Review) return
    const ok = await handleSiiStatusUpdate(`/api/v1/sii/f29/${f29ReviewDraft.item_id}/estado/`, {
      estado_preparacion: f29ReviewDraft.estado_preparacion,
      borrador_ref: f29ReviewDraft.borrador_ref.trim(),
      responsable_revision_ref: f29ReviewDraft.responsable_revision_ref.trim(),
      observaciones: f29ReviewDraft.observaciones.trim(),
    }, 'Revisión F29 actualizada correctamente.')
    if (ok) {
      setF29ReviewDraft(initialF29ReviewDraft)
    }
  }

  function setAnnualReviewItem(value: string) {
    const selected = annualReviewOptions.find((item) => item.id === value)
    setAnnualReviewDraft((current) => ({
      ...current,
      item_id: value,
      ref_value: selected?.refValue || '',
      responsable_revision_ref: selected?.responsableRevisionRef || '',
      observaciones: selected?.observaciones || '',
    }))
  }

  function loadAnnualReview(kind: AnnualReviewKind, item: DdjjPreparacionItem | F22PreparacionItem) {
    setAnnualReviewDraft({
      artifact_kind: kind,
      item_id: String(item.id),
      estado_preparacion: item.estado_preparacion === 'preparado' ? 'aprobado_para_presentacion' : item.estado_preparacion,
      ref_value: kind === 'ddjj' ? (item as DdjjPreparacionItem).paquete_ref || '' : (item as F22PreparacionItem).borrador_ref || '',
      responsable_revision_ref: item.responsable_revision_ref || '',
      observaciones: item.observaciones || '',
    })
  }

  async function handleAnnualReviewSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canEditSii || !canSubmitAnnualReview) return
    const path = annualReviewDraft.artifact_kind === 'ddjj'
      ? `/api/v1/sii/anual/ddjj/${annualReviewDraft.item_id}/estado/`
      : `/api/v1/sii/anual/f22/${annualReviewDraft.item_id}/estado/`
    const ok = await handleSiiStatusUpdate(path, {
      estado_preparacion: annualReviewDraft.estado_preparacion,
      ref_value: annualReviewDraft.ref_value.trim(),
      responsable_revision_ref: annualReviewDraft.responsable_revision_ref.trim(),
      observaciones: annualReviewDraft.observaciones.trim(),
    }, 'Revisión anual actualizada correctamente.')
    if (ok) {
      setAnnualReviewDraft(initialAnnualReviewDraft)
    }
  }

  return (
    <>
      {!canEditSii ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en SII.</div> : null}
      {canEditSii ? <section className="form-grid">
        <section className="panel">
          <div className="section-heading"><div><h2>Capacidad SII</h2><p>Gate operativo por empresa y capacidad tributaria.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateCapacidadSii}>
            <select value={capacidadSiiDraft.empresa} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, empresa: event.target.value }))}>
              <option value="">Selecciona empresa</option>
              {empresas.map((item) => <option key={item.id} value={item.id}>{item.razon_social}</option>)}
            </select>
            <select value={capacidadSiiDraft.capacidad_key} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, capacidad_key: event.target.value }))}>
              <option value="DTEEmision">DTE Emisión</option>
              <option value="DTEConsultaEstado">DTE Consulta Estado</option>
              <option value="F29Preparacion">F29 Preparación</option>
              <option value="F29Presentacion">F29 Presentación</option>
              <option value="DDJJPreparacion">DDJJ Preparación</option>
              <option value="F22Preparacion">F22 Preparación</option>
            </select>
            <input placeholder="Certificado ref" value={capacidadSiiDraft.certificado_ref} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, certificado_ref: event.target.value }))} />
            <input placeholder="Evidencia gate ref" value={capacidadSiiDraft.evidencia_ref} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, evidencia_ref: event.target.value }))} />
            <input placeholder="Prueba flujo ref" value={capacidadSiiDraft.prueba_flujo_ref} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, prueba_flujo_ref: event.target.value }))} />
            <input placeholder="Autorización ambiente ref" value={capacidadSiiDraft.autorizacion_ambiente_ref} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, autorizacion_ambiente_ref: event.target.value }))} />
            <input placeholder="Regla fiscal ref" value={capacidadSiiDraft.regla_fiscal_ref} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, regla_fiscal_ref: event.target.value }))} />
            <select value={capacidadSiiDraft.ambiente} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, ambiente: event.target.value }))}>
              <option value="certificacion">Certificación</option>
              <option value="produccion">Producción</option>
            </select>
            <select value={capacidadSiiDraft.estado_gate} onChange={(event) => setCapacidadSiiDraft((current) => ({ ...current, estado_gate: event.target.value }))}>
              <option value="abierto">Abierto</option>
              <option value="condicionado">Condicionado</option>
              <option value="cerrado">Cerrado</option>
              <option value="suspendido">Suspendido</option>
              <option value="podado">Podado</option>
            </select>
            <button type="submit" className="button-primary" disabled={isSubmitting || !capacidadSiiDraft.empresa}>Guardar capacidad</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Generar DTE</h2><p>Borrador desde un pago mensual con distribución facturable.</p></div></div>
          <form className="entity-form" onSubmit={handleGenerateDte}>
            <select value={dteDraft.pago_mensual_id} onChange={(event) => setDteDraft((current) => ({ ...current, pago_mensual_id: event.target.value }))}>
              <option value="">Selecciona pago</option>
              {pagosElegiblesDte.map((item) => <option key={item.id} value={item.id}>{contratoById.get(item.contrato)?.codigo_contrato || item.contrato} · {item.mes}/{item.anio}</option>)}
            </select>
            <select value={dteDraft.tipo_dte} onChange={(event) => setDteDraft((current) => ({ ...current, tipo_dte: event.target.value }))}>
              <option value="34">34 · Factura Exenta</option>
            </select>
            <button type="submit" className="button-primary" disabled={isSubmitting || !dteDraft.pago_mensual_id}>Generar DTE</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Generar F29</h2><p>Borrador mensual desde cierre contable preparado.</p></div></div>
          <form className="entity-form" onSubmit={handleGenerateF29}>
            <select value={f29Draft.empresa_id} onChange={(event) => setF29Draft((current) => ({ ...current, empresa_id: event.target.value }))}>
              <option value="">Selecciona empresa</option>
              {empresas.map((item) => <option key={item.id} value={item.id}>{item.razon_social}</option>)}
            </select>
            <input placeholder="Año" value={f29Draft.anio} onChange={(event) => setF29Draft((current) => ({ ...current, anio: event.target.value }))} />
            <input placeholder="Mes" value={f29Draft.mes} onChange={(event) => setF29Draft((current) => ({ ...current, mes: event.target.value }))} />
            <button type="submit" className="button-primary" disabled={isSubmitting || !f29Draft.empresa_id}>Generar F29</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Revisión F29</h2><p>Estado mensual con borrador, responsable y observación.</p></div></div>
          <form className="entity-form" onSubmit={handleF29ReviewSubmit}>
            <select value={f29ReviewDraft.item_id} onChange={(event) => {
              const selected = filteredF29s.find((item) => String(item.id) === event.target.value)
              if (selected) {
                loadF29Review(selected)
              } else {
                setF29ReviewDraft(initialF29ReviewDraft)
              }
            }}>
              <option value="">Selecciona F29</option>
              {filteredF29s.map((item) => (
                <option key={item.id} value={item.id}>{empresaById.get(item.empresa)?.razon_social || item.empresa} · {item.mes}/{item.anio} · {item.estado_preparacion}</option>
              ))}
            </select>
            <select value={f29ReviewDraft.estado_preparacion} onChange={(event) => setF29ReviewDraft((current) => ({ ...current, estado_preparacion: event.target.value }))}>
              <option value="preparado">Preparado</option>
              <option value="aprobado_para_presentacion">Aprobado para presentación</option>
              <option value="observado">Observado</option>
              <option value="rectificado">Rectificado</option>
            </select>
            <input placeholder="Borrador F29 ref" value={f29ReviewDraft.borrador_ref} onChange={(event) => setF29ReviewDraft((current) => ({ ...current, borrador_ref: event.target.value }))} />
            <input placeholder="Responsable revisión ref" value={f29ReviewDraft.responsable_revision_ref} onChange={(event) => setF29ReviewDraft((current) => ({ ...current, responsable_revision_ref: event.target.value }))} />
            <input placeholder="Observación no sensible" value={f29ReviewDraft.observaciones} onChange={(event) => setF29ReviewDraft((current) => ({ ...current, observaciones: event.target.value }))} />
            <button type="submit" className="button-primary" disabled={isSubmitting || !canSubmitF29Review}>Guardar revisión F29</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Preparación anual</h2><p>Genera proceso anual, DDJJ y F22.</p></div></div>
          <form className="entity-form" onSubmit={handleGenerateAnnual}>
            <select value={annualDraft.empresa_id} onChange={(event) => setAnnualDraft((current) => ({ ...current, empresa_id: event.target.value }))}>
              <option value="">Selecciona empresa</option>
              {empresas.map((item) => <option key={item.id} value={item.id}>{item.razon_social}</option>)}
            </select>
            <input placeholder="Año tributario" value={annualDraft.anio_tributario} onChange={(event) => setAnnualDraft((current) => ({ ...current, anio_tributario: event.target.value }))} />
            <button type="submit" className="button-primary" disabled={isSubmitting || !annualDraft.empresa_id}>Generar anual</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Revisión anual</h2><p>Actualiza DDJJ/F22 con responsable, referencia y observación.</p></div></div>
          <form className="entity-form" onSubmit={handleAnnualReviewSubmit}>
            <select value={annualReviewDraft.artifact_kind} onChange={(event) => setAnnualReviewKind(event.target.value as AnnualReviewKind)}>
              <option value="ddjj">DDJJ</option>
              <option value="f22">F22</option>
            </select>
            <select value={annualReviewDraft.item_id} onChange={(event) => setAnnualReviewItem(event.target.value)}>
              <option value="">Selecciona artefacto</option>
              {annualReviewOptions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
            </select>
            <select value={annualReviewDraft.estado_preparacion} onChange={(event) => setAnnualReviewDraft((current) => ({ ...current, estado_preparacion: event.target.value }))}>
              <option value="preparado">Preparado</option>
              <option value="aprobado_para_presentacion">Aprobado para presentación</option>
              <option value="observado">Observado</option>
              <option value="rectificado">Rectificado</option>
            </select>
            <input placeholder="Ref paquete/borrador" value={annualReviewDraft.ref_value} onChange={(event) => setAnnualReviewDraft((current) => ({ ...current, ref_value: event.target.value }))} />
            <input placeholder="Responsable revisión ref" value={annualReviewDraft.responsable_revision_ref} onChange={(event) => setAnnualReviewDraft((current) => ({ ...current, responsable_revision_ref: event.target.value }))} />
            <input placeholder="Observación no sensible" value={annualReviewDraft.observaciones} onChange={(event) => setAnnualReviewDraft((current) => ({ ...current, observaciones: event.target.value }))} />
            <button type="submit" className="button-primary" disabled={isSubmitting || !canSubmitAnnualReview}>Guardar revisión</button>
          </form>
        </section>
      </section> : null}

      <TableBlock title="Capacidades SII" subtitle="Gate y ambiente por empresa/capacidad." rows={filteredCapacidadesSii} empty="No hay capacidades SII para este filtro." isLoading={isLoading} loadingLabel="Cargando SII..." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Capacidad', render: (row) => row.capacidad_key },
        { label: 'Ambiente', render: (row) => row.ambiente },
        { label: 'Evidencia', render: (row) => row.evidencia_ref || 'Sin ref' },
        { label: 'Prueba', render: (row) => row.prueba_flujo_ref || 'Sin ref' },
        { label: 'Estado', render: (row) => <Badge label={row.estado_gate} tone={toneFor(row.estado_gate)} /> },
      ]} />
      <TableBlock title="DTE emitidos" subtitle="Borradores y estados manuales de DTE." rows={filteredDtes} empty="No hay DTE para este filtro." isLoading={isLoading} loadingLabel="Cargando SII..." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
        { label: 'Pago', render: (row) => row.pago_mensual },
        { label: 'Monto', render: (row) => row.monto_neto_clp },
        { label: 'Estado', render: (row) => <Badge label={row.estado_dte} tone={toneFor(row.estado_dte)} /> },
        { label: 'Acción', render: (row) => !canEditSii ? 'Solo lectura' : <div className="inline-actions"><button type="button" className="button-ghost inline-action" onClick={() => void handleSiiStatusUpdate(`/api/v1/sii/dtes/${row.id}/estado/`, { estado_dte: 'aceptado', sii_track_id: row.sii_track_id || 'TRACK-LOCAL', ultimo_estado_sii: 'ACEPTADO' }, 'Estado DTE actualizado correctamente.')} disabled={isSubmitting}>Marcar aceptado</button><button type="button" className="button-ghost inline-action" onClick={() => onViewReporting(row.empresa)}>Reporting</button></div> },
      ]} />
      <TableBlock title="F29 mensuales" subtitle="Preparación mensual desde cierres aprobados." rows={filteredF29s} empty="No hay F29 para este filtro." isLoading={isLoading} loadingLabel="Cargando SII..." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Período', render: (row) => `${row.mes}/${row.anio}` },
        { label: 'Capacidad', render: (row) => capacidadSiiById.get(row.capacidad_tributaria)?.capacidad_key || row.capacidad_tributaria },
        { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
        { label: 'Responsable', render: (row) => row.responsable_revision_ref || 'Sin responsable' },
        { label: 'Observación', render: (row) => row.observaciones || 'Sin observación' },
        { label: 'Acción', render: (row) => !canEditSii ? 'Solo lectura' : <button type="button" className="button-ghost inline-action" onClick={() => loadF29Review(row)} disabled={isSubmitting}>Cargar revisión</button> },
      ]} />
      <TableBlock title="Proceso renta anual" subtitle="Proceso consolidado por empresa y año tributario." rows={filteredProcesosAnuales} empty="No hay procesos anuales para este filtro." isLoading={isLoading} loadingLabel="Cargando SII..." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Año tributario', render: (row) => row.anio_tributario },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Responsable', render: (row) => row.responsable_revision_ref || 'Sin responsable' },
        { label: 'Preparación', render: (row) => row.fecha_preparacion || 'Sin fecha' },
      ]} />
      <TableBlock title="DDJJ preparadas" subtitle="Paquetes anuales listos o en preparación." rows={filteredDdjjs} empty="No hay DDJJ para este filtro." isLoading={isLoading} loadingLabel="Cargando SII..." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Año tributario', render: (row) => row.anio_tributario },
        { label: 'Paquete', render: (row) => row.paquete_ref || 'Sin ref' },
        { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
        { label: 'Responsable', render: (row) => row.responsable_revision_ref || 'Sin responsable' },
        { label: 'Observación', render: (row) => row.observaciones || 'Sin observación' },
        { label: 'Acción', render: (row) => !canEditSii ? 'Solo lectura' : <button type="button" className="button-ghost inline-action" onClick={() => loadAnnualReview('ddjj', row)} disabled={isSubmitting}>Cargar revisión</button> },
      ]} />
      <TableBlock title="F22 preparados" subtitle="Borradores anuales por empresa." rows={filteredF22s} empty="No hay F22 para este filtro." isLoading={isLoading} loadingLabel="Cargando SII..." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Año tributario', render: (row) => row.anio_tributario },
        { label: 'Borrador', render: (row) => row.borrador_ref || 'Sin ref' },
        { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
        { label: 'Responsable', render: (row) => row.responsable_revision_ref || 'Sin responsable' },
        { label: 'Observación', render: (row) => row.observaciones || 'Sin observación' },
        { label: 'Acción', render: (row) => !canEditSii ? 'Solo lectura' : <button type="button" className="button-ghost inline-action" onClick={() => loadAnnualReview('f22', row)} disabled={isSubmitting}>Cargar revisión</button> },
      ]} />
    </>
  )
}
