# Matriz de trazabilidad - mayo 2026

Esta matriz conecta producto, fuentes, implementacion, etapa, estado, gate y
proxima accion. Debe actualizarse cuando un frente avance.

La matriz es un mapa de estado, no el cursor operativo. El frente activo y la
decision de que paquete continuar en una reanudacion quedan en
`docs/product/EXECUTION_CURSOR_MAYO_2026.md`.

Nota 2026-05-27: CobranzaActiva persiste traza UF exacta en pagos mensuales.
`PagoMensual` guarda moneda de calculo, fecha UF usada, valor UF usado y
fuente canonica; la fecha debe coincidir con `fecha_vencimiento`. La generacion
de pagos usa `ValorUFDiario` de la fecha de vencimiento, Etapa 1 audita pagos
existentes dependientes de UF contra esa traza exacta y readiness Etapa 2
bloquea trazas faltantes, desalineadas o sobrantes.

Nota 2026-05-27: Patrimonio permite planificar representaciones
patrimoniales futuras contra participaciones futuras alineadas. La validacion
de `RepresentacionComunidad` ya no exige que el representante sea participante
vigente hoy cuando la representacion empieza en una ventana futura; exige que
exista una participacion activa solapada con la vigencia de la representacion,
y el auditor Etapa 1 acepta ese snapshot controlado.

Nota 2026-05-27: CobranzaActiva excluye del score de pago los meses sin
registro operativo. `calculate_payment_score` ignora pagos cuyo vencimiento
queda antes de `Contrato.fecha_registro_operativo`, `EstadoCuentaArrendatario`
expone `score_meses_sin_registro_operativo` en el resumen operativo y
readiness Etapa 2 detecta estados heredados que hayan contado esos meses como
evaluables.

Nota 2026-05-27: Compliance exige motivo no sensible al revocar
exportaciones sensibles. `ExportacionRevokeView` rechaza revocaciones sin
motivo o con URLs, correos, tokens, bearer, claves o credenciales, guarda
`revocation_reason` en el evento `compliance.exportacion_sensible.revoked` y
readiness reporta `compliance.export_revoked_audit_reason_missing` para
snapshots heredados revocados sin motivo auditable valido.

Nota 2026-05-27: PlataformaBase recupera `core.tests_migration_pipeline`
para comunidades mixtas con empresa participante. La resolucion manual de
owners valida de forma controlada que una empresa participante activa tenga
participaciones completas antes de crear comunidad/propiedad, y las fixtures
del flujo actual representan esa estructura patrimonial antes de reimportar
contratos.

Nota 2026-05-27: PlataformaBase/Core cierra superficie admin cruda.
`ScopeAdmin`, `RoleScopeAdmin`, `UserScopeAssignmentAdmin`,
`PlatformSettingAdmin` y `OperationalRuntimeSignalAdmin` reemplazan metadata,
permission sets, valores y refs runtime por vistas redactadas, eliminan
busquedas por campos sensibles y mantienen cerrada el alta manual de settings y
signals runtime desde Django admin.

Nota 2026-05-27: Auditoria cierra superficie admin cruda. `AuditEventAdmin` y
`ManualResolutionAdmin` reemplazan identificadores, resumenes, rationales,
request ids y metadata por vistas redactadas, eliminan busquedas por campos
sensibles y mantienen cerradas alta/borrado manual desde Django admin para no
saltar los flujos auditados del backoffice.

Nota 2026-05-27: Compliance cierra superficie admin de politicas de retencion.
`PoliticaRetencionDatosAdmin` ya no expone ni busca `evento_inicio` crudo,
muestra una version redactada de politicas heredadas con URLs, tokens o
credenciales y mantiene cerrada el alta manual desde admin.

Nota 2026-05-27: Compliance valida el bootstrap demo de politicas de
retencion antes de persistir. `bootstrap_demo_compliance_policies` construye
candidatos `PoliticaRetencionDatos`, ejecuta `full_clean()` sobre todo el set
canonico y solo aplica cambios dentro de una transaccion si no hay campos
invalidos o sensibles, evitando escrituras parciales desde parametros de
bootstrap.

Nota 2026-05-27: SII cierra superficie admin para refs y payloads
tributarios sensibles heredados. Los admins de capacidades SII, DTE, F29,
ProcesoRentaAnual, DDJJ y F22 reemplazan certificados, evidencias, tracking,
borradores, paquetes, resumenes y observaciones crudas por vistas redactadas,
eliminan busquedas por campos sensibles y mantienen el alta manual cerrada
desde backoffice.

Nota 2026-05-27: Canales cierra superficie admin para refs, payloads,
restricciones y motivos sensibles heredados. Los admins de gates de mensajeria,
mensajes salientes, configuraciones de notificacion y recordatorios programados
reemplazan los campos crudos por vistas redactadas, eliminan busquedas por
refs sensibles y mantienen el alta manual cerrada desde backoffice.

Nota 2026-05-27: Contabilidad cierra superficie admin para refs y payloads
sensibles heredados. Los admins de eventos contables, movimientos de asiento,
obligaciones, libros, balances, cierres y efectos de reapertura reemplazan
payloads, `storage_ref`, `centro_resultado_ref`, motivos y evidencias crudas
por vistas redactadas, eliminan busquedas por campos sensibles y cierran el
alta manual de artefactos generados.

Nota 2026-05-27: Conciliacion cierra superficie admin para referencias
bancarias sensibles heredadas. Los admins de conexiones bancarias, movimientos
importados, cuadraturas y transferencias intercuenta reemplazan refs,
responsables, criterios o motivos crudos por vistas redactadas, eliminan
busquedas por campos sensibles y mantienen el alta manual cerrada desde
backoffice.

Nota 2026-05-27: CobranzaActiva cierra superficie admin para referencias y
payloads sensibles heredados. Los admins de UF manual, pagos mensuales, gates
WebPay, intentos WebPay, garantias y repactaciones reemplazan refs, motivos y
payloads crudos por vistas redactadas, eliminan busquedas por campos sensibles
y mantienen el alta manual cerrada desde backoffice.

Nota 2026-05-27: Patrimonio bloquea la inactivacion de empresas y comunidades
que aun conservan participaciones o representaciones propias activas vigentes.
La salida operativa exige transferir o cerrar esa estructura antes de marcar el
owner como inactivo, y el auditor Etapa 1 detecta snapshots heredados que
conserven ownership vigente bajo owners cerrados.

Nota 2026-05-27: Operacion redacta `evidencia_operativa_ref` sensible heredada
en cuentas recaudadoras tanto en list/detail API como en snapshot operativo. La
validacion de escritura sigue rechazando nuevas evidencias sensibles y el
auditor Etapa 1 conserva la deteccion de snapshots heredados defectuosos.

Nota 2026-05-27: Contratos cierra la superficie admin de refs/motivos
contractuales. `ContratoAdmin`, `PeriodoContractualAdmin` y `AvisoTerminoAdmin`
ya no exponen los campos crudos de entrega de llaves, prorrata, politica base
de renovacion ni resolucion guiada de conflicto; muestran versiones redactadas
y mantienen el alta manual cerrada.

Nota 2026-05-26: El flujo GitHub no debe reutilizar PRs cerrados por nombre de
rama. `scripts/codex-github-package.ps1` solo considera PR existente si su
estado es `OPEN`; si `gh pr view <branch>` devuelve un PR `MERGED` o `CLOSED`,
el paquete crea un PR nuevo para que el merge afecte realmente a `main`.

Nota 2026-05-26: Canales endurece el fallback critico de WhatsApp desde
servicio. Cuando `prepare_message()` bloquea un mensaje WhatsApp, crea
`ManualResolution` `canales.whatsapp.fallback_requerido` con actor trazable y
evento `canales.whatsapp.fallback_required` alineado al motivo/contexto del
mensaje; readiness Etapa 2 ya no acepta alertas heredadas sin actor, sin evento
dedicado o con motivo desalineado como fallback suficiente.

Nota 2026-05-26: Contratos y Canales mueven la traza de bloqueo y
rehabilitacion WhatsApp a servicios. `block_whatsapp_contact()` exige actor
trazable, bloquea el contacto, crea `ManualResolution`
`canales.whatsapp.bloqueo_definitivo` y evento
`contratos.arrendatario.whatsapp_blocked` con motivo/evidencia alineados en la
misma transaccion; `rehabilitate_whatsapp_contact()` resuelve alertas y audita
la rehabilitacion. Readiness Etapa 2 exige actor y alineacion de evento/alerta.

Nota 2026-05-26: Cobranza mueve la auditoria de cargas UF manuales a la capa
de servicio. `save_uf_value()` exige actor trazable para fuentes manuales,
guarda el `ValorUFDiario` y crea el `AuditEvent`
`cobranza.valor_uf.manual_loaded` con evidencia, motivo y responsable
alineados en la misma transaccion; API y bootstrap delegan esa responsabilidad
y readiness exige que el motivo del evento coincida con el valor UF.

Nota 2026-05-26: Cobranza mueve la auditoria de repactaciones parciales a la
capa de servicio. `save_repayment_plan()` exige actor trazable cuando el plan
cubre menos que la deuda original, guarda la repactacion y crea el `AuditEvent`
`cobranza.repactacion_deuda.partial_exception` con referencia y motivo
alineados en la misma transaccion; los endpoints HTTP delegan esa
responsabilidad y readiness exige que el motivo del evento coincida con la
repactacion.

Nota 2026-05-26: Cobranza mueve la auditoria de cierre excepcional de pagos a
la capa de servicio. `update_payment_operational_fields()` exige actor trazable
para estados `condonado` o `pagado_por_acuerdo_termino`, sincroniza mora y
distribucion, guarda el pago y crea el `AuditEvent`
`cobranza.pago_mensual.exceptional_state_resolved` con resolucion alineada en
la misma transaccion; el endpoint HTTP delega esa responsabilidad para no
duplicar eventos.

Nota 2026-05-26: Canales mueve la auditoria de envio manual a la capa de
servicio. `mark_message_as_sent()` exige actor trazable, marca el mensaje como
`enviado` y crea el `AuditEvent`
`canales.mensaje_saliente.sent_manually` con `external_ref` alineado en la
misma transaccion; el endpoint HTTP delega esa responsabilidad para no duplicar
eventos.

Nota 2026-05-26: WebPay mueve la auditoria de confirmacion manual a la capa de
servicio. `confirm_webpay_intent_manually()` exige actor trazable, revalida el
gate, marca el intento y el pago en una transaccion y crea el `AuditEvent`
`cobranza.webpay_intento.confirmed_manually` con `external_ref`,
`pago_mensual_id` y `fecha_pago_webpay` alineados; el endpoint HTTP delega esa
responsabilidad para no duplicar eventos.

Nota 2026-05-26: Contratos reserva `renovacion_automatica` para el flujo
guiado con auditoria. `PeriodoContractual.full_clean()` exige el `AuditEvent`
dedicado para tramos con ese origen, el servicio de renovacion conserva la
excepcion interna para crear tramo y evento en la misma operacion, y la API de
contratos rechaza payloads anidados que intenten marcar un tramo como
automatico sin pasar por el endpoint.

Nota 2026-05-26: Contratos mueve la auditoria de prorrata por terminacion
anticipada parcial a guard de dominio. `Contrato.full_clean()` exige que un
contrato terminado anticipadamente con ultimo mes parcial y decision de
prorrata conserve el `AuditEvent` dedicado; la API mantiene el flujo guiado que
crea esa traza despues de guardar y el auditor Etapa 1 conserva la deteccion de
snapshots heredados.

Nota 2026-05-26: SII endurece payloads tributarios locales sin conectar SII ni
leer certificados. `ultimo_resultado`, `resumen_formulario`, `resumen_anual`,
`resumen_paquete` y `resumen_f22` rechazan valores y claves sensibles como
`api_key`, `access_token` o `credential`; readiness Etapa 4 detecta payloads
heredados sensibles sin imprimirlos y mantiene el cierre condicionado a fuente
autorizada.

Nota 2026-05-26: Renta Anual y Reporting clasifican explicitamente payloads
anuales sensibles heredados. Los readiness de Etapa 6 y Etapa 7 reportan
`resumen_anual`, `resumen_paquete` y `resumen_f22` con URLs, tokens,
credenciales, correos o claves sensibles como brecha bloqueante sin imprimir
valores, manteniendo el cierre condicionado a fuente autorizada.

Nota 2026-05-26: Compliance datos sensibles exige trazabilidad de revocacion.
Las exportaciones sensibles en estado `revocada` deben conservar evento
`compliance.exportacion_sensible.revoked`; readiness bloquea snapshots heredados
sin esa auditoria y el endpoint de revocacion mantiene el evento dedicado.

Nota 2026-05-26: Compliance datos sensibles exige actor trazable en auditoria
de exportaciones sensibles. Readiness reporta eventos `prepared`, `accessed`,
`access_denied` o `revoked` sin `actor_user` como brecha bloqueante mediante
conteos/codigos, sin exponer payloads ni metadata sensible.

Nota 2026-05-26: Compliance datos sensibles exige target auditable valido. Los
eventos `prepared`, `accessed`, `access_denied` o `revoked` deben apuntar a
`entity_type=exportacion_sensible` y `entity_id` de una exportacion existente;
readiness reporta eventos huerfanos o mal vinculados sin exponer ids.

Nota 2026-05-26: Compliance datos sensibles alinea la auditoria de
exportaciones sensibles con la exportacion real. Los eventos `prepared`,
`accessed`, `access_denied` y `revoked` conservan metadata no sensible de
categoria, tipo de exportacion, scope, hash, estado, hold, expiracion y creador;
readiness reporta `compliance.export_prepared_audit_event_unaligned`,
`compliance.export_revoked_audit_event_unaligned` y
`compliance.audit_metadata_unaligned` para eventos heredados incompletos o
desalineados.

Nota 2026-05-26: Compliance datos sensibles clasifica referencias sensibles en
fuente y evidencia final. `audit_compliance_data_readiness` distingue refs
faltantes de refs con URLs, tokens, correos o credenciales para
`SourceLabel`, `AuthorizationRef`, politica aprobada, responsables, controles,
evidencia archivada y validacion legal-operativa, sin imprimir valores.

Nota 2026-05-26: El login publico deja de renderizar mensajes internos de
error. La superficie anonima usa `publicSafeApiErrorMessage()` para permitir
solo detalles HTTP acotados y no sensibles, y reemplaza nombres de variables o
configuracion por estados publicos genericos.

Nota 2026-05-26: Documentos ajusta la firma de codeudor al alcance real del
contrato. `DocumentoEmitido.validate_formalization()` exige
`firma_codeudor_registrada` cuando la politica lo pide y el expediente apunta a
un contrato con `CodeudorSolidario` activo; contratos sin codeudor activo no se
bloquean solo por el flag de politica. Readiness reporta
`documents.codebtor_signature_missing` para formalizados heredados que incumplan
esa condicion.

Nota 2026-05-26: Patrimonio mueve la identidad unica de propiedades activas a
guard de escritura. `Propiedad.full_clean()` y la API rechazan nuevas
propiedades activas con ROL de avaluo normalizado duplicado o identidad
operativa duplicada; `audit_stage1_matrix` mantiene la deteccion de snapshots
heredados.

Nota 2026-05-26: Contratos mueve la regla de gastos comunes estructurados a
guard de escritura. Contratos vigentes/futuros con `tiene_gastos_comunes=True`
requieren un `ServicioPropiedad` activo de tipo gasto comun en la propiedad
principal desde `Contrato.full_clean()` y API; el auditor Etapa 1 conserva la
deteccion de snapshots heredados.

Nota 2026-05-26: Contratos mueve la cobertura minima de canal operativo a
guard de escritura. Contratos vigentes/futuros requieren al menos una
`AsignacionCanalOperacion` activa con `IdentidadDeEnvio` activa en su mandato
desde `Contrato.full_clean()` y API; el auditor Etapa 1 conserva la deteccion
de snapshots heredados.

Nota 2026-05-26: Contratos mueve el readiness operativo de arrendatario a
guard de escritura. Contratos vigentes/futuros requieren arrendatario con
estado de contacto activo, email o telefono, domicilio de notificaciones y
contacto de pago activo estructurado desde `Contrato.full_clean()` y API; el
auditor Etapa 1 conserva la deteccion de snapshots heredados.

Nota 2026-05-26: Contratos mueve el respaldo de cierre para contratos futuros
a guard de dominio. `Contrato.full_clean()` valida que un contrato futuro
tenga AvisoTermino registrado sobre el contrato vigente de la propiedad
principal, terminacion anticipada ejecutada o resolucion guiada no sensible si
existe conflicto con renovacion ya ejecutada; API y auditor Etapa 1 conservan
la misma regla para escrituras y snapshots heredados.

Nota 2026-05-26: Contratos mueve el cambio de arrendatario futuro a guard de
escritura. `Contrato.full_clean()` y API rechazan contratos futuros con
arrendatario distinto al vigente si no provienen del flujo guiado de cambio de
arrendatario o no conservan el `AuditEvent` exacto que vincula contrato
anterior, aviso y contrato nuevo; el servicio guiado conserva la excepcion
interna necesaria para crear el contrato y su auditoria en la misma
transaccion, y el auditor Etapa 1 mantiene la deteccion de snapshots heredados.

Nota 2026-05-26: Contratos mueve la entrega de llaves a guard de dominio.
`Contrato.full_clean()` y API rechazan crear o actualizar contratos con
`fecha_entrega` operativa si no existe garantia cubierta o autorizacion
auditada con referencia no sensible y motivo trazable; el auditor Etapa 1
mantiene la deteccion de snapshots heredados sin garantia suficiente ni
autorizacion.

Nota 2026-05-26: CobranzaActiva y Canales endurecen los gates externos sin
abrir integraciones. `restricciones_operativas` de Email/WhatsApp/WebPay
rechaza valores sensibles y tambien nombres de claves sensibles como
`api_key`, `access_token` o `credential`; las claves canonicas de referencia
no sensible, como `credencial_validada_ref`, siguen permitidas cuando su valor
es trazable y no sensible. Readiness Etapa 2 bloquea snapshots heredados con
estas claves sensibles sin imprimir sus valores.

Nota 2026-05-26: CobranzaActiva refuerza que `CodigoCobroResidual` es
post-contrato. `fecha_activacion` debe ser posterior a
`Contrato.fecha_fin_vigente`; dominio/API rechazan nuevas escrituras durante la
vigencia y readiness Etapa 2 reporta `stage2.residual_code.invalid_model` para
snapshots heredados con codigos residuales prematuros.

Nota 2026-05-26: CobranzaActiva exige coherencia saldo/estado en
`CodigoCobroResidual`. Un codigo `activa` mantiene saldo pendiente mayor que
cero; `pagada` o `cancelada` deben quedar con `saldo_actual=0`, y readiness
Etapa 2 bloquea snapshots heredados que oculten saldo bajo estados cerrados.

Nota 2026-05-26: Conciliacion restringe el match exacto automatico de cobranza
residual a la cuenta recaudadora del movimiento bancario. Una referencia
`CCR-XXXXXX` valida pero asociada a otra cuenta queda como ingreso desconocido
para resolucion manual auditada; readiness Etapa 3 sigue bloqueando snapshots
heredados con targets residuales de cuenta incorrecta.

Nota 2026-05-26: CobranzaActiva canoniza la procedencia de `ValorUFDiario`.
`source_key` solo acepta `UF.BancoCentral`, `UF.CMF`, `UF.MiIndicador` o
`UF.CargaManualExtraordinaria`; el bootstrap demo exige `--source-key`
explicito, el backoffice usa selector cerrado y readiness Etapa 2 reporta
`stage2.uf_value.source_not_canonical` para fuentes heredadas libres.

Nota 2026-05-26: CobranzaActiva persiste el efecto economico del codigo
efectivo en `PagoMensual.monto_efecto_codigo_efectivo_clp`, lo valida como
`monto_calculado_clp - monto_facturable_clp`, registra auditoria
`cobranza.pago_mensual.effective_code_applied` cuando el efecto no es cero y
readiness Etapa 2 reporta `stage2.payment.effective_code_effect_mismatch` o
`stage2.payment.effective_code_event_missing`.

Nota 2026-05-26: CobranzaActiva exige resolucion trazable para pagos mensuales
cerrados como `pagado_por_acuerdo_termino` o `condonado`. El dominio/API
requieren referencia no sensible y motivo, registran auditoria
`cobranza.pago_mensual.exceptional_state_resolved`, el snapshot/backoffice
exponen la resolucion redactada y readiness Etapa 2 reporta
`stage2.payment.exceptional_resolution_missing` o
`stage2.payment.exceptional_resolution_event_missing` para datos heredados.

Nota 2026-05-26: Patrimonio exige evidencia formal no sensible cuando una
comunidad usa representacion `designado`. `RepresentacionComunidad` conserva
`evidencia_ref`, API/snapshot/backoffice la exponen con redaccion de valores
sensibles y el auditor Etapa 1 reporta
`stage1.representacion.designada_evidencia_faltante` o
`stage1.representacion.designada_evidencia_sensible` para snapshots heredados.

Nota 2026-05-26: Contabilidad evita doble contabilizacion efectiva del mismo
hecho economico. Si ya existe un `EventoContable` `contabilizado` para la misma
empresa, tipo y entidad origen, un evento nuevo con otra `idempotency_key` queda
en `pendiente_revision_contable`; `EventoContable.full_clean` rechaza
duplicados posteados y readiness Etapa 5 reporta `stage5.duplicate_posted_events`
para snapshots heredados.

Nota 2026-05-25: Documentos incorpora emision local de PDF generado por sistema
mediante endpoint dedicado. El PDF canonico se renderiza sin dependencia
externa, el checksum SHA-256 y `storage_ref` derivan del contenido, se rechaza
contenido sensible, el endpoint generico rechaza `origen=generado_sistema` y
readiness bloquea documentos `generado_sistema` sin auditoria
`documentos.documento_emitido.generated_pdf`.

Nota 2026-05-26: Documentos incorpora vista previa auditada para PDF generado.
`documentos-emitidos/previsualizar-pdf/` deriva checksum/storage sin persistir
documento y registra `documentos.documento_emitido.previewed_pdf`; la emision
generada exige una preview auditada del mismo contenido y readiness reporta
`documents.generated_pdf_preview_missing` para snapshots heredados.

Nota 2026-05-26: Documentos alinea la auditoria de PDF generado y preview con
el contenido emitido. Los eventos `documentos.documento_emitido.generated_pdf`
y `documentos.documento_emitido.previewed_pdf` conservan actor y metadata de
checksum, `storage_ref`, version, tipo documental y expediente; readiness
reporta `documents.generated_pdf_audit_unaligned` y
`documents.generated_pdf_preview_unaligned` para eventos heredados incompletos
o desalineados.

Nota 2026-05-26: Documentos exige `evidencia_formalizacion_ref` no sensible al
formalizar documentos. API/modelo rechazan formalizaciones sin referencia o con
referencia sensible, list/detail/snapshot/backoffice redactan evidencia
heredada sensible y `audit_document_readiness` reporta
`documents.formalization_evidence_missing` o
`documents.formalization_evidence_sensitive` para snapshots heredados.

Nota 2026-05-26: Documentos alinea la auditoria de formalizacion con el acto
formalizado. El endpoint `formalizar/` registra actor y metadata no sensible de
evidencia, firmas, recepcion y comprobante notarial; readiness reporta
`documents.formalization_audit_unaligned` cuando un snapshot conserva evento
sin actor o metadata desalineada.

Nota 2026-05-26: Documentos alinea tambien la auditoria de versiones
correctivas. El evento `documentos.documento_emitido.corrective_version_created`
conserva actor y metadata de origen, expediente, tipo, version, checksum,
`storage_ref` y `correccion_ref`; readiness reporta
`documents.corrective_version_audit_unaligned` para snapshots heredados con
evento incompleto o desalineado.

Nota 2026-05-26: Documentos separa en readiness las brechas notariales
heredadas. `audit_document_readiness` reporta documentos formalizados con
politica notarial sin recepcion, sin comprobante, con comprobante de tipo
incorrecto, de otro expediente o en estado no permitido, sin exponer valores
sensibles ni leer storage real.

Nota 2026-05-25: Patrimonio incorpora flujo operacional de transferencia o
redistribucion de participaciones. El endpoint cierra la participacion origen,
crea destinos desde la fecha efectiva, conserva el 100% del owner, exige motivo
y evidencia no sensible, y registra auditoria
`patrimonio.participacion.transfer_executed`. El auditor Etapa 1 bloquea
sucesiones heredadas con sucesor inmediato sin evento auditable.

Nota 2026-05-26: El auditor Etapa 1 ya no acepta cualquier evento de
transferencia patrimonial como evidencia suficiente. Para sucesiones inmediatas
exige actor y metadata alineada a owner, participacion origen, participante
origen, fecha efectiva, destinos, porcentaje transferido, motivo y evidencia no
sensible; reporta `stage1.participacion.transferencia_auditoria_desalineada`
cuando un snapshot conserva auditoria incompleta, reciclada o sensible.

Nota 2026-05-26: Patrimonio cierra la ruta de reescritura directa de
participaciones en empresas/comunidades existentes. Los serializers rechazan
`participaciones` en updates genericos para no borrar/recrear historia con
`bulk_create`; la creacion inicial sigue permitida y los cambios posteriores
deben pasar por `participaciones/transferir/`, que conserva auditoria.

Nota 2026-05-25: Conciliacion bloquea snapshots heredados donde un abono
parcial o complementario queda `conciliado_exacto` contra un `PagoMensual` sin
resolucion manual auditada. Los pagos parciales o en varios abonos siguen
permitidos solo por resolucion manual trazable de ingreso desconocido.

Nota 2026-05-25: Conciliacion acota el match exacto automatico de pagos al
periodo economico del movimiento bancario. Un abono de otro mes ya no cierra
automaticamente un `PagoMensual` aunque coincidan cuenta y monto; queda como
ingreso desconocido/manual. Readiness Etapa 3 bloquea snapshots heredados con
movimientos conciliados exactos apuntando a pagos de otro periodo.

Nota 2026-05-25: CobranzaActiva calcula y persiste `score_pago` al recalcular
`EstadoCuentaArrendatario`, expone porcentaje, meses evaluados, pagos en plazo
y pagos fuera de plazo en `resumen_operativo`, y readiness Etapa 2 reporta
`stage2.account_state.missing_score` o `stage2.account_state.stale_score` para
snapshots heredados sin score trazable o desalineado con pagos operativos.

Nota 2026-05-24: CobranzaActiva/Canales incorpora guard local para que
WhatsApp solo opere con telefonos en formato internacional. El modelo rechaza
opt-in nuevo con numero local o ambiguo, Canales bloquea preparacion/envio con
datos heredados invalidos y readiness Etapa 2 reporta `stage2.whatsapp.phone_invalid`.

Nota 2026-05-24: Canales registra traza explicita de fallback cuando WhatsApp
queda bloqueado, y readiness Etapa 2 reporta
`stage2.whatsapp.fallback_trace_missing` para mensajes heredados bloqueados o
fallidos sin Email alternativo ni alerta critica trazable.

Nota 2026-05-24: Contratos agrega bloqueo definitivo y rehabilitacion manual
de WhatsApp con motivo, evidencia no sensible, fecha, evento auditable y alerta
administrativa. Readiness Etapa 2 reporta bloqueos heredados sin traza, evento
o alerta, y referencias sensibles de bloqueo/rehabilitacion.

Nota 2026-05-24: Canales incorpora cadencias de notificacion por contrato y
canal habilitado. La API normaliza dias, exige canal activo del mandato,
redacta evidencia sensible heredada y readiness Etapa 2 reporta contratos
vigentes/futuros con canal habilitado sin cadencia activa o configuraciones
invalidas.

Nota 2026-05-24: Contratos incorpora `ContactoPagoArrendatario` como dato
estructurado para cobranza. La API valida contactos activos con nombre y
email/telefono, redacta evidencia sensible heredada, el snapshot expone la
lista estructurada y, desde el guard de escritura 2026-05-26, contratos
vigentes/futuros quedan bloqueados por API/modelo si el arrendatario no tiene
contacto de pago activo.

Nota 2026-05-24: Patrimonio incorpora `ServicioPropiedad` para servicios y
gastos comunes estructurados. La API valida proveedor/administracion, numero de
cliente y evidencia no sensible, el snapshot redacta evidencia heredada y el
auditor Etapa 1 bloquea contratos con gastos comunes sin gasto comun activo en
la propiedad principal.

Nota 2026-05-24: Contratos referencia `PoliticaFirmaYNotaria` para politica
documental contractual. Contratos vigentes/futuros exigen politica activa de
tipo `contrato_principal`, el snapshot la expone y el auditor Etapa 1 bloquea
politicas faltantes, inactivas o de tipo documental incorrecto.

Nota 2026-05-24: Politica documental de contrato principal puede exigir perfil
documental del arrendatario persona natural. `Arrendatario` conserva
nacionalidad, estado civil y profesion, la API bloquea contratos vigentes o
futuros cuando la politica lo exige y faltan esos datos, y `audit_stage1_matrix`
detecta snapshots heredados incompletos.

Nota 2026-05-24: Compliance mueve reglas de retencion desde solo readiness a
dominio/API. `PoliticaRetencionDatos` rechaza eventos de inicio sensibles,
plazos minimos cero, falta de hold para tributario/documental y purga fisica
para documental/secreto; `audit_compliance_data_readiness` conserva la deteccion
de politicas heredadas invalidas sin exponer valores sensibles.

Nota 2026-05-24: Compliance bloquea nuevas exportaciones operativas sobre
categoria `secreto` desde dominio y servicio de preparacion. Readiness mantiene
la deteccion de exportaciones heredadas de secreto como brecha bloqueante sin
exponer payloads ni referencias.

Nota 2026-05-24: Compliance trata `expirada` como estado terminal de
exportacion sensible y exige coherencia con vencimiento cumplido y sin hold
activo. Readiness reporta exportaciones heredadas con estado expirado
inconsistente sin exponer payloads.

Nota 2026-05-24: Compliance registra evento auditable
`compliance.exportacion_sensible.access_denied` cuando se intenta descargar una
exportacion sensible revocada o expirada. Readiness cuenta esos eventos sin
exponer payloads ni metadata sensible.

Nota 2026-05-25: Compliance verifica la integridad de exportaciones sensibles
tambien al descargar. Si el payload cifrado ya no coincide con `payload_hash`,
la descarga se niega, queda auditoria de acceso denegado y readiness reporta
`compliance.export_payload_hash_mismatch` para snapshots heredados.

Nota 2026-05-25: Compliance trata payloads cifrados no descifrables como
acceso denegado controlado. La API no expone error interno, registra auditoria
y readiness reporta `compliance.export_payload_unreadable` para datos heredados
corruptos o no verificables.

Nota 2026-05-25: Contratos registra avisos de termino fuera de plazo sin
inventar fechas, compara el timestamp real de registro contra las `23:59:59`
del ultimo dia permitido y expone/audita la situacion como advertencia
`stage1.aviso_termino.registro_fuera_plazo`, sin convertirla en bloqueo por si
sola.

Nota 2026-05-25: Contratos/garantias permite representar garantias recibidas
por sobre lo pactado solo si el exceso queda clasificado, devuelto,
regularizado o bloqueado con referencia no sensible y motivo auditable. API,
snapshot, backoffice y auditor Etapa 1 reportan `stage1.garantia.exceso_sin_resolucion`
para snapshots heredados sin esa traza.

Nota 2026-05-25: Contratos registra autorizacion auditada para entrega de
llaves cuando la garantia exigida aun no esta cubierta. La API protege
actualizaciones de `fecha_entrega`, redacta referencias sensibles, el
backoffice expone la traza y el auditor Etapa 1 reporta entregas heredadas sin
garantia suficiente ni autorizacion no sensible.

Nota 2026-05-25: Contratos/garantias exige que devoluciones, retenciones o
aplicaciones de garantia apunten al deposito origen, no usen movimientos
derivados como origen y no superen el monto del deposito trazado. La API valida
la regla antes de persistir y el auditor Etapa 1 clasifica snapshots heredados
sin esa traza como defectuosos.

Nota 2026-05-25: Contratos exige que una renovacion de contrato con tramos use
como base el ultimo tramo vigente. Si cambia monto o moneda, el periodo debe
tener referencia no sensible y motivo trazable de politica documentada; API y
auditor Etapa 1 bloquean renovaciones heredadas sin esa traza.

Nota 2026-05-25: Contratos incorpora renovacion automatica operacional. El
endpoint crea el tramo `renovacion_automatica`, extiende `fecha_fin_vigente`,
bloquea `AvisoTermino` registrado, conserva la regla de politica cuando cambia
base y registra auditoria dedicada; el auditor Etapa 1 bloquea renovaciones
automaticas heredadas sin ese evento.

Nota 2026-05-25: Contratos incorpora flujo operacional de cambio de
arrendatario. El endpoint crea `AvisoTermino` registrado y contrato futuro con
nuevo arrendatario en una transaccion, conserva contrato/deuda historica sin
reescritura, copia propiedades contractuales, crea periodo inicial de origen
`cambio_arrendatario` y registra evento auditable; `Contrato.full_clean()` y
API bloquean escrituras directas de futuros con arrendatario distinto que no
usen ese flujo o no conserven esa traza, y el auditor Etapa 1 bloquea futuros
heredados con arrendatario distinto si falta esa traza.

| Frente | Fuentes rectoras | Areas de codigo/docs | Etapa | Estado actual | Gate/evidencia requerida | Proxima accion |
| --- | --- | --- | --- | --- | --- | --- |
| Gobierno documental | Fuente de verdad, AGENTS, README, cursor operativo | `docs/governance`, `AGENTS.md`, `ORDEN_DE_LECTURA.md`, `docs/product/EXECUTION_CURSOR_MAYO_2026.md` | 0 | resuelto_confirmado | PR con CI verde y docs consistentes | Mantener actualizado al cambiar fuentes; bloqueos y evidencia son controles operativos de cierre, no arquitectura de producto; el cursor gobierna reanudaciones, worktrees tacticos y metatareas cerradas. |
| PRD vigente | `01_Set_Vigente/PRD_CANONICO.md` | `01_Set_Vigente`, `docs/product` | 0 | resuelto_confirmado | PRD Mayo 2026 aceptado y promovido | Usarlo como contrato rector unico. |
| PlataformaBase | PRD, ADR stack | `backend/core`, `users`, `audit`, `health`, `frontend`, `scripts/run-acceptance-workflows.ps1`, `scripts/codex-github-package.ps1` | 0 | resuelto_confirmado | CI main verde, acceptance local, build frontend, guard Etapa 1 no evidencial, readiness local Etapa 1 anti-bucle, snapshot evidencial vacio de Etapa 1 cubierto en acceptance como `bloqueado_dato_real`, `real_autorizado` protegido contra migraciones desde el gate Etapa 1, redaccion de metadata sensible en APIs de auditoria, guards transversales de outputs versionables con limite real de directorio en wrappers PowerShell y cierre GitHub por CLI/API con fallback seguro a Git Credential Manager cuando `gh auth status` no esta logueado | Mantener como baseline y no rehacer. |
| Compliance datos sensibles | PRD, ADR secretos y auditoria, matriz gates | `backend/compliance`, `backend/core/compliance_data_readiness.py`, `scripts/run-compliance-data-readiness-gate.ps1`, backoffice compliance | 0 | parcial | Exports cifrados con motivo, scope, usuario, expiracion, auditoria, metadata visible no sensible, `encrypted_ref` no sensible y readiness `Compliance.DatosPersonalesChile2026` | Exportes sensibles cifran payload, exigen `payload_hash` SHA-256 hexadecimal de 64 caracteres, verifican que el payload descifrado coincida con ese hash antes de descargar, niegan como acceso controlado los payloads no descifrables, rechazan nuevas URLs, correos, tokens, bearer, api keys o credenciales en `motivo`/`scope_resumen`/`encrypted_ref`, bloquean categoria `secreto`, exigen categoria canonica por tipo de exportacion y politica de retencion activa tambien desde `prepare_sensitive_export`, bloquean nuevas exportaciones preparadas sin hold que excedan 30 dias de vigencia, tratan `expirada` como estado terminal no descargable, auditan intentos denegados de descarga revocada/expirada, payload desalineado o payload no descifrable y redactan metadata visible sensible heredada y `encrypted_ref` sensible heredado antes de exponer list/detail al backoffice; al revocar exige motivo no sensible y lo persiste como `revocation_reason` en auditoria; el admin Django de exportaciones sensibles no expone `scope_resumen`, `motivo`, `encrypted_payload` ni `encrypted_ref` crudos, quita `encrypted_ref` de busqueda y muestra solo versiones redactadas; `audit_compliance_data_readiness` consolida politicas de retencion por categoria, hold tributario/documental, purga restringida, integridad/auditoria de exportes, metadata sensible heredada, `encrypted_ref` sensible heredado, categoria secreto heredada, hashes no canonicos, payloads cifrados desalineados con hash, payloads no descifrables, expiraciones preparadas mayores a 30 dias heredadas, estados expirados inconsistentes, conteo de accesos denegados, eventos de auditoria sin actor, sin target de exportacion existente, con metadata desalineada frente a categoria, tipo, scope, hash, estado, hold, expiracion y creador, o revocados sin motivo no sensible; refs finales, deadline 2026-12-01 y fuente autorizada sin leer secretos ni datos reales. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel`, `AuthorizationRef`, politica aprobada, responsables, controles, evidencia archivada y validacion legal-operativa no sensibles. |
| Patrimonio | PRD, modelo canonico | `backend/patrimonio`, backoffice patrimonio | 1 | implementado_sin_evidencia | Datos reales/snapshot y validacion de entidades | API y auditor Etapa 1 validan socios, empresas, comunidades, participaciones actualmente vigentes, participantes patrimoniales activos, transferencia/reemplazo/redistribucion auditada de participaciones conservando 100%, duplicidad de participantes en el set vigente, representaciones actualmente vigentes, ventanas efectivas de representacion sin solapes, evidencia no sensible en representaciones designadas, propiedades, servicios/gastos comunes estructurados y duplicidad de identidad por rol de avaluo o identidad operativa fuerte; `Propiedad.full_clean()` y API bloquean nuevas propiedades activas duplicadas por ROL de avaluo normalizado o identidad operativa, mientras el auditor mantiene deteccion de snapshots heredados; `RepresentacionComunidad` exige `evidencia_ref` formal trazable cuando el modo es `designado`, valida representantes patrimoniales contra participaciones activas solapadas con la ventana de la representacion, snapshots/backoffice redactan evidencia sensible heredada y el admin Django no expone ni busca `evidencia_ref` cruda, mostrando solo version redactada; `ServicioPropiedad` exige proveedor/administracion, numero de cliente, evidencia no sensible y gasto comun activo estructurado cuando un contrato vigente/futuro declara gastos comunes; la activacion de empresas/comunidades no acepta participaciones futuras como vigentes, participantes inactivos/no listos ni participantes vigentes repetidos, comunidades activas tampoco aceptan representaciones futuras como vigentes, la planificacion futura no solapada queda permitida y los solapes heredados quedan defectuosos, incluyendo representaciones patrimoniales futuras con participacion futura alineada, y las desactivaciones no pueden dejar propiedades, representaciones actualmente vigentes o participaciones activas colgando de entidades no operativas. Ejecutar `scripts/run-stage1-snapshot-gate.ps1` contra snapshot/DB autorizada. |
| Operacion | PRD, ADR identidad envio | `backend/operacion`, backoffice operacion | 1 | implementado_sin_evidencia | Cuentas, mandatos e identidades validadas | Cuentas/recaudador soportan empresa, comunidad o socio; cuentas recaudadoras activas exigen uso operativo declarado, modo `manual_controlado` o `gate_bancario`, y evidencia operativa trazable no sensible; entidad facturadora exige `ConfiguracionFiscalEmpresa` activa con regimen tributario activo; mandatos activos que comunican o facturan documentos exigen autoridad operativa con nombre, RUT valido normalizado y evidencia trazable no sensible; identidades de envio activas exigen `credencial_ref` trazable no sensible y la API redacta referencias sensibles heredadas; el admin Django de Operacion no expone ni busca `evidencia_operativa_ref`, `credencial_ref` ni `autoridad_operativa_evidencia_ref` crudos y muestra solo versiones redactadas; cuentas recaudadoras no pueden pausarse/inactivarse si sostienen mandatos activos, mandatos no pueden inactivarse si sostienen contratos vigentes/futuros ni recortar su vigencia fuera del rango contractual dependiente, la planificacion futura no solapada de mandatos queda permitida y los solapes heredados quedan defectuosos, identidades no pueden suspenderse/inactivarse si sostienen asignaciones activas y la ultima asignacion activa de un mandato con contratos vigentes/futuros no puede inactivarse; auditor Etapa 1 exige identidad/asignacion de canal activa por mandato de contrato vigente/futuro y detecta cuentas activas sin evidencia operativa, credenciales sensibles existentes, autoridad operativa faltante/invalida/sensible, identidad ajena a administrador/facturadora y uso de identidad distinta del propietario sin autorizacion de comunicacion; usar `scripts/run-stage1-snapshot-gate.ps1` contra snapshot/DB autorizada. |
| Contratos | PRD, reglas contractuales | `backend/contratos`, backoffice contratos | 1 | implementado_sin_evidencia | Matriz contrato-propiedad-periodo-garantia | Usar `scripts/run-stage1-snapshot-gate.ps1`; la fuente debe tener al menos un contrato vigente o futuro, no solo contratos historicos; arrendatarios, contactos de pago estructurados, codeudores solidarios con snapshot nombre/RUT valido desde API anidada y auditor, maximo 3 activos y sin duplicados, contacto/domicilio operativo, perfil documental de persona natural cuando la politica contractual exige nacionalidad/estado civil/profesion, `Contrato.full_clean()` y API exigen canal operativo activo por mandato para contratos vigentes/futuros, vigencia del mandato cubriendo contrato, override opcional de `IdentidadDeEnvio` validado contra identidad activa y owner autorizado por mandato, politica documental activa de tipo `contrato_principal`, y representante legal de arrendatario empresa exigido por API/modelo con nombre y RUT valido normalizado y auditado en datos heredados; contratos, vinculos contrato-propiedad, periodos, garantias y avisos de termino existentes se validan globalmente, incluyendo filas historicas; la clasificacion agregada de `contratos_activos_o_futuros` queda acotada a contratos/avisos vigentes o futuros para no atribuirle defectos historicos; calendario mensual, continuidad de periodos, periodos existentes acotados a la vigencia contractual, al calendario mensual y a numeracion cronologica, minimo operativo, renovaciones de contratos con tramos usando por defecto la base del ultimo tramo vigente o politica documentada no sensible cuando cambia monto/moneda, renovacion automatica operacional que extiende la vigencia creando `PeriodoContractual` auditable y queda bloqueada por `AvisoTermino` registrado, propiedad principal o vinculada activa en contratos vigentes/futuros, `Contrato.full_clean()` y API exigen gasto comun activo estructurado cuando `tiene_gastos_comunes` aplica, composicion de roles principal/vinculada, contrato acotado a una propiedad o pareja principal/vinculada, propiedad vinculada sin contrato independiente, pareja principal/vinculada con mismo codigo efectivo, contrato futuro con aviso/terminacion, avisos de termino con fecha efectiva dentro del contrato, conflicto entre aviso, renovacion ya ejecutada y contrato futuro resuelto con referencia no sensible y motivo trazable sin cancelar ni reescribir efectos producidos, terminacion anticipada con ultimo mes parcial solo con regla o decision de prorrata no sensible y evento auditable dedicado, entrega de llaves con garantia cubierta o autorizacion auditada no sensible cuando `fecha_entrega` queda registrada, codigo efectivo `001-999` en contrato, pagos existentes alineados a la propiedad principal, al periodo contractual y al vencimiento del mes operativo, contratos retroactivos registrados despues del dia 5 alertados para posible notificacion manual sin bloquear por si solos, bloqueo de reconstruccion automatica de cobros vencidos antes del registro operativo, pagos existentes de cobro pasado retroactivo marcados defectuosos, pagos en estado pagado efectivo con monto y fecha trazable, ajustes contractuales existentes normalizados al primer dia del mes y acotados a la vigencia contractual, pagos/distribuciones existentes, respaldo `ValorUFDiario` valido para pagos dependientes de UF, con procedencia manual trazable cuando aplique, y coherencia de garantias con `HistorialGarantia`, fechas de recepcion/cierre, movimiento final de garantia, cronologia de movimientos derivados, garantias parciales abiertas con aceptacion formal trazable o marca de incompletitud y garantias con exceso sobre lo pactado solo con resolucion no sensible ya tienen gate local. |
| CobranzaActiva | PRD, gates canales/WebPay | `backend/cobranza`, `canales`, frontend, `backend/core/stage2_cobranza_readiness.py`, `scripts/run-stage2-readiness-gate.ps1` | 2 | parcial | Cobros reproducibles sin envios reales accidentales | Cadencias de notificacion por contrato/canal habilitado se normalizan, exigen canal activo del mandato, redactan evidencia sensible heredada y son bloqueantes en readiness si faltan para contratos vigentes/futuros; los pagos mensuales pendientes/atrasados con cadencia activa materializan recordatorios locales por pago/canal/dia sin enviar proveedores, se exponen en snapshot/backoffice y readiness bloquea pagos cobrables sin programacion, con programacion heredada invalida, ligada a configuracion inactiva u omitida sin motivo operativo no sensible; pagos mensuales abiertos vencidos se refrescan contra fecha de corte, pasan de `pendiente` a `atrasado`, recalculan `dias_mora`, sincronizan estado de cuenta y readiness bloquea pendientes vencidos o mora atrasada; el efecto economico del codigo efectivo queda persistido como `monto_efecto_codigo_efectivo_clp`, debe cuadrar con `monto_calculado_clp - monto_facturable_clp` y, si no es cero, conservar evento auditable `cobranza.pago_mensual.effective_code_applied` con actor y montos alineados; el score de pago excluye pagos sin registro operativo valido y expone `score_meses_sin_registro_operativo` para detectar estados heredados desalineados; los pagos `pagado_por_acuerdo_termino` o `condonado` requieren referencia no sensible, motivo y evento auditable `cobranza.pago_mensual.exceptional_state_resolved` con actor y resolucion alineada; pagos originales en `en_repactacion` o `pagado_via_repactacion` deben enlazar una `RepactacionDeuda` del mismo contrato/arrendatario, conservar `dias_mora` y mantener estado compatible del plan activo/cumplido; registro manual de envio exige `external_ref` trazable no sensible y revalida gate/identidad/destinatario/mandato; `MensajeSaliente.clean()` rechaza estados `preparado`/`enviado` sin gate abierto, readiness Email, identidad activa, destinatario, mandato operativo, contexto WhatsApp valido o documento formalizado cuando la politica lo exige, y tambien exige `external_ref` no sensible, `enviado_at` y evento auditable con actor para mensajes enviados; Email abierto exige `evidencia_ref`, prueba aislada/envio, OAuth/credencial validada, `IdentidadDeEnvio` activa y `AsignacionCanalOperacion` activa sobre mandato operativo activo, todo con refs no sensibles; mensajes con `DocumentoEmitido` cuya politica exige firma/notaria solo se preparan o marcan enviados si el documento ya esta formalizado; WhatsApp queda cerrado por defecto sin opt-in evidenciado con referencia no sensible, template aprobado, ventana permitida, identidad y asignacion activas cuando se abre, sin refs sensibles en gate ni evidencia de opt-in; un bloqueo definitivo de WhatsApp debe marcar el contacto con motivo, evidencia no sensible, fecha, evento auditable y alerta administrativa, la rehabilitacion manual conserva la traza del bloqueo, y un bloqueo/fallo de mensaje WhatsApp debe conservar Email alternativo preparado/enviado o alerta critica/fallback trazable; WebPay tiene gate `WebPay.IntentoPago` con `evidencia_ref` no sensible, intento local con `return_url_ref` no sensible, `fecha_pago_webpay` separada y confirmacion manual solo con `external_ref` no sensible, pago mensual pagado con la misma fecha WebPay y gate revalidado; garantias recibidas parcialmente exponen brecha, incompletitud y aceptacion formal no sensible hasta regularizarse; repactaciones existentes se validan contra coherencia saldo/estado, total de plan y excepcion formal auditable cuando no cubren toda la deuda original; codigos residuales existentes se validan contra formato canonico `CCR-XXXXXX` con caracteres no ambiguos; estados de cuenta existentes deben estar recalculados contra pagos abiertos, repactaciones activas y codigos residuales activos; valores UF manuales requieren evidencia, motivo, responsable no sensibles y evento auditable con actor; APIs y snapshots redactan refs sensibles, `restricciones_operativas`, `provider_payload` sensible, evidencia opt-in/bloqueo/rehabilitacion WhatsApp heredada y `storage_ref` documental expuesto por Canales ya persistidos en gates, mensajes salientes e intentos WebPay antes de exponerlos al backoffice, y el modelo rechaza nuevas escrituras de mensajes salientes con `provider_payload` sensible; `audit_stage2_cobranza_readiness` detecta UF manual sin procedencia/evento auditable, refs sensibles en gates, opt-in WhatsApp, bloqueos definitivos sin traza/evento/alerta, mensajes WhatsApp bloqueados/fallidos sin fallback trazable, mensajes enviados sin timestamp, sin evento auditable o con evento auditable sin actor/`external_ref` no sensible alineado, mensajes/confirmaciones WebPay con `external_ref` sensible o desalineacion con el pago mensual, documentos no formalizados en mensajes preparados/enviados cuando la politica exige firma/notaria, pagos pendientes vencidos o mora desactualizada, efecto de codigo efectivo descuadrado o sin evento auditable, pagos excepcionales sin resolucion trazable o sin evento auditable, pagos en estados de repactacion sin plan trazable o con plan incompatible, estados de cuenta faltantes o desactualizados, repactaciones inconsistentes, repactaciones parciales sin excepcion formal o sin evento auditable, codigos residuales no canonicos e intentos WebPay con `return_url_ref` o `provider_payload` sensible, y `run-stage2-readiness-gate.ps1` consolida readiness sin llamar proveedores, exige `SourceLabel`/`AuthorizationRef` para fuentes evidenciales y solo cierra con `source_kind` `snapshot_controlado` o `real_autorizado`. Falta prueba externa real/controlada de correo/WebPay y datos de Etapa 1 confirmados para cierre. |
| Conciliacion | ADR banca, gates banco | `backend/conciliacion`, `backend/core/stage3_conciliacion_readiness.py`, `scripts/run-stage3-readiness-gate.ps1`, frontend | 3 | parcial | Saldo sistema igual a saldo banco con data controlada | Conexion bancaria activa/primaria exige referencias no sensibles de gate, credencial, conectividad, movimientos y saldos segun capacidad; movimientos `provider_sync` solo entran por conexion primaria lista con `transaction_id_banco` no sensible y no duplicado por conexion, reforzado por modelo y constraint DB, toda `referencia` bancaria de movimiento debe ser no sensible, y carga manual exige evidencia de importacion no sensible; movimientos conciliados exactos existentes deben mantener target coherente con pago mensual pagado, codigo residual pagado o transferencia intercuenta trazada de la misma cuenta recaudadora; ingresos desconocidos existentes deben coincidir con movimiento bancario, cuenta, monto, fecha, descripcion, tipo abono y estado de conciliacion; ingresos desconocidos resueltos manualmente requieren pago mensual, contrato, periodo economico canonico `YYYY-MM` alineado al mes/anio del `PagoMensual`, criterio aplicado, evidencia no sensible y motivo; los cargos bancarios conciliados exactos requieren resolucion manual resuelta, y los cargos bancarios resueltos manualmente requieren `CategoriaMovimiento`, entidad afectada, periodo economico canonico `YYYY-MM`, criterio de reparto, evidencia no sensible y motivo; las transferencias internas/intercuenta resueltas manualmente requieren par cargo/abono, cuentas distintas, monto opuesto equivalente, periodo economico canonico `YYYY-MM`, owner origen/destino, criterio de conciliacion, evidencia no sensible, responsable y motivo, y readiness detecta pares o resoluciones heredadas cerradas sin contexto, con periodo/target inconsistente o con evidencia sensible; resoluciones manuales abiertas que quedan obsoletas por match exacto u otra resolucion manual se cierran como `superseded` con motivo, metadata y evento de auditoria alineado, y readiness bloquea supersesiones sin metadata, motivo o evento de auditoria alineado; `CuadraturaBancaria` registra saldo sistema, saldo banco, diferencia calculada, fecha de cuadratura alineada al periodo economico, evidencia y responsable por cuenta/periodo, y readiness bloquea cierres sin registro para cada cuenta/periodo con movimientos, sin estado cuadrado, con refs sensibles, con periodo/fecha desalineados o con diferencia distinta de cero; API/snapshot redactan refs bancarias, incluyendo `referencia` de movimientos, y refs de cuadratura sensibles ya persistidas; `audit_stage3_conciliacion_readiness` y `run-stage3-readiness-gate.ps1` consolidan conexiones, movimientos, ingresos desconocidos, resoluciones manuales, transferencias intercuenta, cuadraturas, senales de saldo, continuidad local de saldos reportados, referencias finales, cargos exactos sin resolucion y deteccion de refs sensibles existentes sin llamar bancos. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel` y `AuthorizationRef` no sensibles. Falta banco real o snapshot autorizado, evidencia Etapa 2, prueba bancaria, cuadratura sistema/banco y responsable para cierre. |
| Contabilidad | ADR contabilidad nativa | `backend/contabilidad`, `backend/core/stage5_contabilidad_readiness.py`, `scripts/run-stage5-readiness-gate.ps1`, reporting | 5 | parcial | Eventos, reglas, asientos y cierre mensual | Preparar y aprobar cierre mensual exige eventos posteados, asientos balanceados, `periodo_contable` coherente con `fecha_contable`, `hash_integridad` presente y vigente para asientos contabilizados, movimientos de asiento obligatorios que sumen los totales debe/haber y cuentas contables de la misma empresa del evento; `EventoContable` evita doble contabilizacion efectiva del mismo hecho economico dejando en revision un evento nuevo si ya existe otro contabilizado para la misma empresa, tipo y entidad origen, y readiness reporta `stage5.duplicate_posted_events` para snapshots heredados; `MovimientoAsiento.clean()` bloquea nuevas escrituras con cuentas de otra empresa y readiness bloquea snapshots heredados con esa incoherencia; tambien bloquea si existen movimientos bancarios no resueltos del periodo para cuentas de la empresa. Las transferencias intercuenta conciliadas que involucren cuentas recaudadoras con owner empresa generan eventos contables idempotentes de salida/entrada (`TransferenciaIntercuentaSalida`, `TransferenciaIntercuentaEntrada`) y `audit_stage5_contabilidad_readiness` bloquea snapshots con transferencias de empresa sin esos eventos. Un cierre aprobado solo se reabre con `PoliticaReversoContable` activa para `reapertura_cierre_mensual`, que permita reapertura y exija aprobacion; ademas la reapertura debe aplicar un efecto contable posterior (`reverso` o `asiento_complementario`) con motivo, efecto esperado, monto, evidencia no sensible y `EventoContable` contabilizado bajo regla/matriz activa. `audit_stage5_contabilidad_readiness` marca como brecha los cierres aprobados sin politica, cierres reabiertos sin efecto, efectos sin evento contabilizado y efectos con referencias sensibles. APIs y reporting redactan payloads, `storage_ref` y refs de centro de resultado sensibles ya persistidos en eventos, movimientos, obligaciones, libros, balances y cierres; el dominio rechaza nuevas escrituras sensibles y `audit_stage5_contabilidad_readiness` las detecta como brecha bloqueante sin exponer valores. `audit_stage5_contabilidad_readiness` y `run-stage5-readiness-gate.ps1` consolidan configuracion fiscal, reglas/matriz, eventos, asientos, hash vigente, integridad de movimientos, snapshots, cierres, efectos de reapertura, transferencias intercuenta y conciliacion del periodo sin conectar servicios externos. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel` y `AuthorizationRef` no sensibles. Sigue faltando Conciliacion cerrada, ledger/reportes controlados y responsable para cierre. |
| Documentos | ADR estrategia documental | `backend/documentos`, `scripts/run-stage5-documents-readiness-gate.ps1`, backoffice documentos, docs operativos | 5 | parcial | PDF canonico, origen, firma/notaria definida | Documentos emitidos exigen `storage_ref` PDF no sensible, `checksum` SHA-256 canonico, `usuario` responsable y politica activa para su tipo documental; `DocumentoEmitido.clean()` bloquea nuevas escrituras sin responsable o sin politica activa, la API valida create usando el usuario autenticado antes de persistir, y `PoliticaFirmaYNotaria.clean()` evita desactivar politicas ya usadas por documentos existentes. APIs, snapshot y admin/backoffice redactan `storage_ref`, `evidencia_formalizacion_ref` y `correccion_ref` sensibles heredados antes de exponer documentos, conservan metadata trazable y quitan esas refs de la busqueda administrativa; readiness documental detecta referencias sensibles, checksums heredados no canonicos, documentos sin usuario y documentos heredados sin politica activa como brechas bloqueantes sin imprimir valores. Formalizacion bloquea comprobantes notariales borrador/cancelados, documentos borrador/archivados/cancelados, cualquier intento de pasar a `formalizado` por create/update generico, mutaciones posteriores de documentos formalizados y re-formalizaciones, obligando el endpoint `formalizar/` con auditoria especifica desde estado `emitido`; las correcciones posteriores se registran como versiones correctivas con `documento_origen` formalizado, mismo expediente/tipo documental, PDF/checksum propios, `correccion_ref` no sensible y auditoria `documentos.documento_emitido.corrective_version_created`; `audit_document_readiness` bloquea formalizados sin evento `documentos.documento_emitido.formalized`, versiones correctivas heredadas invalidas o sin auditoria dedicada, y formalizados con politica notarial sin recepcion, sin comprobante, con comprobante de tipo incorrecto, de otro expediente o en estado no permitido. `audit_document_readiness` y `run-stage5-documents-readiness-gate.ps1` consolidan politicas activas por tipo documental, metadata, responsables y prueba PDF controlada sin leer storage real, y rechazan outputs dentro del repo fuera de `local-evidence/` antes de recolectar readiness. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel` y `AuthorizationRef` no sensibles. Falta decision final de politica firma/notaria, prueba PDF controlada y responsable para cierre. |
| SII | ADR SII, matriz gates | `backend/sii`, `backend/core/stage4_sii_readiness.py`, `scripts/run-stage4-readiness-gate.ps1`, backoffice SII | 4 | parcial | Certificacion/ambiente SII y regla fiscal validada | Capacidad SII abierta exige refs no sensibles de certificado, evidencia, prueba de flujo, autorizacion de ambiente, regla fiscal y `ConfiguracionFiscalEmpresa` activa de la misma empresa dentro del regimen fiscal automatizable v1; el dominio/API rechaza capacidades abiertas sin esa configuracion activa, y una empresa fuera de ese regimen no puede abrir automatizacion tributaria oficial. DTE/F29/anuales bloquean referencias sensibles en tracking, borradores o paquetes, rechazan por dominio nuevas escrituras asociadas a empresas sin `ConfiguracionFiscalEmpresa` activa propia, y APIs/snapshot/auditoria de cambios DTE redactan refs o payloads sensibles heredados antes de exponerlos o persistir metadata operativa; borradores/estados revalidan readiness local y presentaciones finales siguen bloqueadas hasta gate externo autorizado. DTE, F29, DDJJ y F22 validan que la capacidad SII asignada sea exactamente la familia tributaria correspondiente (`DTEEmision`, `F29Preparacion`, `DDJJPreparacion`, `F22Preparacion`) y readiness bloquea snapshots heredados con capacidad cruzada. F29, DDJJ y F22 en estado preparado, aprobado, observado o rectificado revalidan capacidad SII abierta/lista, y `audit_stage4_sii_readiness` bloquea DTE externo o preparaciones tributarias avanzadas con capacidad condicionada, cerrada o invalida. `audit_stage4_sii_readiness` y `run-stage4-readiness-gate.ps1` consolidan configuracion fiscal por empresa, capacidades, DTE, F29 y preparacion anual sin conectar SII ni leer certificados, y detectan refs sensibles existentes. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel` y `AuthorizationRef` no sensibles. Falta ambiente SII real/controlado autorizado, evidencia de ledger, regla fiscal validada y responsable para cierre. |
| Renta Anual | PRD, SII, contabilidad, documentos | `backend/sii`, `backend/reporting`, `backend/core/stage6_renta_anual_readiness.py`, `scripts/run-stage6-readiness-gate.ps1`, documentos tributarios | 6 | parcial | Doce cierres mensuales, reglas fiscales, DDJJ/F22 y certificados trazables | `audit_stage6_renta_anual_readiness` y `run-stage6-readiness-gate.ps1` consolidan configuracion fiscal, capacidades anuales DDJJ/F22, cierres aprobados, obligaciones mensuales, ProcesoRentaAnual, DDJJ, F22 y respaldos tributarios PDF sin conectar SII ni leer certificados reales; capacidades anuales, proceso, DDJJ y F22 bloquean si pertenecen a empresas sin configuracion fiscal activa propia, y el dominio/API rechaza nuevas escrituras equivalentes. El dominio SII rechaza F29, ProcesoRentaAnual, DDJJ y F22 en estados aprobados, presentados, observados o rectificados si falta la referencia final trazable correspondiente, y readiness clasifica explicitamente referencias finales sensibles en ProcesoRentaAnual, DDJJ y F22 sin exponer valores. ProcesoRentaAnual, DDJJ y F22 tambien validan que sus resumenes anuales apunten al ano comercial inmediatamente anterior al `anio_tributario`, y readiness bloquea snapshots heredados con `fiscal_year` desalineado. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel` y `AuthorizationRef` no sensibles. Falta evidencia final con doce cierres/snapshot controlado, regla fiscal validada, certificados/respaldos controlados y responsable tributario. |
| Reporting | PRD, contabilidad, SII | `backend/reporting`, `backend/core/stage7_reporting_readiness.py`, `scripts/run-stage7-readiness-gate.ps1`, frontend reporting | 7 | parcial | Reportes trazables a ledger/datos/documentos | Resumen financiero mensual exige cierre aprobado y eventos con asiento posteado, balanceado, con movimientos y `hash_integridad` vigente; libros por periodo exigen snapshots contables aprobados, balance cuadrado y cierre aprobado, y redactan `storage_ref`/resumen sensibles heredados antes de exponerlos; resumen tributario anual exige proceso/DDJJ/F22 con resumen trazable, `fiscal_year` alineado al ano comercial inmediatamente anterior al `anio_tributario` y `ConfiguracionFiscalEmpresa` activa propia por empresa incluida, redactando `paquete_ref`, `borrador_ref` y payloads anuales sensibles heredados antes de exponerlos; `audit_stage7_reporting_readiness` consolida esos origenes mas prueba API, visualizacion backoffice y responsables sin ejecutar smoke publico ni leer datos reales, bloquea procesos/DDJJ/F22 heredados con ejercicio anual desalineado, payloads anuales sensibles y referencias finales sensibles sin exponer valores. `local`, `fixture` y `demo` solo diagnostican; el cierre exige `source_kind` `snapshot_controlado` o `real_autorizado` con `SourceLabel` y `AuthorizationRef` no sensibles, reenviados por `run-stage7-readiness-gate.ps1` como `ReportingSourceLabel` y `ReportingAuthorizationRef`. Falta evidencia con cierres/snapshot controlado y datos reales autorizados para cierre final. |
| Migracion legacy | Fuente de verdad, migration README | `migration/`, `scripts/assert-repo-hygiene.ps1` | 1 | parcial | Extractores read-only, clasificacion migrable, contexto sensible externo y bundles no versionados | Inventario metadata/schema-only detecto `.env`, CSV/SQL, Excel/JSON y varias `.db`/`.sqlite3` legacy con esquema compatible de Etapa 1; mientras no haya fuente autorizada, `scripts/run-stage1-local-readiness.ps1` y acceptance verifican preparacion segura con `source_kind=local`, sin solicitar secretos ni simular `snapshot_controlado`, y acceptance tambien verifica que un `snapshot_controlado` vacio falle como `bloqueado_dato_real` con `stage1.data_missing`; `scripts/assert-repo-hygiene.ps1` bloquea regresion de `.env`, DBs, bundles generados, dumps, snapshots, certificados y evidencia local versionada en el root activo; exportador y reportes de migracion rechazan salidas dentro del repo fuera de `migration/bundles/` antes de leer legacy, bundles o DBs; para cierre, autorizar una fuente concreta y validar snapshot/bundle controlado con `scripts/run-stage1-snapshot-gate.ps1`, que exige `SourceLabel`, `AuthorizationRef` y `ResponsibleRef` no sensibles; decidir tratamiento de historial Git/savegames para `BLK-008`. |
| Operacion productiva | Runbooks, gates externos | `backend/health`, `backend/core/operational_observability.py`, `backend/core/models.py`, `backend/core/views.py`, `frontend/src/backoffice/workspaces/OverviewWorkspace.tsx`, `docs/operations`, `scripts/run-postgres-restore-rehearsal.ps1`, `scripts/run-stage7-readiness-gate.ps1`, infra, CI | 7 | parcial | Backup/restore, monitoreo, smoke, rollback, aceptacion | Health/readiness publicos redactan fallas de dependencias; hay rehearsal PostgreSQL local sintetico para preparar backup/restore sin datos reales, y su wrapper rechaza outputs dentro del repo fuera de `local-evidence/` antes de generar plan o tocar Docker; auditoria local de observabilidad agrega gates, integraciones, backlogs y senales runtime, y rechaza outputs dentro del repo fuera de `local-evidence/` antes de auditar; `OperationalRuntimeSignal` permite registrar latencia mensual, cola/tareas, webhooks fallidos y crons fallidos con evidencia y payload no sensibles, rechazando tambien claves de payload con forma de secreto o credencial, pero solo `snapshot_controlado` o `real_autorizado` con `source_label`, `authorization_ref` y observacion dentro de las ultimas 24 horas habilitan cierre productivo; API/backoffice autenticados muestran observabilidad operativa con referencias y valores runtime redactados; el release gate ejecuta readiness local Etapa 7, exige Reporting listo con fuente autorizada, observabilidad runtime autorizada y reciente, restore de backup/snapshot autorizado, smoke publico autorizado y aceptacion final autorizada con referencias no sensibles; para restore y smoke `authorization_ref` debe ser explicito y `responsible_ref` no lo sustituye, y las referencias sensibles en evidencia de restore/smoke/aceptacion final se clasifican con codigos especificos sin exponer valores. Confirma que resultados sinteticos/locales, mediciones antiguas o referencias simples no cierran Operacion productiva. Falta ejecutar restore con backup/snapshot autorizado, medir senales recientes en ambiente real/controlado, smoke real autorizado, Reporting autorizado y aceptacion final autorizada. |
