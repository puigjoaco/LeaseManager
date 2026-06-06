import type { Dispatch, FormEvent, SetStateAction } from 'react'

import { Badge, TableBlock } from '../shared'

type Tone = 'neutral' | 'positive' | 'warning' | 'danger'

type CanalMensajeriaItem = {
  id: number
  canal: string
  provider_key: string
  estado_gate: string
  restricciones_operativas: Record<string, unknown>
  evidencia_ref: string
}

type MensajeSalienteItem = {
  id: number
  canal: string
  canal_mensajeria: number
  identidad_envio: number | null
  contrato: number | null
  arrendatario: number | null
  documento_emitido: number | null
  destinatario: string
  asunto: string
  cuerpo: string
  estado: string
  motivo_bloqueo: string
  external_ref: string
  usuario: number | null
  provider_payload: Record<string, unknown>
  enviado_at: string | null
}

type ConfiguracionNotificacionItem = {
  id: number
  contrato: number
  canal: string
  dias_notificacion: number[]
  activa: boolean
  evidencia_configuracion_ref: string
}

type NotificacionCobranzaItem = {
  id: number
  pago_mensual: number
  contrato: number
  arrendatario: number | null
  pago_anio: number
  pago_mes: number
  pago_estado: string
  pago_fecha_vencimiento: string
  pago_monto_facturable_clp: string
  configuracion: number
  configuracion_activa: boolean
  configuracion_dias_notificacion: number[]
  canal: string
  dia_notificacion: number
  fecha_programada: string
  estado: string
  mensaje_saliente: number | null
  motivo_estado: string
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
  prueba_aislada_ref: string
  oauth_validado_ref: string
  credencial_validada_ref: string
  template_aprobado_ref: string
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

type ConfiguracionNotificacionDraft = {
  contrato: string
  canal: string
  dias_notificacion_text: string
  activa: boolean
  evidencia_configuracion_ref: string
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
  configuracionNotificacionDraft,
  setConfiguracionNotificacionDraft,
  handleCreateConfiguracionNotificacion,
  gatesCanales,
  identidades,
  contratos,
  arrendatarios,
  documentosEmitidos,
  mensajesSalientes,
  filteredGatesCanales,
  filteredConfiguracionesNotificacion,
  filteredNotificacionesCobranza,
  filteredMensajesSalientes,
  isSubmitting,
  isLoading,
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
  configuracionNotificacionDraft: ConfiguracionNotificacionDraft
  setConfiguracionNotificacionDraft: Dispatch<SetStateAction<ConfiguracionNotificacionDraft>>
  handleCreateConfiguracionNotificacion: (event: FormEvent<HTMLFormElement>) => Promise<void>
  gatesCanales: CanalMensajeriaItem[]
  identidades: IdentidadItem[]
  contratos: ContratoItem[]
  arrendatarios: ArrendatarioItem[]
  documentosEmitidos: DocumentoEmitidoItem[]
  mensajesSalientes: MensajeSalienteItem[]
  filteredGatesCanales: CanalMensajeriaItem[]
  filteredConfiguracionesNotificacion: ConfiguracionNotificacionItem[]
  filteredNotificacionesCobranza: NotificacionCobranzaItem[]
  filteredMensajesSalientes: MensajeSalienteItem[]
  isSubmitting: boolean
  isLoading: boolean
  contratoById: ReadonlyMap<number, ContratoItem>
  toneFor: (value: string) => Tone
}) {
  const documentoById = new Map(documentosEmitidos.map((item) => [item.id, item]))
  const gateById = new Map(gatesCanales.map((item) => [item.id, item]))
  const identidadById = new Map(identidades.map((item) => [item.id, item]))
  const arrendatarioById = new Map(arrendatarios.map((item) => [item.id, item]))
  const configuracionById = new Map(filteredConfiguracionesNotificacion.map((item) => [item.id, item]))
  const mensajeById = new Map(mensajesSalientes.map((item) => [item.id, item]))
  const refValue = (value: unknown) => (typeof value === 'string' && value.trim() ? value.trim() : '')
  const formatPayload = (value?: Record<string, unknown>) => {
    if (!value || Object.keys(value).length === 0) return '-'
    return JSON.stringify(value)
  }
  const gateRefs = (row: CanalMensajeriaItem) => {
    const refs = row.restricciones_operativas || {}
    const visibleRefs = [
      ['prueba', refValue(refs.prueba_aislada_ref) || refValue(refs.prueba_envio_ref)],
      ['oauth', refValue(refs.oauth_validado_ref)],
      ['credencial', refValue(refs.credencial_validada_ref)],
      ['template', refValue(refs.template_aprobado_ref) || refValue(refs.template_ref)],
    ].filter(([, value]) => value)
    if (visibleRefs.length) {
      return visibleRefs.map(([label, value]) => `${label}: ${value}`).join(' · ')
    }
    if (refs.templates_aprobados === true) {
      return 'template aprobado'
    }
    return 'Sin refs'
  }

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
              <input placeholder="Prueba aislada ref" value={gateCanalDraft.prueba_aislada_ref} onChange={(event) => setGateCanalDraft((current) => ({ ...current, prueba_aislada_ref: event.target.value }))} />
              <input placeholder="OAuth ref" value={gateCanalDraft.oauth_validado_ref} onChange={(event) => setGateCanalDraft((current) => ({ ...current, oauth_validado_ref: event.target.value }))} />
              <input placeholder="Credencial validada ref" value={gateCanalDraft.credencial_validada_ref} onChange={(event) => setGateCanalDraft((current) => ({ ...current, credencial_validada_ref: event.target.value }))} />
              <input placeholder="Template aprobado ref" value={gateCanalDraft.template_aprobado_ref} onChange={(event) => setGateCanalDraft((current) => ({ ...current, template_aprobado_ref: event.target.value }))} />
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

          <section className="panel">
            <div className="section-heading"><div><h2>Cadencia de notificaciones</h2><p>Días por contrato y canal habilitado.</p></div></div>
            <form className="entity-form" onSubmit={handleCreateConfiguracionNotificacion}>
              <select value={configuracionNotificacionDraft.contrato} onChange={(event) => setConfiguracionNotificacionDraft((current) => ({ ...current, contrato: event.target.value }))}>
                <option value="">Selecciona contrato</option>
                {contratos.map((item) => (
                  <option key={item.id} value={item.id}>{item.codigo_contrato}</option>
                ))}
              </select>
              <select value={configuracionNotificacionDraft.canal} onChange={(event) => setConfiguracionNotificacionDraft((current) => ({ ...current, canal: event.target.value }))}>
                <option value="email">Email</option>
                <option value="whatsapp">WhatsApp</option>
              </select>
              <input placeholder="Días 1,3,5,10,15,20,25" value={configuracionNotificacionDraft.dias_notificacion_text} onChange={(event) => setConfiguracionNotificacionDraft((current) => ({ ...current, dias_notificacion_text: event.target.value }))} />
              <input placeholder="Evidencia ref" value={configuracionNotificacionDraft.evidencia_configuracion_ref} onChange={(event) => setConfiguracionNotificacionDraft((current) => ({ ...current, evidencia_configuracion_ref: event.target.value }))} />
              <label className="inline-checkbox"><input type="checkbox" checked={configuracionNotificacionDraft.activa} onChange={(event) => setConfiguracionNotificacionDraft((current) => ({ ...current, activa: event.target.checked }))} /> Activa</label>
              <button type="submit" className="button-primary" disabled={isSubmitting || !configuracionNotificacionDraft.contrato}>Guardar cadencia</button>
            </form>
          </section>
        </section>
      ) : null}

      <TableBlock title="Gates de canal" subtitle="Estado operativo por canal." rows={filteredGatesCanales} empty="No hay gates de canal para este filtro." isLoading={isLoading} loadingLabel="Cargando canales..." columns={[
        { label: 'Canal', render: (row) => row.canal },
        { label: 'Provider', render: (row) => row.provider_key },
        { label: 'Estado', render: (row) => <Badge label={row.estado_gate} tone={toneFor(row.estado_gate)} /> },
        { label: 'Evidencia', render: (row) => row.evidencia_ref || 'Sin evidencia' },
        { label: 'Refs operativas', render: gateRefs },
      ]} />

      <TableBlock title="Cadencias de notificación" subtitle="Configuración local por contrato y canal habilitado." rows={filteredConfiguracionesNotificacion} empty="No hay cadencias configuradas." isLoading={isLoading} loadingLabel="Cargando canales..." columns={[
        { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
        { label: 'Canal', render: (row) => row.canal },
        { label: 'Días', render: (row) => row.dias_notificacion.join(', ') || 'Sin días' },
        { label: 'Estado', render: (row) => <Badge label={row.activa ? 'activa' : 'inactiva'} tone={row.activa ? 'positive' : 'neutral'} /> },
        { label: 'Evidencia', render: (row) => row.evidencia_configuracion_ref || 'Base sugerida' },
      ]} />

      <TableBlock title="Recordatorios programados" subtitle="Programación local por pago, sin envío externo." rows={filteredNotificacionesCobranza} empty="No hay recordatorios programados para este filtro." isLoading={isLoading} loadingLabel="Cargando canales..." columns={[
        { label: 'Contrato', render: (row) => contratoById.get(row.contrato)?.codigo_contrato || row.contrato },
        { label: 'Arrendatario', render: (row) => row.arrendatario ? (arrendatarioById.get(row.arrendatario)?.nombre_razon_social || row.arrendatario) : 'Sin arrendatario' },
        { label: 'Pago', render: (row) => `${row.pago_mes}/${row.pago_anio} · ${row.pago_estado}` },
        { label: 'Vencimiento', render: (row) => row.pago_fecha_vencimiento },
        { label: 'Monto', render: (row) => row.pago_monto_facturable_clp },
        { label: 'Canal', render: (row) => row.canal },
        { label: 'Cadencia', render: (row) => {
          const config = configuracionById.get(row.configuracion)
          const dias = config?.dias_notificacion || row.configuracion_dias_notificacion
          const estadoConfig = row.configuracion_activa ? 'activa' : 'inactiva'
          return `${row.dia_notificacion} de ${dias.join(', ')} · ${estadoConfig}`
        } },
        { label: 'Fecha', render: (row) => row.fecha_programada },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Mensaje', render: (row) => {
          const message = row.mensaje_saliente ? mensajeById.get(row.mensaje_saliente) : null
          return message ? `${message.estado} · ${message.destinatario || message.asunto || message.id}` : row.motivo_estado || 'Pendiente local'
        } },
      ]} />

      <TableBlock title="Mensajes salientes" subtitle="Preparados, bloqueados o enviados manualmente." rows={filteredMensajesSalientes} empty="No hay mensajes salientes para este filtro." isLoading={isLoading} loadingLabel="Cargando canales..." columns={[
        { label: 'Canal', render: (row) => row.canal },
        { label: 'Gate', render: (row) => {
          const gate = gateById.get(row.canal_mensajeria)
          return gate ? `${gate.provider_key} · ${gate.estado_gate}` : row.canal_mensajeria
        } },
        { label: 'Identidad', render: (row) => {
          const identidad = row.identidad_envio ? identidadById.get(row.identidad_envio) : null
          return identidad ? `${identidad.remitente_visible} · ${identidad.direccion_o_numero}` : 'Sin identidad'
        } },
        { label: 'Destinatario', render: (row) => row.destinatario || 'Sin destinatario' },
        { label: 'Contrato', render: (row) => row.contrato ? (contratoById.get(row.contrato)?.codigo_contrato || row.contrato) : 'Sin contrato' },
        { label: 'Arrendatario', render: (row) => row.arrendatario ? (arrendatarioById.get(row.arrendatario)?.nombre_razon_social || row.arrendatario) : 'Sin arrendatario' },
        { label: 'Documento', render: (row) => row.documento_emitido ? (documentoById.get(row.documento_emitido)?.storage_ref || row.documento_emitido) : 'Sin documento' },
        { label: 'Estado', render: (row) => <Badge label={row.estado} tone={toneFor(row.estado)} /> },
        { label: 'Enviado', render: (row) => row.enviado_at || 'Sin envio' },
        { label: 'Traza', render: (row) => row.motivo_bloqueo || row.external_ref || 'Sin observación' },
        { label: 'Payload', render: (row) => formatPayload(row.provider_payload) },
      ]} />
    </>
  )
}
