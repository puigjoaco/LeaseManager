import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock } from '../shared'

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'

type EmpresaItem = { id: number; razon_social: string }
type RegimenTributarioItem = { id: number; codigo_regimen: string; descripcion: string; estado: string }
type ConfiguracionFiscalItem = { id: number; empresa: number; regimen_tributario: number; moneda_funcional: string; aplica_ppm: boolean; estado: string }
type CuentaContableItem = { id: number; empresa: number; codigo: string; nombre: string; naturaleza: string; estado: string }
type ReglaContableItem = { id: number; empresa: number; evento_tipo: string; plan_cuentas_version: string; criterio_cargo: string; criterio_abono: string }
type MatrizReglaItem = { id: number; regla_contable: number; cuenta_debe: number; cuenta_haber: number; condicion_impuesto: string; estado: string }
type EventoContableItem = { id: number; empresa: number | null; evento_tipo: string; entidad_origen_tipo: string; entidad_origen_id: string; monto_base: string; estado_contable: string }
type AsientoContableItem = { id: number; evento_contable: number; periodo_contable: string; debe_total: string; haber_total: string; estado: string }
type ObligacionMensualItem = { id: number; empresa: number; anio: number; mes: number; obligacion_tipo: string; monto_calculado: string; estado_preparacion: string }
type CierreMensualItem = { id: number; empresa: number; anio: number; mes: number; estado: string }

type ConfigFiscalDraft = {
  empresa: string
  regimen_tributario: string
  afecta_iva_arriendo: boolean
  tasa_iva: string
  aplica_ppm: boolean
  inicio_ejercicio: string
  moneda_funcional: string
  estado: string
}

type CuentaContableDraft = {
  empresa: string
  plan_cuentas_version: string
  codigo: string
  nombre: string
  naturaleza: string
  nivel: string
  padre: string
  estado: string
  es_control_obligatoria: boolean
}

type ReglaContableDraft = {
  empresa: string
  evento_tipo: string
  plan_cuentas_version: string
  criterio_cargo: string
  criterio_abono: string
  vigencia_desde: string
  vigencia_hasta: string
  estado: string
}

type MatrizDraft = {
  regla_contable: string
  cuenta_debe: string
  cuenta_haber: string
  condicion_impuesto: string
  estado: string
}

type EventoContableDraft = {
  empresa: string
  evento_tipo: string
  entidad_origen_tipo: string
  entidad_origen_id: string
  fecha_operativa: string
  moneda: string
  monto_base: string
  payload_resumen: string
  idempotency_key: string
}

type CierreDraft = {
  empresa_id: string
  anio: string
  mes: string
}

export function ContabilidadWorkspace({
  canEditContabilidad,
  configFiscalDraft,
  setConfigFiscalDraft,
  handleCreateConfigFiscal,
  cuentaContableDraft,
  setCuentaContableDraft,
  handleCreateCuentaContable,
  reglaContableDraft,
  setReglaContableDraft,
  handleCreateReglaContable,
  matrizDraft,
  setMatrizDraft,
  handleCreateMatriz,
  eventoContableDraft,
  setEventoContableDraft,
  handleCreateEventoContable,
  cierreDraft,
  setCierreDraft,
  handlePrepareCierre,
  filteredRegimenes,
  filteredConfigsFiscales,
  filteredCuentasContables,
  filteredReglasContables,
  filteredMatrices,
  filteredEventosContables,
  filteredAsientosContables,
  filteredObligaciones,
  filteredCierres,
  empresas,
  regimenesTributarios,
  cuentasContables,
  reglasContables,
  empresaById,
  regimenById,
  reglaById,
  cuentaContableById,
  toneFor,
  isSubmitting,
  handleAccountingAction,
  onViewImpact,
}: {
  canEditContabilidad: boolean
  configFiscalDraft: ConfigFiscalDraft
  setConfigFiscalDraft: Dispatch<SetStateAction<ConfigFiscalDraft>>
  handleCreateConfigFiscal: (event: FormEvent<HTMLFormElement>) => Promise<void>
  cuentaContableDraft: CuentaContableDraft
  setCuentaContableDraft: Dispatch<SetStateAction<CuentaContableDraft>>
  handleCreateCuentaContable: (event: FormEvent<HTMLFormElement>) => Promise<void>
  reglaContableDraft: ReglaContableDraft
  setReglaContableDraft: Dispatch<SetStateAction<ReglaContableDraft>>
  handleCreateReglaContable: (event: FormEvent<HTMLFormElement>) => Promise<void>
  matrizDraft: MatrizDraft
  setMatrizDraft: Dispatch<SetStateAction<MatrizDraft>>
  handleCreateMatriz: (event: FormEvent<HTMLFormElement>) => Promise<void>
  eventoContableDraft: EventoContableDraft
  setEventoContableDraft: Dispatch<SetStateAction<EventoContableDraft>>
  handleCreateEventoContable: (event: FormEvent<HTMLFormElement>) => Promise<void>
  cierreDraft: CierreDraft
  setCierreDraft: Dispatch<SetStateAction<CierreDraft>>
  handlePrepareCierre: (event: FormEvent<HTMLFormElement>) => Promise<void>
  filteredRegimenes: RegimenTributarioItem[]
  filteredConfigsFiscales: ConfiguracionFiscalItem[]
  filteredCuentasContables: CuentaContableItem[]
  filteredReglasContables: ReglaContableItem[]
  filteredMatrices: MatrizReglaItem[]
  filteredEventosContables: EventoContableItem[]
  filteredAsientosContables: AsientoContableItem[]
  filteredObligaciones: ObligacionMensualItem[]
  filteredCierres: CierreMensualItem[]
  empresas: EmpresaItem[]
  regimenesTributarios: RegimenTributarioItem[]
  cuentasContables: CuentaContableItem[]
  reglasContables: ReglaContableItem[]
  empresaById: ReadonlyMap<number, EmpresaItem>
  regimenById: ReadonlyMap<number, RegimenTributarioItem>
  reglaById: ReadonlyMap<number, ReglaContableItem>
  cuentaContableById: ReadonlyMap<number, CuentaContableItem>
  toneFor: (value: string) => Tone
  isSubmitting: boolean
  handleAccountingAction: (path: string, successMessage: string) => Promise<void>
  onViewImpact: (companyId: number) => void
}) {
  return (
    <>
      {!canEditContabilidad ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Contabilidad.</div> : null}
      {canEditContabilidad ? <section className="form-grid">
        <section className="panel">
          <div className="section-heading"><div><h2>Configuración fiscal</h2><p>Prerequisito para contabilización y cierre mensual oficial.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateConfigFiscal}>
            <select value={configFiscalDraft.empresa} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, empresa: event.target.value }))}>
              <option value="">Selecciona empresa</option>
              {empresas.map((item) => <option key={item.id} value={item.id}>{item.razon_social}</option>)}
            </select>
            <select value={configFiscalDraft.regimen_tributario} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, regimen_tributario: event.target.value }))}>
              <option value="">Selecciona régimen</option>
              {regimenesTributarios.map((item) => <option key={item.id} value={item.id}>{item.codigo_regimen}</option>)}
            </select>
            <input type="date" value={configFiscalDraft.inicio_ejercicio} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, inicio_ejercicio: event.target.value }))} />
            <select value={configFiscalDraft.moneda_funcional} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, moneda_funcional: event.target.value }))}>
              <option value="CLP">CLP</option>
              <option value="UF">UF</option>
            </select>
            <input placeholder="Tasa IVA" value={configFiscalDraft.tasa_iva} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, tasa_iva: event.target.value }))} />
            <select value={configFiscalDraft.estado} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, estado: event.target.value }))}>
              <option value="activa">Activa</option>
              <option value="borrador">Borrador</option>
              <option value="inactiva">Inactiva</option>
            </select>
            <label className="checkbox-row"><input type="checkbox" checked={configFiscalDraft.afecta_iva_arriendo} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, afecta_iva_arriendo: event.target.checked }))} />Afecta IVA arriendo</label>
            <label className="checkbox-row"><input type="checkbox" checked={configFiscalDraft.aplica_ppm} onChange={(event) => setConfigFiscalDraft((current) => ({ ...current, aplica_ppm: event.target.checked }))} />Aplica PPM</label>
            <button type="submit" className="button-primary" disabled={isSubmitting || !configFiscalDraft.empresa || !configFiscalDraft.regimen_tributario}>Guardar configuración</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Cuenta contable</h2><p>Plan mínimo para reglas y asientos.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateCuentaContable}>
            <select value={cuentaContableDraft.empresa} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, empresa: event.target.value }))}>
              <option value="">Selecciona empresa</option>
              {empresas.map((item) => <option key={item.id} value={item.id}>{item.razon_social}</option>)}
            </select>
            <input placeholder="Versión plan" value={cuentaContableDraft.plan_cuentas_version} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, plan_cuentas_version: event.target.value }))} />
            <input placeholder="Código" value={cuentaContableDraft.codigo} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, codigo: event.target.value }))} />
            <input placeholder="Nombre" value={cuentaContableDraft.nombre} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, nombre: event.target.value }))} />
            <select value={cuentaContableDraft.naturaleza} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, naturaleza: event.target.value }))}>
              <option value="deudora">Deudora</option>
              <option value="acreedora">Acreedora</option>
            </select>
            <input placeholder="Nivel" value={cuentaContableDraft.nivel} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, nivel: event.target.value }))} />
            <select value={cuentaContableDraft.padre} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, padre: event.target.value }))}>
              <option value="">Sin padre</option>
              {cuentasContables.filter((item) => !cuentaContableDraft.empresa || item.empresa === Number(cuentaContableDraft.empresa)).map((item) => (
                <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}</option>
              ))}
            </select>
            <select value={cuentaContableDraft.estado} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, estado: event.target.value }))}>
              <option value="activa">Activa</option>
              <option value="inactiva">Inactiva</option>
            </select>
            <label className="checkbox-row"><input type="checkbox" checked={cuentaContableDraft.es_control_obligatoria} onChange={(event) => setCuentaContableDraft((current) => ({ ...current, es_control_obligatoria: event.target.checked }))} />Cuenta de control obligatoria</label>
            <button type="submit" className="button-primary" disabled={isSubmitting || !cuentaContableDraft.empresa || !cuentaContableDraft.codigo || !cuentaContableDraft.nombre}>Guardar cuenta</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Regla y matriz</h2><p>Relaciona evento contable con cuentas debe/haber.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateReglaContable}>
            <select value={reglaContableDraft.empresa} onChange={(event) => setReglaContableDraft((current) => ({ ...current, empresa: event.target.value }))}>
              <option value="">Selecciona empresa</option>
              {empresas.map((item) => <option key={item.id} value={item.id}>{item.razon_social}</option>)}
            </select>
            <input placeholder="Evento tipo" value={reglaContableDraft.evento_tipo} onChange={(event) => setReglaContableDraft((current) => ({ ...current, evento_tipo: event.target.value }))} />
            <input placeholder="Versión plan" value={reglaContableDraft.plan_cuentas_version} onChange={(event) => setReglaContableDraft((current) => ({ ...current, plan_cuentas_version: event.target.value }))} />
            <input placeholder="Criterio cargo" value={reglaContableDraft.criterio_cargo} onChange={(event) => setReglaContableDraft((current) => ({ ...current, criterio_cargo: event.target.value }))} />
            <input placeholder="Criterio abono" value={reglaContableDraft.criterio_abono} onChange={(event) => setReglaContableDraft((current) => ({ ...current, criterio_abono: event.target.value }))} />
            <input type="date" value={reglaContableDraft.vigencia_desde} onChange={(event) => setReglaContableDraft((current) => ({ ...current, vigencia_desde: event.target.value }))} />
            <button type="submit" className="button-primary" disabled={isSubmitting || !reglaContableDraft.empresa || !reglaContableDraft.evento_tipo}>Guardar regla</button>
          </form>
          <form className="entity-form subform" onSubmit={handleCreateMatriz}>
            <select value={matrizDraft.regla_contable} onChange={(event) => setMatrizDraft((current) => ({ ...current, regla_contable: event.target.value }))}>
              <option value="">Selecciona regla</option>
              {reglasContables.map((item) => <option key={item.id} value={item.id}>{item.evento_tipo} · {empresaById.get(item.empresa)?.razon_social || item.empresa}</option>)}
            </select>
            <select value={matrizDraft.cuenta_debe} onChange={(event) => setMatrizDraft((current) => ({ ...current, cuenta_debe: event.target.value }))}>
              <option value="">Cuenta debe</option>
              {cuentasContables.map((item) => <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}</option>)}
            </select>
            <select value={matrizDraft.cuenta_haber} onChange={(event) => setMatrizDraft((current) => ({ ...current, cuenta_haber: event.target.value }))}>
              <option value="">Cuenta haber</option>
              {cuentasContables.map((item) => <option key={item.id} value={item.id}>{item.codigo} · {item.nombre}</option>)}
            </select>
            <input placeholder="Condición impuesto" value={matrizDraft.condicion_impuesto} onChange={(event) => setMatrizDraft((current) => ({ ...current, condicion_impuesto: event.target.value }))} />
            <button type="submit" className="button-secondary" disabled={isSubmitting || !matrizDraft.regla_contable || !matrizDraft.cuenta_debe || !matrizDraft.cuenta_haber}>Guardar matriz</button>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>Evento y cierre</h2><p>Evento manual, preparación y acciones sobre cierres.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateEventoContable}>
            <select value={eventoContableDraft.empresa} onChange={(event) => setEventoContableDraft((current) => ({ ...current, empresa: event.target.value }))}>
              <option value="">Selecciona empresa</option>
              {empresas.map((item) => <option key={item.id} value={item.id}>{item.razon_social}</option>)}
            </select>
            <input placeholder="Evento tipo" value={eventoContableDraft.evento_tipo} onChange={(event) => setEventoContableDraft((current) => ({ ...current, evento_tipo: event.target.value }))} />
            <input placeholder="Entidad origen tipo" value={eventoContableDraft.entidad_origen_tipo} onChange={(event) => setEventoContableDraft((current) => ({ ...current, entidad_origen_tipo: event.target.value }))} />
            <input placeholder="Entidad origen id" value={eventoContableDraft.entidad_origen_id} onChange={(event) => setEventoContableDraft((current) => ({ ...current, entidad_origen_id: event.target.value }))} />
            <input type="date" value={eventoContableDraft.fecha_operativa} onChange={(event) => setEventoContableDraft((current) => ({ ...current, fecha_operativa: event.target.value }))} />
            <input placeholder="Monto base" value={eventoContableDraft.monto_base} onChange={(event) => setEventoContableDraft((current) => ({ ...current, monto_base: event.target.value }))} />
            <input placeholder="Idempotency key" value={eventoContableDraft.idempotency_key} onChange={(event) => setEventoContableDraft((current) => ({ ...current, idempotency_key: event.target.value }))} />
            <input placeholder="Payload resumen JSON" value={eventoContableDraft.payload_resumen} onChange={(event) => setEventoContableDraft((current) => ({ ...current, payload_resumen: event.target.value }))} />
            <button type="submit" className="button-primary" disabled={isSubmitting || !eventoContableDraft.empresa || !eventoContableDraft.monto_base || !eventoContableDraft.idempotency_key}>Guardar evento</button>
          </form>
          <form className="entity-form subform" onSubmit={handlePrepareCierre}>
            <select value={cierreDraft.empresa_id} onChange={(event) => setCierreDraft((current) => ({ ...current, empresa_id: event.target.value }))}>
              <option value="">Selecciona empresa</option>
              {empresas.map((item) => <option key={item.id} value={item.id}>{item.razon_social}</option>)}
            </select>
            <input placeholder="Año" value={cierreDraft.anio} onChange={(event) => setCierreDraft((current) => ({ ...current, anio: event.target.value }))} />
            <input placeholder="Mes" value={cierreDraft.mes} onChange={(event) => setCierreDraft((current) => ({ ...current, mes: event.target.value }))} />
            <button type="submit" className="button-secondary" disabled={isSubmitting || !cierreDraft.empresa_id}>Preparar cierre</button>
          </form>
        </section>
      </section> : null}

      <TableBlock title="Regímenes tributarios" subtitle="Regímenes disponibles para configuración fiscal." rows={filteredRegimenes} empty="No hay regímenes para este filtro." columns={[
        { label: 'Código', render: (row) => row.codigo_regimen },
        { label: 'Descripción', render: (row) => row.descripcion },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />
      <TableBlock title="Configuraciones fiscales" subtitle="Estado fiscal activo por empresa." rows={filteredConfigsFiscales} empty="No hay configuraciones fiscales para este filtro." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Régimen', render: (row) => regimenById.get(row.regimen_tributario)?.codigo_regimen || row.regimen_tributario },
        { label: 'Moneda', render: (row) => row.moneda_funcional },
        { label: 'PPM', render: (row) => row.aplica_ppm ? 'Sí' : 'No' },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />
      <TableBlock title="Cuentas contables" subtitle="Plan contable disponible por empresa." rows={filteredCuentasContables} empty="No hay cuentas contables para este filtro." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Código', render: (row) => row.codigo },
        { label: 'Nombre', render: (row) => row.nombre },
        { label: 'Naturaleza', render: (row) => row.naturaleza },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />
      <TableBlock title="Reglas y matrices" subtitle="Mapeo entre eventos y cuentas debe/haber." rows={filteredReglasContables} empty="No hay reglas contables para este filtro." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Evento', render: (row) => row.evento_tipo },
        { label: 'Versión', render: (row) => row.plan_cuentas_version },
        { label: 'Cargo', render: (row) => row.criterio_cargo || 'Sin criterio' },
        { label: 'Abono', render: (row) => row.criterio_abono || 'Sin criterio' },
      ]} />
      <TableBlock title="Matrices de reglas" subtitle="Detalle de cuentas usadas por regla activa." rows={filteredMatrices} empty="No hay matrices para este filtro." columns={[
        { label: 'Regla', render: (row) => reglaById.get(row.regla_contable)?.evento_tipo || row.regla_contable },
        { label: 'Debe', render: (row) => cuentaContableById.get(row.cuenta_debe)?.codigo || row.cuenta_debe },
        { label: 'Haber', render: (row) => cuentaContableById.get(row.cuenta_haber)?.codigo || row.cuenta_haber },
        { label: 'Condición', render: (row) => row.condicion_impuesto || 'Sin condición' },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />
      <TableBlock title="Eventos contables" subtitle="Hechos económicos pendientes, en revisión o contabilizados." rows={filteredEventosContables} empty="No hay eventos contables para este filtro." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa || 0)?.razon_social || row.empresa || 'Sin empresa' },
        { label: 'Evento', render: (row) => row.evento_tipo },
        { label: 'Origen', render: (row) => `${row.entidad_origen_tipo}:${row.entidad_origen_id}` },
        { label: 'Monto', render: (row) => row.monto_base },
        { label: 'Estado', render: (row) => <Badge label={row.estado_contable} tone={toneFor(row.estado_contable)} /> },
        {
          label: 'Acción',
          render: (row) => {
            const companyId = row.empresa
            return !canEditContabilidad ? 'Solo lectura' : (
              <div className="inline-actions">
                <button type="button" className="button-ghost inline-action" onClick={() => void handleAccountingAction(`/api/v1/contabilidad/eventos-contables/${row.id}/contabilizar/`, 'Reintento de contabilización ejecutado correctamente.')} disabled={isSubmitting}>Contabilizar</button>
                {companyId != null ? <button type="button" className="button-ghost inline-action" onClick={() => onViewImpact(companyId)}>Ver impacto</button> : null}
              </div>
            )
          },
        },
      ]} />
      <TableBlock title="Asientos contables" subtitle="Asientos balanceados generados desde eventos." rows={filteredAsientosContables} empty="No hay asientos para este filtro." columns={[
        { label: 'Evento', render: (row) => row.evento_contable },
        { label: 'Período', render: (row) => row.periodo_contable },
        { label: 'Debe', render: (row) => row.debe_total },
        { label: 'Haber', render: (row) => row.haber_total },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />
      <TableBlock title="Obligaciones mensuales" subtitle="PPM e impuestos preparados desde los cierres." rows={filteredObligaciones} empty="No hay obligaciones mensuales para este filtro." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Período', render: (row) => `${row.mes}/${row.anio}` },
        { label: 'Tipo', render: (row) => row.obligacion_tipo },
        { label: 'Monto', render: (row) => row.monto_calculado },
        { label: 'Estado', render: (row) => <Badge label={row.estado_preparacion} tone={toneFor(row.estado_preparacion)} /> },
      ]} />
      <TableBlock title="Cierres mensuales" subtitle="Preparación, aprobación y reapertura del período." rows={filteredCierres} empty="No hay cierres mensuales para este filtro." columns={[
        { label: 'Empresa', render: (row) => empresaById.get(row.empresa)?.razon_social || row.empresa },
        { label: 'Período', render: (row) => `${row.mes}/${row.anio}` },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Acción', render: (row) => !canEditContabilidad ? 'Solo lectura' : <div className="inline-actions"><button type="button" className="button-ghost inline-action" onClick={() => void handleAccountingAction(`/api/v1/contabilidad/cierres-mensuales/${row.id}/aprobar/`, 'Cierre aprobado correctamente.')} disabled={isSubmitting}>Aprobar</button><button type="button" className="button-ghost inline-action" onClick={() => void handleAccountingAction(`/api/v1/contabilidad/cierres-mensuales/${row.id}/reabrir/`, 'Cierre reabierto correctamente.')} disabled={isSubmitting}>Reabrir</button></div> },
      ]} />
    </>
  )
}
