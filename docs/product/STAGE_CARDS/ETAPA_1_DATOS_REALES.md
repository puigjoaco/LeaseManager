# Etapa 1 - Datos reales y matriz base

## Objetivo

Confirmar entidades, propiedades, contratos, cuentas, facturacion y reglas base
contra datos reales o snapshot controlado.

## Alcance

- Socios, empresas, comunidades y participaciones.
- Propiedades, cuentas recaudadoras y mandatos.
- Arrendatarios, contactos de pago, contratos, periodos, garantias y
  propiedades por contrato.
- Codeudores solidarios cuando existan, con snapshot de identidad trazable.
- Matriz contrato-propiedad-cuenta-facturacion.

## Gate

- Snapshot o fuente real autorizada.
- Extractores read-only.
- Sin secretos versionados.
- Referencias trazables no sensibles de `AuthorizationRef` y `ResponsibleRef`
  en el gate evidencial.
- El JSON del auditor debe exponer `sections.source_trace`,
  `sections.source_trace_sensitive`, `sections.final_evidence` y
  `sections.final_evidence_sensitive` para distinguir trazas faltantes de
  valores sensibles sin publicar valores crudos.
- Guard deterministico de higiene del repo: `scripts/assert-repo-hygiene.ps1`
  debe pasar y acceptance lo ejecuta con `-IncludeUntracked` para evitar
  reintroducir `.env`, DBs locales/historicas, bundles generados, dumps,
  snapshots, certificados, evidencia local versionada o artefactos sensibles no
  ignorados.
- Clasificacion de cada agregado migrable.
- Validacion de participaciones actualmente vigentes: para activar empresas o
  comunidades solo cuentan participaciones activas con `vigente_desde` ya
  alcanzado y sin `vigente_hasta` vencido.
- Duplicidad de participantes vigentes: una empresa o comunidad activa no
  puede repetir el mismo socio o empresa participante dentro del set
  actualmente vigente; participaciones historicas no vigentes pueden coexistir
  con la participacion actual del mismo participante.
- Validacion de representaciones actualmente vigentes: para activar
  comunidades o bloquear desactivaciones de socios solo cuentan
  representaciones activas con `vigente_desde` ya alcanzado y sin
  `vigente_hasta` vencido; representaciones futuras no sustituyen la
  representacion vigente.
- Planificacion de representaciones de comunidad: pueden coexistir
  representaciones activas historicas, actuales o futuras solo si sus ventanas
  efectivas no se solapan; el dominio y el auditor bloquean cualquier snapshot
  con mas de una representacion vigente para la misma fecha.
- Representaciones patrimoniales futuras: si el representante programado no es
  participante vigente hoy, debe existir una participacion activa cuya ventana
  se solape con la ventana futura de la representacion; no debe marcarse
  invalida una planificacion futura correctamente alineada.
- Representaciones designadas de comunidad: si una comunidad usa un
  representante `designado` fuera de las participaciones patrimoniales, debe
  conservar `evidencia_ref` formal trazable no sensible. API, snapshot,
  admin/backoffice y auditor Etapa 1 bloquean o redactan datos heredados sin
  esa traza. Las observaciones de representacion no pueden contener URLs,
  correos, tokens ni credenciales; la API redacta observaciones heredadas
  sensibles y el auditor las clasifica como defecto especifico. El admin
  Django no permite alta, edicion ni borrado manual de representaciones; deben
  cerrarse por vigencia, inactivacion o flujo auditado.
- Validacion de participantes patrimoniales activos: una participacion activa
  solo puede apuntar a un socio activo o a una empresa participante activa con
  participaciones completas.
- Transferencia, reemplazo o redistribucion de participaciones: el flujo
  operacional debe cerrar la participacion origen, crear destinos vigentes
  desde la fecha efectiva, conservar el 100% del owner y registrar auditoria
  dedicada con actor, owner, fecha efectiva, destinos, porcentaje, motivo no
  sensible y evidencia no sensible. El auditor Etapa 1 bloquea sucesiones
  heredadas con sucesor inmediato sin evento auditable o con auditoria
  incompleta, desalineada, con motivo sensible o evidencia sensible. Las
  empresas y comunidades existentes no aceptan
  reescritura directa de `participaciones` por update generico; cualquier
  cambio de ownership debe usar el flujo auditado.
- Validacion de transiciones de estado patrimonial: socios, empresas y
  comunidades no pueden desactivarse si sostienen propiedades,
  representaciones o participaciones activas vigentes, incluyendo la estructura
  patrimonial propia de empresas/comunidades que debe transferirse o cerrarse
  antes de la salida operativa. Socios, empresas y comunidades tampoco pueden
  quedar inactivos mientras conserven cuentas recaudadoras activas o mandatos
  operativos activos; socios y empresas tampoco pueden conservar identidades de
  envio activas despues de su salida operativa.
- El admin Django de Patrimonio no permite alta, edicion ni borrado manual de
  socios, empresas, comunidades, participaciones ni propiedades; las altas,
  bajas y cambios estructurales deben pasar por API, estado, vigencia o flujo
  auditado.
- Las altas y ediciones API de Patrimonio deben persistir la mutacion y los
  eventos `created`, `updated` o `state_changed` de forma atomica; si falla la
  auditoria, no deben quedar entidades patrimoniales ni participaciones
  anidadas persistidas sin traza. Los eventos `state_changed` deben conservar
  metadata minima con campo de estado, estado anterior y estado nuevo.
- El auditor Etapa 1 bloquea eventos `state_changed` heredados de Patrimonio,
  Operacion o Contratos que no conserven esa metadata minima de transicion.
- La matriz debe incluir al menos un contrato vigente o futuro; contratos solo
  historicos no constituyen evidencia operativa de Etapa 1.
- Validacion de no duplicar propiedades activas por rol de avaluo normalizado
  ni identidad operativa fuerte; `Propiedad.full_clean()` y la API bloquean
  nuevas escrituras duplicadas, y el auditor Etapa 1 conserva la deteccion de
  snapshots heredados.
- Validacion de que cada contrato vigente o futuro tenga al menos un canal
  operativo activo asignado por su mandato; `Contrato.full_clean()`, la API y
  el auditor Etapa 1 bloquean contratos nuevos o heredados sin esa cobertura.
  El snapshot operativo y el backoffice de Operacion muestran asignaciones de
  canal por mandato, identidad, prioridad y estado para verificar cobertura sin
  abrir proveedores externos. El backoffice de Operacion tambien permite
  crear y editar esas asignaciones mediante la API auditada, filtrando
  identidades por canal antes de persistir cobertura operativa.
- Validacion de que las identidades de envio activas usen `credencial_ref`
  trazable no sensible; API y admin/backoffice deben redactar referencias
  sensibles heredadas antes de exponerlas. El snapshot operativo y la tabla de
  identidades del backoffice muestran la referencia de credencial solo en su
  version redactada para verificar cobertura de canal sin exponer secretos. El
  backoffice de Operacion tambien permite crear y editar identidades de envio
  mediante la API auditada, restringiendo owner a empresa o socio y exigiendo
  referencia de credencial cuando la identidad queda activa. El snapshot
  operativo conserva `owner_id` junto a `owner_tipo` para que la edicion desde
  backoffice mantenga el owner exacto sin depender de consultas auxiliares.
- Validacion de transiciones operativas: cuentas recaudadoras, mandatos,
  identidades de envio y asignaciones de canal no pueden pausarse,
  suspenderse o inactivarse si dejan contratos vigentes/futuros, mandatos o
  canales activos sin cobertura operativa. Una identidad con asignaciones
  activas tampoco puede cambiar canal u owner si deja incompatibles esas
  asignaciones. El admin Django no permite alta, edicion ni borrado manual de
  cuentas recaudadoras, identidades de envio, mandatos ni asignaciones de
  canal; los cambios y bajas deben expresarse por API, estado, vigencia o
  flujo auditado.
- Las altas y ediciones API de Operacion deben persistir la mutacion y los
  eventos `created`, `updated` o `state_changed` de forma atomica; si falla la
  auditoria, no deben quedar cuentas recaudadoras, identidades, mandatos ni
  asignaciones de canal mutadas sin traza. Los eventos `state_changed` deben
  conservar metadata minima con campo de estado, estado anterior y estado
  nuevo.
- Validacion de cuentas recaudadoras activas: una cuenta activa debe declarar
  uso operativo, modo `manual_controlado` o `gate_bancario`, y evidencia
  operativa trazable no sensible; API, snapshot y admin/backoffice redactan
  referencias sensibles heredadas antes de exponerlas, y el auditor Etapa 1
  detecta faltantes o referencias sensibles heredadas. El admin Django no
  expone ni busca `numero_cuenta` ni `titular_rut` crudos en cuentas
  recaudadoras ni muestra cuentas asociadas a mandatos mediante labels con
  numero bancario.
- Validacion de cuenta activa para facturacion operativa: un
  `MandatoOperacion` activo con `entidad_facturadora` requiere que esa empresa
  tenga una cuenta recaudadora activa propia ademas de la cuenta activa del
  recaudador del mandato; la API bloquea nuevas operaciones incompletas y el
  auditor Etapa 1 emite `stage1.facturacion.cuenta_activa_faltante` para
  snapshots heredados.
- Validacion de que cada contrato vigente o futuro este cubierto por la
  vigencia del `MandatoOperacion` que define propiedad, cuenta y facturacion;
  un mandato con contratos vigentes/futuros no puede recortar su vigencia fuera
  del rango contractual ya dependiente.
- Planificacion de mandatos operativos: pueden coexistir mandatos activos
  historicos, actuales o futuros de una misma propiedad solo si sus ventanas
  efectivas no se solapan; el dominio y el auditor bloquean cualquier snapshot
  con mas de un mandato vigente para la misma fecha.
- Autoridad operativa de mandato: un `MandatoOperacion` activo que autoriza
  comunicacion o facturacion de documentos debe conservar nombre, RUT valido
  normalizado y evidencia trazable no sensible de su representante/autoridad;
  API, snapshot, admin/backoffice y auditor Etapa 1 detectan faltantes, RUT
  invalido o referencias sensibles. El backoffice de Operacion muestra nombre,
  RUT, evidencia redactada, autorizaciones y ventana de vigencia para que la
  cobertura operativa sea revisable antes de construir contratos dependientes.
- Validacion de que cada propiedad principal o vinculada de contratos vigentes
  o futuros este activa.
- Servicios y gastos comunes estructurados: `ServicioPropiedad` registra tipo
  de servicio, proveedor/administracion, numero de cliente, evidencia opcional
  no sensible y estado; API, snapshot y admin/backoffice exponen evidencia
  heredada solo mediante version redactada, y `Contrato.full_clean()`, la API y
  el auditor Etapa 1 bloquean contratos vigentes/futuros con gastos comunes si
  la propiedad principal no tiene un gasto comun activo estructurado. El admin
  Django no permite alta, edicion ni borrado manual de servicios de propiedad
  para no destruir cobertura operativa ni evidencia. El backoffice de
  Patrimonio muestra los servicios de cada propiedad desde el snapshot
  redaccionado para que la cobertura de gastos comunes sea verificable antes
  de construir contratos dependientes. El backoffice de Contratos consume esa
  cobertura del mandato seleccionado, muestra el estado del gasto comun activo
  y bloquea el guardado de contratos vigentes/futuros con gastos comunes cuando
  la propiedad principal no conserva ese servicio estructurado.
- Validacion de roles contrato-propiedad: exactamente una propiedad principal
  y, si hay pareja, una propiedad vinculada.
- Validacion de que cada contrato vigente o futuro cubra una sola propiedad o
  una pareja propiedad principal + vinculada.
- Validacion de que la pareja propiedad principal + vinculada comparta el
  `CodigoConciliacionEfectivo` de la propiedad principal.
- Validacion de codeudores solidarios: snapshot con nombre/RUT valido desde la
  API anidada y el auditor, sin duplicados activos y maximo 3 activos por
  contrato. El backoffice de Contratos permite informar hasta tres codeudores
  solidarios al crear o editar contratos simples, conserva fecha de inclusion y
  estado en el payload anidado auditado, y muestra cobertura y detalle de
  codeudores desde el snapshot del contrato.
- Validacion de contratos con arrendatario empresa: API/modelo exigen snapshot
  de representante legal con nombre y RUT valido normalizado, y el auditor
  detecta faltantes, incompletos o RUT invalido en datos heredados. El
  backoffice de Contratos captura nombre/RUT de representante legal, bloquea
  altas vigentes/futuras de empresa sin esos datos y muestra cobertura de
  snapshot en la tabla de contratos.
- Readiness operativo de arrendatario: `Contrato.full_clean()`, la API y el
  auditor Etapa 1 bloquean contratos vigentes/futuros si el arrendatario no
  tiene estado de contacto activo, email o telefono operativo, domicilio de
  notificaciones y al menos un contacto de pago activo estructurado. Los
  contactos de pago conservan nombre, rol operativo, email o telefono y
  evidencia opcional no sensible; API, snapshot y admin/backoffice exponen
  evidencia heredada solo mediante version redactada. El backoffice de
  Contratos captura contactos de pago estructurados desde la API auditada,
  exige arrendatario, nombre y medio operativo antes de enviar, y muestra
  cobertura de contacto de pago en la tabla de arrendatarios y en una lista
  dedicada.
- El admin Django de Contratos no permite alta, edicion ni borrado manual de
  arrendatarios, contactos de pago, contratos, relaciones contrato-propiedad,
  periodos, codeudores ni avisos de termino. Las altas, bajas y cambios
  contractuales deben expresarse por API, estado, vigencia o flujo auditado.
- Las altas y ediciones API de Contratos deben persistir la mutacion y los
  eventos `created`, `updated`, `state_changed` y trazas contractuales
  derivadas de forma atomica; si falla la auditoria, no deben quedar
  arrendatarios, contactos de pago, contratos anidados ni estados
  contractuales mutados sin traza. Los eventos `state_changed` deben conservar
  metadata minima con campo de estado, estado anterior y estado nuevo.
- Validacion de telefonos para mensajeria: si un arrendatario usa WhatsApp
  operativo, el telefono debe estar en formato internacional; numeros locales
  o ambiguos quedan bloqueados para Canales y clasificados por el auditor
  Etapa 1 en snapshots heredados; admin/backoffice expone refs/motivos
  WhatsApp heredados solo mediante version redactada.
- Override explicito de `IdentidadDeEnvio` por contrato: si existe, debe estar
  activo y pertenecer a la entidad facturadora o al administrador operativo
  autorizado por el mandato; Canales lo usa antes de la asignacion del mandato
  cuando coincide con el canal solicitado. El backoffice de Contratos filtra el
  selector de override segun el mandato elegido, solo ofrece identidades activas
  cuyo owner sea administrador operativo o entidad facturadora autorizada, y
  marca overrides heredados no elegibles para revision.
- Politica documental contractual: cada contrato vigente o futuro debe
  referenciar una `PoliticaFirmaYNotaria` activa de tipo
  `contrato_principal`; API, snapshot y auditor Etapa 1 detectan politicas
  faltantes, inactivas o de tipo documental incorrecto.
- Perfil documental de arrendatario persona natural: cuando la politica
  documental contractual lo exige, contratos vigentes/futuros requieren
  nacionalidad, estado civil y profesion; API, snapshot y auditor Etapa 1
  detectan datos faltantes en fuentes heredadas o controladas.
- Validacion de periodos contractuales existentes: cada tramo debe quedar
  dentro de la vigencia del contrato, iniciar el dia 1, cerrar el ultimo dia
  del mes y respetar numeracion cronologica antes de calcular cobranza.
- Renovaciones de contratos con tramos: la base por defecto debe ser la del
  ultimo tramo vigente. Si una renovacion cambia monto o moneda, el periodo
  debe conservar referencia no sensible y motivo trazable de la politica
  documentada que autoriza la diferencia; API y auditor Etapa 1 bloquean
  renovaciones heredadas sin esa traza o con motivo sensible, y
  API/snapshot/admin/backoffice exponen refs/motivos heredados solo mediante
  version redactada.
- Renovacion automatica operacional: el endpoint de contrato crea un nuevo
  `PeriodoContractual` de origen `renovacion_automatica`, extiende
  `fecha_fin_vigente`, usa por defecto la base del ultimo tramo, bloquea la
  operacion si existe `AvisoTermino` registrado y deja evento auditable
  dedicado con actor trazable. `PeriodoContractual.full_clean()` bloquea
  nuevas escrituras con origen `renovacion_automatica` sin ese evento o sin
  actor, y la API de contratos no acepta ese origen en payloads anidados; el
  auditor Etapa 1 marca como defectuosas renovaciones automaticas heredadas sin
  ese evento completo.
- Validacion de garantias: montos/estado coherentes, fechas de recepcion y
  cierre consistentes, y saldos recibidos, devueltos o aplicados conciliados
  contra `HistorialGarantia`, incluyendo que devoluciones, retenciones o
  aplicaciones apunten al deposito origen, no superen ese deposito y conserven
  cronologia valida; las justificaciones de movimientos no deben contener
  referencias sensibles y se exponen redactadas si son heredadas. Si una garantia fue recibida parcialmente y
  sigue abierta, debe tener aceptacion formal trazable no sensible o quedar
  marcada como incompleta. Si una garantia recibida excede lo pactado, el
  exceso debe quedar clasificado, devuelto, regularizado o bloqueado con
  referencia no sensible y motivo auditable no sensible; API, snapshot y admin
  exponen refs/motivos heredados sensibles solo mediante version redactada, y
  snapshots sin esa resolucion son defectuosos.
- Entrega de llaves: un contrato con `fecha_entrega` operativa debe tener
  garantia cubierta o autorizacion auditada con referencia no sensible y motivo
  trazable. `Contrato.full_clean()` y la API bloquean nuevas escrituras y
  actualizaciones de entrega sin garantia suficiente ni autorizacion; el
  auditor Etapa 1 mantiene deteccion de snapshots heredados, y admin/backoffice
  expone refs/motivos heredados solo mediante version redactada.
- Validacion de ajustes contractuales existentes: contrato, moneda, rango de
  meses normalizado al primer dia del mes dentro de la vigencia contractual y
  justificacion no sensible deben ser coherentes antes de usarlos en cobranza;
  ajustes CLP activos no pueden dejar ningun mes contractual bajo el minimo
  operativo de CLP 1.000.
  API, snapshot y admin/backoffice exponen justificaciones heredadas solo
  mediante version redactada, y el auditor Etapa 1 marca ajustes heredados con
  justificacion sensible.
- Validacion de avisos de termino existentes: la fecha efectiva debe quedar
  dentro del rango del contrato asociado.
- Transiciones de estado contractual: `Contrato.full_clean()` y la API
  impiden regresiones directas como `vigente` -> `pendiente_activacion` y
  reaperturas de estados terminales como `finalizado` o `cancelado`. Los
  cambios deben avanzar por el ciclo operativo permitido y conservar la
  auditoria de cambio de estado con estado anterior y nuevo trazables.
- Cancelacion contractual: un contrato solo puede quedar `cancelado` si no
  conserva efectos irreversibles operativos o economicos, como pagos
  mensuales generados, garantia recibida/devuelta/aplicada o con historial,
  entrega de llaves registrada o aviso de termino registrado. `Contrato.full_clean()`,
  la API y el auditor Etapa 1 bloquean nuevas escrituras o snapshots heredados
  que intenten cancelar contratos con esos efectos.
- Avisos de termino fuera de plazo: se registran sin inventar fechas, se
  comparan contra `AvisoTermino.registrado_at` como timestamp real de registro
  hasta las `23:59:59` del ultimo dia permitido y se reportan como advertencia
  operativa. API, snapshot, admin/backoffice exponen ese timestamp como
  lectura; el auditor Etapa 1 bloquea avisos registrados heredados que no lo
  conserven.
- Terminacion anticipada con ultimo mes parcial: solo se permite si el
  contrato conserva una referencia no sensible a regla o decision de prorrata,
  un motivo trazable y un evento auditable dedicado con actor y metadata
  alineada a referencia, motivo y fecha fin vigente. `Contrato.full_clean()` y
  la API bloquean nuevas escrituras sin esa auditoria completa o con motivo
  sensible, y el auditor Etapa 1 bloquea snapshots heredados sin esa decision,
  sin auditoria alineada o con motivo sensible; API/snapshot/admin/backoffice
  exponen refs/motivos heredados solo mediante version redactada.
- Validacion de pagos y distribuciones existentes en el snapshot: si existen,
  deben cuadrar devengo, conciliacion, porcentaje y entidad facturadora.
- Validacion de que pagos mensuales existentes queden dentro de la vigencia
  del contrato y del periodo contractual referenciado, tengan vencimiento
  alineado al mes operativo y al dia de pago contractual, y conserven
  `CodigoConciliacionEfectivo` en rango operativo `001-999` y alineado con la
  propiedad principal del contrato.
- Validacion de que pagos mensuales existentes en estado pagado efectivo tengan
  monto pagado mayor que cero y fecha trazable de deposito, WebPay o deteccion.
- Contratos retroactivos registrados despues del dia 5 del mes operativo
  generan alerta de posible notificacion manual, y Cobranza bloquea la
  reconstruccion automatica de cobros vencidos antes del registro operativo.
  El auditor Etapa 1 reporta la alerta como advertencia y marca como defecto
  pagos existentes que reconstruyan esos cobros pasados. El backoffice de
  Contratos permite informar `fecha_registro_operativo`, muestra esa fecha en
  la tabla y expone el detalle de la alerta retroactiva devuelta por la API.
- Si un contrato futuro coexiste con `AvisoTermino` y una renovacion
  contractual ya ejecutada, el aviso debe conservar resolucion guiada con
  referencia no sensible y motivo trazable. `Contrato.full_clean()`, la API y
  el auditor Etapa 1 bloquean contratos futuros sin AvisoTermino registrado,
  terminacion anticipada ejecutada o resolucion guiada cuando hay conflicto de
  renovacion, o con motivo de resolucion sensible, sin cancelar ni reescribir
  efectos producidos; la causal del aviso y sus refs/motivos deben ser no
  sensibles, y API/snapshot/admin/backoffice exponen causales, refs o motivos
  heredados sensibles solo mediante version redactada. La tabla de avisos del
  backoffice muestra el detalle redactado de registro fuera de plazo y de la
  resolucion guiada de conflicto de renovacion.
- Cambio de arrendatario: el flujo operacional guiado crea `AvisoTermino`
  registrado y contrato futuro con nuevo arrendatario en una transaccion,
  conserva el contrato/deuda historica sin reescribir identidad, copia las
  propiedades contractuales, inicia un periodo de origen `cambio_arrendatario`
  y registra auditoria dedicada con actor trazable. `Contrato.full_clean()` y
  la API bloquean la escritura directa de contratos futuros con arrendatario
  distinto al vigente si no provienen del flujo guiado o no conservan el evento
  auditable exacto con actor. El auditor Etapa 1 marca como defectuosos
  contratos futuros heredados con arrendatario distinto al vigente si no existe
  el evento auditable completo que vincula contrato anterior, aviso y contrato
  nuevo.
- Validacion de respaldo UF para pagos existentes: si el pago mensual depende
  de periodo o ajuste en UF, debe conservar `moneda_calculo`, fecha, valor y
  fuente UF usados. La fecha UF debe coincidir con `fecha_vencimiento` y debe
  existir `ValorUFDiario` canonico para esa fecha exacta. Si el valor UF fue
  cargado manualmente, debe conservar `evidencia_ref`, `motivo_carga` y
  `responsable_ref` no sensibles.
- Verificacion segura sin fuente autorizada:

```powershell
cd "D:/Proyectos/LeaseManager"
.\scripts\run-stage1-local-readiness.ps1
```

La verificacion local diagnostica preparacion segura y debe quedar
`implementado_sin_evidencia`; no reemplaza el gate evidencial.

- Auditor reproducible de matriz, solo cuando exista autorizacion explicita
  actual para una fuente `snapshot_controlado` o `real_autorizado`:

```powershell
cd "D:/Proyectos/LeaseManager"
$env:DATABASE_URL="<snapshot-controlado-o-db-real-autorizada>"
.\scripts\run-stage1-snapshot-gate.ps1 `
  -SourceKind snapshot_controlado `
  -SourceLabel "<etiqueta-no-sensible>" `
  -AuthorizationRef "<autorizacion-no-sensible>" `
  -ResponsibleRef "<responsable-no-sensible>" `
  -RunMigrations
```

## Salida

La etapa no cierra si no existe evidencia de datos reales/controlados. Codigo
preparado sin esa evidencia queda `implementado_sin_evidencia`.

El bloqueo por falta de fuente autorizada no forma parte de la arquitectura del
producto: solo impide declarar cierre de Etapa 1. Si `BLK-002` ya esta
registrado y no hay autorizacion nueva, no se debe repetir la misma solicitud
en bucle; corresponde avanzar en preparacion segura o dejar una unica pregunta
concreta.

El release gate deterministico ejecuta esta verificacion local dentro de
`scripts/run-acceptance-workflows.ps1` para proteger la regla anti-bucle: sin
fuente autorizada, la ruta local queda `implementado_sin_evidencia`, nunca se
presenta como `snapshot_controlado` y no cierra la etapa. El estado
`bloqueado_dato_real` queda reservado para el gate evidencial contra
`snapshot_controlado` o `real_autorizado`.

Procedimiento operativo: `docs/product/STAGE1_SNAPSHOT_INTAKE_MAYO_2026.md`.
