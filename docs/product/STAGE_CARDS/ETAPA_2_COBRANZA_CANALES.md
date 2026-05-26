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
- Repactaciones parciales solo pueden existir con excepcion formal, referencia
  no sensible, motivo auditable y evento auditable dedicado. El servicio de
  guardado de repactaciones crea esa auditoria en la misma transaccion que
  persiste el plan parcial y exige actor trazable; la readiness bloquea
  snapshots heredados sin esa traza o con motivo desalineado en el evento.
- Pagos originales en estado `en_repactacion` o `pagado_via_repactacion`
  deben conservar enlace a una `RepactacionDeuda` del mismo contrato y
  arrendatario. Un pago `en_repactacion` requiere plan activo; un pago
  `pagado_via_repactacion` requiere plan cumplido. La readiness bloquea
  snapshots heredados sin plan trazable o con estado de plan incompatible.
- Codigos residuales existentes deben usar formato canonico `CCR-XXXXXX` con
  caracteres mayusculos no ambiguos; la readiness debe bloquear snapshots que
  conserven referencias fuera de formato. Tambien deben ser estrictamente
  post-contrato: `fecha_activacion` debe ser posterior a
  `Contrato.fecha_fin_vigente`; dominio, API y readiness bloquean codigos
  heredados activos durante la vigencia del contrato origen. Su saldo debe ser
  coherente con el estado: `activa` conserva saldo pendiente mayor que cero, y
  `pagada` o `cancelada` deben quedar sin saldo pendiente.
- Estados de cuenta existentes deben estar recalculados contra pagos abiertos,
  repactaciones activas, codigos residuales activos y score de pago; el resumen
  operativo debe exponer porcentaje, meses evaluados, pagos en plazo y pagos
  fuera de plazo. La readiness debe bloquear snapshots con arrendatarios
  cobrables sin estado, con resumen operativo desactualizado o con score
  faltante/desalineado.
- Los valores UF deben declarar una fuente canonica de la cadena
  `UF.BancoCentral`, `UF.CMF`, `UF.MiIndicador` o
  `UF.CargaManualExtraordinaria`. La API rechaza nuevas fuentes libres, el
  bootstrap demo exige `--source-key` explicito y la readiness bloquea
  snapshots heredados con `source_key` no canonico para evitar defaults
  silenciosos.
- Valores UF manuales solo son aceptables como excepcion auditada: cada
  `ValorUFDiario` con fuente manual debe conservar `evidencia_ref`,
  `motivo_carga`, `responsable_ref` no sensibles y evento auditable
  `cobranza.valor_uf.manual_loaded` con actor. El servicio de guardado de UF
  crea esa auditoria en la misma transaccion que persiste la carga manual para
  cubrir API y llamadas internas controladas; la readiness bloquea snapshots
  con procedencia incompleta, referencias sensibles, carga manual sin evento o
  motivo desalineado entre el valor UF y su auditoria.
- Garantias contractuales recibidas parcialmente deben quedar visibles como
  incompletas hasta regularizarse o contar con aceptacion formal mediante
  referencia no sensible; APIs y backoffice exponen brecha, estado de
  incompletitud y aceptacion parcial.
- Envio externo cerrado por defecto.
- Prueba aislada de correos/WebPay con referencias no sensibles.
- Evidencia de auditoria por operacion critica; mensajes en estado `enviado`
  deben conservar evento auditable de envio manual con actor y `external_ref`
  no sensible alineado al mensaje. El servicio de registro manual crea esa
  auditoria en la misma transaccion que marca el mensaje como `enviado`, para
  cubrir tanto el endpoint HTTP como llamadas internas controladas.
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
- El efecto economico de aplicar el codigo efectivo debe quedar persistido en
  `PagoMensual.monto_efecto_codigo_efectivo_clp` como
  `monto_calculado_clp - monto_facturable_clp`. Si el efecto es distinto de
  cero, debe existir evento auditable `cobranza.pago_mensual.effective_code_applied`
  con actor, codigo y montos alineados. La readiness bloquea snapshots con
  efecto descuadrado o sin evento.
- Los pagos mensuales cerrados como `pagado_por_acuerdo_termino` o
  `condonado` solo son aceptables con referencia trazable no sensible, motivo
  auditable y evento dedicado
  `cobranza.pago_mensual.exceptional_state_resolved` con actor y resolucion
  alineada. El servicio de actualizacion operacional crea esa auditoria en la
  misma transaccion que cambia el estado, y el endpoint HTTP delega esa
  responsabilidad para cubrir tambien llamadas internas controladas. La
  readiness bloquea snapshots heredados sin esa resolucion o sin evento.
- Mensajes salientes con `DocumentoEmitido` cuya politica documental exige
  firma o notaria solo pueden prepararse o marcarse enviados si el documento
  ya esta `formalizado`; el dominio conserva el mismo guard para escrituras
  directas y readiness detecta snapshots heredados.
- Email cerrado/condicionado por defecto: un gate `Email.Salida` abierto
  requiere `evidencia_ref`, referencia de prueba aislada/envio y referencia
  OAuth/credencial validada, todas no sensibles; preparar o registrar envio
  revalida esas referencias antes de permitir operacion manual controlada. El
  JSON `restricciones_operativas` rechaza URLs, tokens, credenciales, correos
  y claves sensibles como `api_key` o `access_token`, conservando solo claves
  canonicas de referencia no sensible como `credencial_validada_ref`. El
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
  evidencia no sensible, fecha, evento auditable y alerta administrativa; el
  servicio de bloqueo crea la alerta y el evento con actor en la misma
  transaccion. La rehabilitacion manual conserva la traza del bloqueo, usa
  referencia no sensible y resuelve alertas desde servicio con auditoria
  dedicada. Todo mensaje WhatsApp bloqueado o fallido debe quedar con Email
  alternativo preparado/enviado o con alerta critica/fallback trazable; la
  readiness bloquea snapshots heredados sin esa traza, con bloqueo definitivo
  sin evento/alerta, sin actor o con evidencia/motivo desalineados.
- WebPay cerrado/condicionado por defecto: preparar intento local requiere gate
  `WebPay.IntentoPago`, `return_url_ref` controlado no sensible y
  `evidencia_ref` no sensible; confirmar manualmente requiere `external_ref`
  trazable no sensible y `fecha_pago_webpay` diferenciada. Un intento WebPay
  confirmado debe quedar alineado con un `PagoMensual` pagado y la misma fecha
  WebPay, y el servicio de confirmacion manual debe conservar auditoria
  dedicada con actor y referencia externa alineada en la misma transaccion.
  `provider_payload` no puede contener URLs, tokens, credenciales, correos ni
  claves sensibles; `restricciones_operativas` del gate WebPay aplica la misma
  regla incluyendo nombres de claves sensibles. Ningun flujo llama Transbank ni
  marca pago confirmado sin revalidar el gate.
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
  valores UF manuales, estados de cuenta, identidades/asignaciones de canal, gates
  Email/WhatsApp/WebPay, mensajes enviados/preparados e intentos WebPay,
  incluyendo deteccion de
  UF manual sin evento auditable, refs sensibles en gates, `external_ref`, `return_url_ref` o
  `provider_payload` sensible, intentos WebPay confirmados desalineados con el
  pago mensual, pagos pendientes vencidos, mora desactualizada, efecto de
  codigo efectivo descuadrado o sin evento auditable, pagos por acuerdo de
  termino o condonados sin resolucion trazable o sin evento auditable, y
  estados de cuenta con score faltante o desalineado, sin enviar mensajes ni conectar
  proveedores externos. Para cierre debe ejecutarse
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
