# Etapa 2 - Cobranza y canales

## Objetivo

Cerrar cobranza activa, estados de cuenta, codigos de cobro y canales
condicionados sin envios reales accidentales.

## Alcance

- Pagos mensuales.
- Ajustes y garantias.
- Codigos residuales.
- Estados de cuenta.
- Email, WebPay y notificaciones condicionadas.

## Gate

- Datos de Etapa 1 confirmados.
- Fuente de cierre `snapshot_controlado` o `real_autorizado`, con
  `SourceLabel` y `AuthorizationRef` no sensibles; auditorias `local`,
  `fixture` o `demo` solo preparan y diagnostican.
- Repactaciones existentes deben mantener coherencia saldo/estado: una
  repactacion activa conserva saldo pendiente mayor que cero y una cumplida
  debe quedar sin saldo pendiente.
- Codigos residuales existentes deben usar formato canonico `CCR-XXXXXX` con
  caracteres mayusculos no ambiguos; la readiness debe bloquear snapshots que
  conserven referencias fuera de formato.
- Estados de cuenta existentes deben estar recalculados contra pagos abiertos,
  repactaciones activas y codigos residuales activos; la readiness debe
  bloquear snapshots con arrendatarios cobrables sin estado o con resumen
  operativo desactualizado.
- Garantias contractuales recibidas parcialmente deben quedar visibles como
  incompletas hasta regularizarse o contar con aceptacion formal mediante
  referencia no sensible; APIs y backoffice exponen brecha, estado de
  incompletitud y aceptacion parcial.
- Envio externo cerrado por defecto.
- Prueba aislada de correos/WebPay con referencias no sensibles.
- Evidencia de auditoria por operacion critica; mensajes en estado `enviado`
  deben conservar evento auditable de envio manual con actor y `external_ref`
  no sensible alineado al mensaje.
- Registro manual de envio solo con `external_ref` trazable no sensible y
  revalidacion del gate abierto, identidad activa, destinatario y mandato
  operativo activo.
- `MensajeSaliente.clean()` bloquea nuevas escrituras en estado `preparado` o
  `enviado` sin gate abierto, readiness Email, identidad activa, destinatario,
  mandato operativo activo, contexto WhatsApp valido o formalizacion
  documental cuando corresponda; mensajes `enviado` requieren `external_ref`
  trazable no sensible y timestamp de envio.
- Las notificaciones por cobranza se configuran por contrato y canal
  habilitado mediante cadencias activas de dias. La base sugerida es
  `1/3/5/10/15/20/25`; una cadencia distinta requiere referencia no sensible,
  la API no permite cadencias activas sin asignacion de canal vigente en el
  mandato, el snapshot redacta evidencia heredada sensible y readiness bloquea
  contratos vigentes/futuros con canal habilitado sin cadencia activa o con
  configuraciones invalidas.
- Los pagos mensuales pendientes o atrasados con cadencia activa deben
  materializar recordatorios programados por pago/canal/dia. La generacion de
  `PagoMensual` crea la programacion local de forma idempotente, el snapshot de
  Canales la expone al backoffice y readiness bloquea pagos cobrables sin
  recordatorios programados, con programacion heredada invalida o ligada a una
  configuracion inactiva. Un recordatorio omitido requiere motivo operativo no
  sensible. Esta programacion no envia Email, WhatsApp ni proveedores externos.
- Los pagos mensuales abiertos vencidos deben refrescarse contra una fecha de
  corte operativa: un pago `pendiente` vencido pasa a `atrasado`, `dias_mora`
  se recalcula, y el estado de cuenta del arrendatario queda sincronizado. La
  readiness bloquea pagos pendientes ya vencidos o pagos atrasados con
  `dias_mora` desactualizado para la fecha de corte auditada.
- Mensajes salientes con `DocumentoEmitido` cuya politica documental exige
  firma o notaria solo pueden prepararse o marcarse enviados si el documento
  ya esta `formalizado`; el dominio conserva el mismo guard para escrituras
  directas y readiness detecta snapshots heredados.
- Email cerrado/condicionado por defecto: un gate `Email.Salida` abierto
  requiere `evidencia_ref`, referencia de prueba aislada/envio y referencia
  OAuth/credencial validada, todas no sensibles; preparar o registrar envio
  revalida esas referencias antes de permitir operacion manual controlada. El
  cierre local exige `IdentidadDeEnvio` Email activa y
  `AsignacionCanalOperacion` activa sobre mandato operativo activo; el sistema
  no inventa remitente sustituto.
- WhatsApp cerrado por defecto: requiere opt-in con evidencia, template
  aprobado registrado en el gate sin refs sensibles, ventana `08:00-21:00
  America/Santiago`, identidad activa y contacto no bloqueado con telefono en
  formato internacional. Si el gate WhatsApp queda abierto, el readiness exige
  identidad y asignacion WhatsApp activas. La evidencia de opt-in debe ser una
  referencia trazable no sensible; APIs y snapshots deben redactar evidencia
  sensible heredada y readiness debe bloquearla sin imprimir el valor. La
  readiness tambien debe bloquear opt-ins heredados con telefono local o
  ambiguo. El bloqueo definitivo del contacto debe registrar motivo,
  evidencia no sensible, fecha, evento auditable y alerta administrativa; la
  rehabilitacion manual conserva la traza del bloqueo y usa referencia no
  sensible. Todo mensaje WhatsApp bloqueado o fallido debe quedar con Email
  alternativo preparado/enviado o con alerta critica/fallback trazable; la
  readiness bloquea snapshots heredados sin esa traza o con bloqueo definitivo
  sin evento/alerta.
- WebPay cerrado/condicionado por defecto: preparar intento local requiere gate
  `WebPay.IntentoPago`, `return_url_ref` controlado no sensible y
  `evidencia_ref` no sensible; confirmar manualmente requiere `external_ref`
  trazable no sensible y `fecha_pago_webpay` diferenciada. Un intento WebPay
  confirmado debe quedar alineado con un `PagoMensual` pagado y la misma fecha
  WebPay. `provider_payload` no puede contener URLs, tokens, credenciales,
  correos ni claves sensibles. Ningun flujo llama Transbank ni marca pago
  confirmado sin revalidar el gate.
- APIs y snapshots de Canales/Cobranza redactan refs sensibles ya persistidas
  antes de devolver gates, mensajes salientes o intentos WebPay al backoffice;
  esto cubre `evidencia_ref`, `restricciones_operativas`, `external_ref`,
  `return_url_ref`, `provider_payload` y `storage_ref` documental expuesto por
  snapshot de Canales, sin abrir integraciones externas. Los mensajes
  salientes rechazan nuevas escrituras con `provider_payload` que contenga
  URLs, tokens, credenciales, correos o claves sensibles y tambien rechazan
  mensajes enviados sin `external_ref` no sensible, sin timestamp de envio,
  sin evento auditable de envio manual o con evento sin actor/`external_ref`
  trazable alineado.
- Auditoria local `audit_stage2_cobranza_readiness` consolida pagos mensuales,
  estados de cuenta, identidades/asignaciones de canal, gates
  Email/WhatsApp/WebPay, mensajes enviados/preparados e intentos WebPay,
  incluyendo deteccion de
  refs sensibles en gates, `external_ref`, `return_url_ref` o
  `provider_payload` sensible, intentos WebPay confirmados desalineados con el
  pago mensual, pagos pendientes vencidos y mora desactualizada, sin enviar
  mensajes ni conectar proveedores externos. Para cierre debe ejecutarse
  con `--source-kind
  snapshot_controlado` o `--source-kind real_autorizado`; la fuente local no
  puede marcar `ready_for_stage2_cobranza=true`.
- Wrapper reproducible:

```powershell
cd "D:/Proyectos/LeaseManager"
.\scripts\run-stage2-readiness-gate.ps1
```

  La ejecucion local crea SQLite bajo `local-evidence/`, corre migraciones y
  exige `source_kind=local`, `classification=parcial`,
  `ready_for_stage2_cobranza=false` y `stage2.source_kind_not_authorized`.
  Para cierre autorizado se debe usar el mismo wrapper con `-SourceKind
  snapshot_controlado` o `-SourceKind real_autorizado`, `-SourceLabel`,
  `-AuthorizationRef`, `-Stage1EvidenceRef`, `-EmailProofRef`,
  `-WebPayProofRef`, `-ResponsibleRef` y `-RequireReady`.

## Salida

Cobranza puede cerrarse solo si los cobros trazan a contrato, propiedad, cuenta
y periodo contractual. Sin Etapa 1 cerrada y sin prueba aislada de integracion
externa, el frente queda en preparacion segura o `parcial`, no cerrado.
