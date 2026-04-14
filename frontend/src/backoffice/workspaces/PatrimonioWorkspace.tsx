import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock } from '../shared'

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'
type OwnerOption = { tipo: string; id: number; label: string }
type SocioItem = { id: number; nombre: string; rut: string; email: string; telefono: string; domicilio: string; activo: boolean }
type EmpresaItem = { id: number; razon_social: string; rut: string; estado: string; participaciones_detail?: unknown[]; participaciones_count?: number }
type ComunidadItem = { id: number; nombre: string; estado: string; participaciones_detail?: unknown[]; participaciones_count?: number; representacion_vigente: { modo_representacion: string; socio_representante_nombre: string } | null }
type PropiedadItem = { id: number; codigo_propiedad: string; direccion: string; comuna: string; region: string; rol_avaluo: string; tipo_inmueble: string; owner_tipo: string; owner_id: number; owner_display: string; estado: string }
type SocioDraft = { nombre: string; rut: string; email: string; telefono: string; domicilio: string; activo: boolean }
type PropiedadDraft = { codigo_propiedad: string; direccion: string; comuna: string; region: string; rol_avaluo: string; tipo_inmueble: string; estado: string; owner_tipo: string; owner_id: string }

export function PatrimonioWorkspace({
  canEditPatrimonio,
  editingSocioId,
  socioDraft,
  setSocioDraft,
  handleCreateSocio,
  cancelEditSocio,
  editingPropiedadId,
  propiedadDraft,
  setPropiedadDraft,
  handleCreatePropiedad,
  cancelEditPropiedad,
  patrimonioOwners,
  filteredSocios,
  filteredEmpresas,
  filteredComunidades,
  filteredPropiedades,
  toneFor,
  isSubmitting,
  isLoading,
  startEditSocio,
  startEditPropiedad,
  goToEmpresaContext,
  goToEmpresaSiiContext,
  goToPropertyOperationContext,
  canOpenContabilidad,
  canOpenSii,
}: {
  canEditPatrimonio: boolean
  editingSocioId: number | null
  socioDraft: SocioDraft
  setSocioDraft: Dispatch<SetStateAction<SocioDraft>>
  handleCreateSocio: (event: FormEvent<HTMLFormElement>) => Promise<void>
  cancelEditSocio: () => void
  editingPropiedadId: number | null
  propiedadDraft: PropiedadDraft
  setPropiedadDraft: Dispatch<SetStateAction<PropiedadDraft>>
  handleCreatePropiedad: (event: FormEvent<HTMLFormElement>) => Promise<void>
  cancelEditPropiedad: () => void
  patrimonioOwners: OwnerOption[]
  filteredSocios: SocioItem[]
  filteredEmpresas: EmpresaItem[]
  filteredComunidades: ComunidadItem[]
  filteredPropiedades: PropiedadItem[]
  toneFor: (value: string) => Tone
  isSubmitting: boolean
  isLoading: boolean
  startEditSocio: (row: SocioItem) => void
  startEditPropiedad: (row: PropiedadItem) => void
  goToEmpresaContext: (empresaId: number) => void
  goToEmpresaSiiContext: (empresaId: number, razonSocial: string) => void
  goToPropertyOperationContext: (propiedadId: number, codigoPropiedad: string) => void
  canOpenContabilidad: boolean
  canOpenSii: boolean
}) {
  return (
    <>
      {!canEditPatrimonio ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Patrimonio.</div> : null}
      <section className="form-grid">
        <section className="panel">
          <div className="section-heading"><div><h2>{editingSocioId ? 'Editar socio' : 'Alta rápida de socio'}</h2><p>Ingreso mínimo para participantes activos.</p></div></div>
          <form className="entity-form" onSubmit={handleCreateSocio}>
            <input placeholder="Nombre completo" value={socioDraft.nombre} onChange={(event) => setSocioDraft((current) => ({ ...current, nombre: event.target.value }))} />
            <input placeholder="RUT" value={socioDraft.rut} onChange={(event) => setSocioDraft((current) => ({ ...current, rut: event.target.value }))} />
            <input placeholder="Email" value={socioDraft.email} onChange={(event) => setSocioDraft((current) => ({ ...current, email: event.target.value }))} />
            <input placeholder="Teléfono" value={socioDraft.telefono} onChange={(event) => setSocioDraft((current) => ({ ...current, telefono: event.target.value }))} />
            <input placeholder="Domicilio" value={socioDraft.domicilio} onChange={(event) => setSocioDraft((current) => ({ ...current, domicilio: event.target.value }))} />
            <label className="checkbox-row"><input type="checkbox" checked={socioDraft.activo} onChange={(event) => setSocioDraft((current) => ({ ...current, activo: event.target.checked }))} />Activo</label>
            <div className="inline-actions">
              <button type="submit" className="button-primary" disabled={isSubmitting || !canEditPatrimonio}>{editingSocioId ? 'Guardar cambios' : 'Guardar socio'}</button>
              {editingSocioId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditSocio}>Cancelar</button> : null}
            </div>
          </form>
        </section>

        <section className="panel">
          <div className="section-heading"><div><h2>{editingPropiedadId ? 'Editar propiedad' : 'Alta rápida de propiedad'}</h2><p>Owner explícito y código operativo desde el inicio.</p></div></div>
          <form className="entity-form" onSubmit={handleCreatePropiedad}>
            <input placeholder="Código propiedad" value={propiedadDraft.codigo_propiedad} onChange={(event) => setPropiedadDraft((current) => ({ ...current, codigo_propiedad: event.target.value }))} />
            <input placeholder="Dirección" value={propiedadDraft.direccion} onChange={(event) => setPropiedadDraft((current) => ({ ...current, direccion: event.target.value }))} />
            <input placeholder="Comuna" value={propiedadDraft.comuna} onChange={(event) => setPropiedadDraft((current) => ({ ...current, comuna: event.target.value }))} />
            <input placeholder="Región" value={propiedadDraft.region} onChange={(event) => setPropiedadDraft((current) => ({ ...current, region: event.target.value }))} />
            <input placeholder="Rol avalúo" value={propiedadDraft.rol_avaluo} onChange={(event) => setPropiedadDraft((current) => ({ ...current, rol_avaluo: event.target.value }))} />
            <select value={propiedadDraft.tipo_inmueble} onChange={(event) => setPropiedadDraft((current) => ({ ...current, tipo_inmueble: event.target.value }))}>
              <option value="otro">Otro</option><option value="departamento">Departamento</option><option value="casa">Casa</option><option value="local">Local</option><option value="oficina">Oficina</option><option value="bodega">Bodega</option><option value="estacionamiento">Estacionamiento</option>
            </select>
            <select value={propiedadDraft.estado} onChange={(event) => setPropiedadDraft((current) => ({ ...current, estado: event.target.value }))}>
              <option value="borrador">Borrador</option><option value="activa">Activa</option><option value="inactiva">Inactiva</option>
            </select>
            <select value={`${propiedadDraft.owner_tipo}:${propiedadDraft.owner_id}`} onChange={(event) => { const [tipo, id] = event.target.value.split(':'); setPropiedadDraft((current) => ({ ...current, owner_tipo: tipo, owner_id: id || '' })) }}>
              <option value="">Selecciona owner</option>
              {patrimonioOwners.map((owner) => <option key={`${owner.tipo}:${owner.id}`} value={`${owner.tipo}:${owner.id}`}>{owner.label} · {owner.tipo}</option>)}
            </select>
            <div className="inline-actions">
              <button type="submit" className="button-primary" disabled={isSubmitting || !canEditPatrimonio || !propiedadDraft.owner_id}>{editingPropiedadId ? 'Guardar cambios' : 'Guardar propiedad'}</button>
              {editingPropiedadId ? <button type="button" className="button-ghost inline-action" onClick={cancelEditPropiedad}>Cancelar</button> : null}
            </div>
          </form>
        </section>
      </section>

      <TableBlock title="Socios" subtitle="Participantes y representantes activos." rows={filteredSocios} empty="No hay socios para este filtro." isLoading={isLoading} loadingLabel="Cargando patrimonio..." columns={[
        { label: 'Nombre', render: (row) => row.nombre },
        { label: 'RUT', render: (row) => row.rut },
        { label: 'Contacto', render: (row) => row.email || row.telefono || 'Sin dato' },
        { label: 'Estado', render: (row) => <Badge label={row.activo ? 'activo' : 'inactivo'} tone={row.activo ? 'positive' : 'danger'} /> },
        { label: 'Acción', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditSocio(row)}>Editar</button> },
      ]} />
      <TableBlock title="Empresas" subtitle="Owners empresariales y participaciones vigentes." rows={filteredEmpresas} empty="No hay empresas para este filtro." isLoading={isLoading} loadingLabel="Cargando patrimonio..." columns={[
        { label: 'Razón social', render: (row) => row.razon_social },
        { label: 'RUT', render: (row) => row.rut },
        { label: 'Participaciones', render: (row) => String(row.participaciones_count ?? row.participaciones_detail?.length ?? 0) },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Siguiente paso', render: (row) => <div className="inline-actions">{canOpenContabilidad ? <button type="button" className="button-ghost inline-action" onClick={() => goToEmpresaContext(row.id)}>Contabilidad</button> : null}{canOpenSii ? <button type="button" className="button-ghost inline-action" onClick={() => goToEmpresaSiiContext(row.id, row.razon_social)}>SII</button> : null}{!canOpenContabilidad && !canOpenSii ? 'Sin acceso adicional' : null}</div> },
      ]} />
      <TableBlock title="Comunidades" subtitle="Representación vigente y composición comunitaria." rows={filteredComunidades} empty="No hay comunidades para este filtro." isLoading={isLoading} loadingLabel="Cargando patrimonio..." columns={[
        { label: 'Nombre', render: (row) => row.nombre },
        { label: 'Representación', render: (row) => row.representacion_vigente ? `${row.representacion_vigente.socio_representante_nombre} · ${row.representacion_vigente.modo_representacion.replaceAll('_', ' ')}` : 'Sin representación' },
        { label: 'Participaciones', render: (row) => String(row.participaciones_count ?? row.participaciones_detail?.length ?? 0) },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
      ]} />
      <TableBlock title="Propiedades" subtitle="Inventario elegible dentro del greenfield." rows={filteredPropiedades} empty="No hay propiedades para este filtro." isLoading={isLoading} loadingLabel="Cargando patrimonio..." columns={[
        { label: 'Código', render: (row) => row.codigo_propiedad },
        { label: 'Dirección', render: (row) => row.direccion },
        { label: 'Owner', render: (row) => `${row.owner_display} · ${row.owner_tipo.replaceAll('_', ' ')}` },
        { label: 'Ubicación', render: (row) => `${row.comuna}, ${row.region}` },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Editar', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => startEditPropiedad(row)}>Editar</button> },
        { label: 'Siguiente paso', render: (row) => <button type="button" className="button-ghost inline-action" onClick={() => goToPropertyOperationContext(row.id, row.codigo_propiedad)}>Crear mandato</button> },
      ]} />
    </>
  )
}
