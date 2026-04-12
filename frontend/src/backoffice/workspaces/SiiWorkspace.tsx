import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock } from '../shared'

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'

type EmpresaItem = { id: number; razon_social: string }
type PagoItem = { id: number; contrato: number; mes: number; anio: number }
type ContratoItem = { id: number; codigo_contrato: string }
type CapacidadSiiItem = { id: number; empresa: number; capacidad_key: string; ambiente: string; estado_gate: string }
type DteEmitidoItem = { id: number; empresa: number; contrato: number; pago_mensual: number; monto_neto_clp: string; estado_dte: string; sii_track_id: string }
type F29PreparacionItem = { id: number; empresa: number; capacidad_tributaria: number; anio: number; mes: number; estado_preparacion: string; borrador_ref: string }
type ProcesoRentaAnualItem = { id: number; empresa: number; anio_tributario: number; estado: string; fecha_preparacion: string | null }
type DdjjPreparacionItem = { id: number; empresa: number; anio_tributario: number; estado_preparacion: string; paquete_ref: string }
type F22PreparacionItem = { id: number; empresa: number; anio_tributario: number; estado_preparacion: string; borrador_ref: string }

type CapacidadSiiDraft = {
  empresa: string
  capacidad_key: string
  certificado_ref: string
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
  handleSiiStatusUpdate: (path: string, body: Record<string, unknown>, successMessage: string) => Promise<void>
  onViewReporting: (companyId: number) => void
}) {
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
              {pagos.map((item) => <option key={item.id} value={item.id}>{contratoById.get(item.contrato)?.codigo_contrato || item.contrato} · {item.mes}/{item.anio}</option>)}
            </select>
            <select value={dteDraft.tipo_dte} onChange={(event) => setDteDraft((current) => ({ ...current, tipo_dte: event.target.value }))}>
              <option value="34">34 · Factura Exenta</option>
              <option value="56">56 · Nota Débito</option>
              <option value="61">61 · Nota Crédito</option>
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
      </section> : null}

      <TableBlock title="Capacidades SII" subtitle="Gate y ambiente por empresa/capacidad." rows={filteredCapacidadesSii} empty="No hay capacidades SII para este filtro." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Capacidad', render: (row) => row.capacidad_key },
        { label: 'Ambiente', render: (row) => row.ambiente },
        { label: 'Estado', render: (row) => <Badge label={row.estado_gate} tone={toneFor(row.estado_gate)} /> },
      ]} />
      <TableBlock title="DTE emitidos" subtitle="Borradores y estados manuales de DTE." rows={filteredDtes} empty="No hay DTE para este filtro." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
        { label: 'Pago', render: (row) => row.pago_mensual },
        { label: 'Monto', render: (row) => row.monto_neto_clp },
        { label: 'Estado', render: (row) => <Badge label={row.estado_dte} tone={toneFor(row.estado_dte)} /> },
        { label: 'Acción', render: (row) => !canEditSii ? 'Solo lectura' : <div className="inline-actions"><button type="button" className="button-ghost inline-action" onClick={() => void handleSiiStatusUpdate(`/api/v1/sii/dtes/${row.id}/estado/`, { estado_dte: 'aceptado', sii_track_id: row.sii_track_id || 'TRACK-LOCAL', ultimo_estado_sii: 'ACEPTADO' }, 'Estado DTE actualizado correctamente.')} disabled={isSubmitting}>Marcar aceptado</button><button type="button" className="button-ghost inline-action" onClick={() => onViewReporting(row.empresa)}>Reporting</button></div> },
      ]} />
      <TableBlock title="F29 mensuales" subtitle="Preparación mensual desde cierres aprobados." rows={filteredF29s} empty="No hay F29 para este filtro." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Período', render: (row) => `${row.mes}/${row.anio}` },
        { label: 'Capacidad', render: (row) => capacidadSiiById.get(row.capacidad_tributaria)?.capacidad_key || row.capacidad_tributaria },
        { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
        { label: 'Acción', render: (row) => !canEditSii ? 'Solo lectura' : <button type="button" className="button-ghost inline-action" onClick={() => void handleSiiStatusUpdate(`/api/v1/sii/f29/${row.id}/estado/`, { estado_preparacion: 'preparado', borrador_ref: row.borrador_ref || 'F29-LOCAL' }, 'Estado F29 actualizado correctamente.')} disabled={isSubmitting}>Actualizar estado</button> },
      ]} />
      <TableBlock title="Proceso renta anual" subtitle="Proceso consolidado por empresa y año tributario." rows={filteredProcesosAnuales} empty="No hay procesos anuales para este filtro." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Año tributario', render: (row) => row.anio_tributario },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Preparación', render: (row) => row.fecha_preparacion || 'Sin fecha' },
      ]} />
      <TableBlock title="DDJJ preparadas" subtitle="Paquetes anuales listos o en preparación." rows={filteredDdjjs} empty="No hay DDJJ para este filtro." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Año tributario', render: (row) => row.anio_tributario },
        { label: 'Paquete', render: (row) => row.paquete_ref || 'Sin ref' },
        { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
        { label: 'Acción', render: (row) => !canEditSii ? 'Solo lectura' : <button type="button" className="button-ghost inline-action" onClick={() => void handleSiiStatusUpdate(`/api/v1/sii/anual/ddjj/${row.id}/estado/`, { estado_preparacion: 'preparado', ref_value: row.paquete_ref || 'DDJJ-LOCAL' }, 'Estado DDJJ actualizado correctamente.')} disabled={isSubmitting}>Actualizar estado</button> },
      ]} />
      <TableBlock title="F22 preparados" subtitle="Borradores anuales por empresa." rows={filteredF22s} empty="No hay F22 para este filtro." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Año tributario', render: (row) => row.anio_tributario },
        { label: 'Borrador', render: (row) => row.borrador_ref || 'Sin ref' },
        { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
        { label: 'Acción', render: (row) => !canEditSii ? 'Solo lectura' : <button type="button" className="button-ghost inline-action" onClick={() => void handleSiiStatusUpdate(`/api/v1/sii/anual/f22/${row.id}/estado/`, { estado_preparacion: 'preparado', ref_value: row.borrador_ref || 'F22-LOCAL' }, 'Estado F22 actualizado correctamente.')} disabled={isSubmitting}>Actualizar estado</button> },
      ]} />
    </>
  )
}
