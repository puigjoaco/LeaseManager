import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock } from '../shared'

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'

type CanalMensajeriaItem = {
  id: number
  canal: string
  provider_key: string
  estado_gate: string
  evidencia_ref: string
}

type MensajeSalienteItem = {
  id: number
  canal: string
  contrato: number | null
  documento_emitido: number | null
  destinatario: string
  asunto: string
  cuerpo: string
  estado: string
  motivo_bloqueo: string
  external_ref: string
}

type IdentidadItem = {
  id: number
  canal: string
  remitente_visible: string
  direccion_o_numero: string
}

type ContratoItem = {
  id: number
  codigo_contrato: string
}

type ArrendatarioItem = {
  id: number
  nombre_razon_social: string
}

type DocumentoEmitidoItem = {
  id: number
  tipo_documental: string
  storage_ref: string
}

type GateCanalDraft = {
  canal: string
  provider_key: string
  estado_gate: string
  evidencia_ref: string
}

type MensajeDraft = {
  canal: string
  canal_mensajeria: string
  identidad_envio: string
  contrato: string
  arrendatario: string
  documento_emitido: string
  asunto: string
  cuerpo: string
}

type MensajeEnvioDraft = {
  mensajeId: string
  external_ref: string
}

export function CanalesWorkspace({
  canEditCanales,
  gateCanalDraft,
  setGateCanalDraft,
  handleCreateGateCanal,
  mensajeDraft,
  setMensajeDraft,
  handlePrepareMensaje,
  mensajeEnvioDraft,
  setMensajeEnvioDraft,
  handleRegistrarEnvioMensaje,
  gatesCanales,
  identidades,
  contratos,
  arrendatarios,
  documentosEmitidos,
  mensajesSalientes,
  filteredGatesCanales,
  filteredMensajesSalientes,
  isSubmitting,
  contratoById,
  toneFor,
}: {
  canEditCanales: boolean
  gateCanalDraft: GateCanalDraft
  setGateCanalDraft: Dispatch<SetStateAction<GateCanalDraft>>
  handleCreateGateCanal: (event: FormEvent<HTMLFormElement>) => Promise<void>
  mensajeDraft: MensajeDraft
  setMensajeDraft: Dispatch<SetStateAction<MensajeDraft>>
  handlePrepareMensaje: (event: FormEvent<HTMLFormElement>) => Promise<void>
  mensajeEnvioDraft: MensajeEnvioDraft
  setMensajeEnvioDraft: Dispatch<SetStateAction<MensajeEnvioDraft>>
  handleRegistrarEnvioMensaje: (event: FormEvent<HTMLFormElement>) => Promise<void>
  gatesCanales: CanalMensajeriaItem[]
  identidades: IdentidadItem[]
  contratos: ContratoItem[]
  arrendatarios: ArrendatarioItem[]
  documentosEmitidos: DocumentoEmitidoItem[]
  mensajesSalientes: MensajeSalienteItem[]
  filteredGatesCanales: CanalMensajeriaItem[]
  filteredMensajesSalientes: MensajeSalienteItem[]
  isSubmitting: boolean
  contratoById: ReadonlyMap<number, ContratoItem>
  toneFor: (value: string) => Tone
}) {
  const documentoById = new Map(documentosEmitidos.map((item) => [item.id, item]))

  return (
    <>
      {!canEditCanales ? <div className="readonly-banner">Tu rol actual tiene acceso de solo lectura en Canales.</div> : null}
      {canEditCanales ? (
        <section className="form-grid">
          <section className="panel">
            <div className="section-heading"><div><h2>Gate de canal</h2><p>Estado operativo por canal y provider.</p></div></div>
            <form className="entity-form" onSubmit={handleCreateGateCanal}>
              <select value={gateCanalDraft.canal} onChange={(event) => setGateCanalDraft((current) => ({ ...current, canal: event.target.value }))}>
                <option value="email">Email</option>
                <option value="whatsapp">WhatsApp</option>
              </select>
              <input placeholder="Provider key" value={gateCanalDraft.provider_key} onChange={(event) => setGateCanalDraft((current) => ({ ...current, provider_key: event.target.value }))} />
              <select value={gateCanalDraft.estado_gate} onChange={(event) => setGateCanalDraft((current) => ({ ...current, estado_gate: event.target.value }))}>
                <option value="abierto">Abierto</option>
                <option value="condicionado">Condicionado</option>
                <option value="cerrado">Cerrado</option>
                <option value="suspendido">Suspendido</option>
              </select>
              <input placeholder="Evidencia ref" value={gateCanalDraft.evidencia_ref} onChange={(event) => setGateCanalDraft((current) => ({ ...current, evidencia_ref: event.target.value }))} />
              <button type="submit" className="button-primary" disabled={isSubmitting || !gateCanalDraft.provider_key}>Guardar gate</button>
            </form>
          </section>

          <section className="panel">
            <div className="section-heading"><div><h2>Preparar mensaje</h2><p>Usa contrato, arrendatario o documento como contexto del envío.</p></div></div>
            <form className="entity-form" onSubmit={handlePrepareMensaje}>
              <select value={mensajeDraft.canal} onChange={(event) => setMensajeDraft((current) => ({ ...current, canal: event.target.value }))}>
                <option value="email">Email</option>
                <option value="whatsapp">WhatsApp</option>
              </select>
              <select value={mensajeDraft.canal_mensajeria} onChange={(event) => setMensajeDraft((current) => ({ ...current, canal_mensajeria: event.target.value }))}>
                <option value="">Selecciona gate</option>
                {gatesCanales.filter((item) => item.canal === mensajeDraft.canal).map((item) => (
                  <option key={item.id} value={item.id}>{item.canal} · {item.provider_key}</option>
                ))}
              </select>
              <select value={mensajeDraft.identidad_envio} onChange={(event) => setMensajeDraft((current) => ({ ...current, identidad_envio: event.target.value }))}>
                <option value="">Sin override de identidad</option>
                {identidades.filter((item) => item.canal === mensajeDraft.canal).map((item) => (
                  <option key={item.id} value={item.id}>{item.remitente_visible} · {item.direccion_o_numero}</option>
                ))}
              </select>
              <select value={mensajeDraft.contrato} onChange={(event) => setMensajeDraft((current) => ({ ...current, contrato: event.target.value }))}>
                <option value="">Sin contrato</option>
                {contratos.map((item) => (
                  <option key={item.id} value={item.id}>{item.codigo_contrato}</option>
                ))}
              </select>
              <select value={mensajeDraft.arrendatario} onChange={(event) => setMensajeDraft((current) => ({ ...current, arrendatario: event.target.value }))}>
                <option value="">Sin arrendatario</option>
                {arrendatarios.map((item) => (
                  <option key={item.id} value={item.id}>{item.nombre_razon_social}</option>
                ))}
              </select>
              <select value={mensajeDraft.documento_emitido} onChange={(event) => setMensajeDraft((current) => ({ ...current, documento_emitido: event.target.value }))}>
                <option value="">Sin documento</option>
                {documentosEmitidos.map((item) => (
                  <option key={item.id} value={item.id}>{item.tipo_documental} · {item.storage_ref}</option>
                ))}
              </select>
              <input placeholder="Asunto" value={mensajeDraft.asunto} onChange={(event) => setMensajeDraft((current) => ({ ...current, asunto: event.target.value }))} />
              <input placeholder="Cuerpo" value={mensajeDraft.cuerpo} onChange={(event) => setMensajeDraft((current) => ({ ...current, cuerpo: event.target.value }))} />
              <button type="submit" className="button-primary" disabled={isSubmitting || !mensajeDraft.canal_mensajeria}>Preparar mensaje</button>
            </form>
          </section>

          <section className="panel">
            <div className="section-heading"><div><h2>Registrar envío</h2><p>Marca un mensaje preparado como enviado manualmente.</p></div></div>
            <form className="entity-form" onSubmit={handleRegistrarEnvioMensaje}>
              <select value={mensajeEnvioDraft.mensajeId} onChange={(event) => setMensajeEnvioDraft((current) => ({ ...current, mensajeId: event.target.value }))}>
                <option value="">Selecciona mensaje</option>
                {mensajesSalientes.filter((item) => item.estado === 'preparado').map((item) => (
                  <option key={item.id} value={item.id}>{item.canal} · {item.destinatario || item.asunto || item.id}</option>
                ))}
              </select>
              <input placeholder="External ref" value={mensajeEnvioDraft.external_ref} onChange={(event) => setMensajeEnvioDraft((current) => ({ ...current, external_ref: event.target.value }))} />
              <button type="submit" className="button-primary" disabled={isSubmitting || !mensajeEnvioDraft.mensajeId}>Registrar envío</button>
            </form>
          </section>
        </section>
      ) : null}

      <TableBlock title="Gates de canal" subtitle="Estado operativo por canal." rows={filteredGatesCanales} empty="No hay gates de canal para este filtro." columns={[
        { label: 'Canal', render: (row) => row.canal },
        { label: 'Provider', render: (row) => row.provider_key },
        { label: 'Estado', render: (row) => <Badge label={row.estado_gate} tone={toneFor(row.estado_gate)} /> },
        { label: 'Evidencia', render: (row) => row.evidencia_ref || 'Sin evidencia' },
      ]} />

      <TableBlock title="Mensajes salientes" subtitle="Preparados, bloqueados o enviados manualmente." rows={filteredMensajesSalientes} empty="No hay mensajes salientes para este filtro." columns={[
        { label: 'Canal', render: (row) => row.canal },
        { label: 'Destinatario', render: (row) => row.destinatario || 'Sin destinatario' },
        { label: 'Contrato', render: (row) => row.contrato ? (contratoById.get(row.contrato)?.codigo_contrato || row.contrato) : 'Sin contrato' },
        { label: 'Documento', render: (row) => row.documento_emitido ? (documentoById.get(row.documento_emitido)?.storage_ref || row.documento_emitido) : 'Sin documento' },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Motivo', render: (row) => row.motivo_bloqueo || row.external_ref || 'Sin observación' },
      ]} />
    </>
  )
}
