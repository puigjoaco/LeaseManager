# Etapa 5 - Pre-cierre mensual y contabilidad asistida

## Objetivo

Preparar un paquete mensual contable y tributario reproducible desde hechos
conciliados: ledger, asientos, liquidaciones, PPM, F29/F21 y reportes. El core
mecaniza reglas y evidencia; no reemplaza revision responsable cuando una regla
contable o tributaria requiere criterio.

## Alcance

- Eventos contables.
- Reglas y matriz contable.
- Asientos y movimientos.
- Cierre mensual.
- Liquidaciones y reportes.
- Paquete de revision/aprobacion responsable.

## Gate

- Conciliacion cerrada.
- El estado `aprobado` dentro del sistema exige responsable trazado y evidencia;
  no equivale por si solo a presentacion tributaria ni a criterio contable
  externo.
- Preparar o aprobar cierre mensual bloquea si existen movimientos bancarios
  del periodo para cuentas de la empresa en `pendiente`,
  `ingreso_desconocido` o `manual_requerida`.
- Preparar o aprobar cierre mensual exige `CuadraturaBancaria` cuadrada para
  cada cuenta recaudadora de la empresa que tenga movimientos bancarios en el
  periodo; la readiness detecta cierres heredados sin cuadratura o con
  diferencia abierta.
- Reglas contables vigentes.
- Reglas contables activas sin vigencias solapadas para la misma empresa, tipo
  de evento y version de plan; el dominio/API bloquea nuevas ambiguedades y
  readiness clasifica snapshots heredados con
  `stage5.rules_overlapping_vigencia`.
- Un mismo hecho economico no puede generar doble contabilizacion efectiva:
  si ya existe un `EventoContable` contabilizado para la misma empresa, tipo y
  entidad origen, un evento nuevo con otra `idempotency_key` queda en revision
  y readiness bloquea snapshots heredados con duplicados posteados.
- Asientos balanceados.
- Asientos del periodo con `periodo_contable` consistente con
  `fecha_contable`.
- Asientos contabilizados con `hash_integridad` presente y vigente respecto de
  su contenido actual; el cierre y readiness bloquean hashes heredados
  desactualizados.
- Un cierre mensual aprobado solo se reabre con `PoliticaReversoContable`
  activa para `reapertura_cierre_mensual`, que permita reapertura y exija
  aprobacion.
- Un cierre mensual aprobado debe conservar `LiquidacionMensual` de empresa
  preparada o aprobada para el mismo periodo y cierre contable.
  `approve_monthly_close()` exige esa liquidacion antes de pasar el cierre a
  `aprobado`, y agrega la referencia no sensible de liquidacion, responsable y
  evidencia base al resumen del cierre y al evento auditable de aprobacion. La
  readiness Etapa 5 detecta cierres heredados cuya liquidacion de empresa
  existe para el periodo pero no esta vinculada al cierre aprobado, o cuyo
  resumen de cierre perdio el contexto de responsable/evidencia de aprobacion.
- Si la liquidacion mensual declara comision de administracion aplicable, debe
  existir una `LineaLiquidacionMensual` explicita de
  `comision_administracion` con beneficiario, monto positivo y evidencia no
  sensible.
- Si la liquidacion mensual preparada o aprobada conserva
  `saldo_final_clp` distinto de cero, debe existir una
  `LineaLiquidacionMensual` explicita de `saldo_final_explicado` cuyo total
  cuadre con ese saldo final y tenga evidencia no sensible.
- Las lineas economicas de liquidaciones preparadas o aprobadas deben trazar a
  `EventoContable`, y las explicaciones/evidencias de saldo final no pueden
  contener URLs, correos, tokens, credenciales ni referencias sensibles.
- La reapertura posterior al cierre debe aplicar un efecto contable trazable:
  `reverso` o `asiento_complementario`, segun la politica activa. El efecto
  exige motivo, efecto esperado, monto, evidencia no sensible y genera un
  `EventoContable` contabilizado en el periodo posterior; la reapertura no se
  guarda si falta regla/matriz activa para ese efecto. La API de reapertura
  registra `reopened` y `state_changed` en la misma transaccion con transicion
  `aprobado` -> `reabierto` y contexto redactable del efecto.
- `audit_stage5_contabilidad_readiness` detecta cierres reabiertos sin efecto
  de reapertura, sin auditoria `state_changed` trazable, efectos sin evento
  contable contabilizado o referencias sensibles en motivo/evidencia del
  efecto.
- Movimientos de asiento obligatorios, con sumas debe/haber iguales a los
  totales del asiento y cuentas contables de la misma empresa del evento.
  `MovimientoAsiento.clean()` bloquea nuevas escrituras con cuentas de otra
  empresa y readiness conserva la deteccion de snapshots heredados.
- Transferencias intercuenta conciliadas que involucren cuentas recaudadoras
  con owner empresa deben generar eventos contables idempotentes de salida y/o
  entrada (`TransferenciaIntercuentaSalida`,
  `TransferenciaIntercuentaEntrada`) alineados con empresa, fecha, moneda y
  monto del movimiento bancario correspondiente antes de considerar el ledger
  preparado para cierre.
- Eventos, movimientos, obligaciones, libros, balances y cierres no pueden
  persistir nuevas URLs, tokens, credenciales, correos ni referencias sensibles
  en payloads, `storage_ref` o `centro_resultado_ref`.
- Referencias y textos operativos de Contabilidad se normalizan antes de
  `full_clean()` y `save()`: `centro_resultado_ref`, `storage_ref`, referencias
  de liquidacion, evidencias de lineas y motivos/evidencias de reapertura quedan
  canonicos antes de validadores de campo, persistencia, snapshot, readiness y
  auditoria.
- APIs de contabilidad y reporting de libros redactan payloads y referencias
  sensibles heredadas antes de exponerlas al backoffice.
- El backoffice de Contabilidad debe exponer `LiquidacionMensual` y
  `LineaLiquidacionMensual` del snapshot de control, permitir registrar
  liquidacion de empresa con responsable/evidencia no sensible, mostrar esas
  referencias antes de aprobar un cierre y cargar la reapertura solo mediante
  formulario con motivo, efecto esperado, monto y evidencia. No debe ofrecer
  acciones ciegas de aprobacion/reapertura que oculten la base responsable del
  cierre.
- Las mutaciones API de Contabilidad deben persistir cambios operativos y
  auditoria de vista en una unica transaccion. Esto cubre altas/ediciones de
  catalogos contables, creacion y reintento de contabilizacion de eventos,
  preparacion, aprobacion y reapertura de cierres mensuales; si falla la
  auditoria, no deben quedar entidades, asientos, obligaciones, snapshots,
  estados de cierre ni efectos de reapertura mutados sin traza.
- Las mutaciones API de Contabilidad que actualizan entidades con estado deben
  persistir `updated` y, cuando corresponda, `state_changed` en la misma
  transaccion. Los eventos `contabilidad.*.state_changed` deben conservar
  metadata minima de transicion con `campo_estado`, `estado_anterior` y
  `estado_nuevo`.
- La creacion y el reintento de contabilizacion de `EventoContable` deben
  registrar `contabilidad.evento_contable.state_changed` cuando
  `post_accounting_event()` cambie `estado_contable`, incluyendo el `asiento_id`
  cuando exista asiento. Si falla esa auditoria, no deben persistir evento,
  asiento ni cambio de estado sin traza.
- `audit_stage5_contabilidad_readiness` bloquea eventos `state_changed`
  heredados de Contabilidad que no conserven esa metadata minima de
  transicion.
- El admin Django de Contabilidad no expone refs/payloads crudos de eventos,
  asientos, movimientos, obligaciones, libros, balances, cierres ni efectos
  de reapertura; muestra versiones redactadas y mantiene cerrada el alta,
  edicion y borrado manual de esos artefactos generados desde backoffice.
- El admin Django de configuracion contable/fiscal deshabilita el borrado
  manual de regimenes, configuraciones fiscales, cuentas, reglas, matriz y
  politicas de reverso; los cambios deben pasar por edicion controlada,
  estados, versionado o flujos auditados.
- `audit_stage5_contabilidad_readiness` consolida configuracion fiscal,
  reglas/matriz, eventos, asientos, integridad de movimientos, snapshots,
  cierres mensuales y conciliacion del periodo sin presentar impuestos ni
  conectar servicios externos.
- `audit_stage5_contabilidad_readiness` bloquea cierre si detecta payloads,
  `storage_ref`, resumenes de snapshot, obligaciones, cierres o movimientos de
  asiento con referencias sensibles heredadas.
- `audit_stage5_contabilidad_readiness` solo puede cerrar con `--source-kind`
  `snapshot_controlado` o `real_autorizado`; `local`, `fixture` y `demo`
  diagnostican brechas pero no habilitan cierre de Etapa 5.
- Las fuentes autorizadas deben declarar `SourceLabel` y `AuthorizationRef` no
  sensibles.
- Si `SourceLabel` o `AuthorizationRef` contienen URL, token, credencial o
  valor sensible, readiness debe clasificar `stage5.source_label_sensitive` o
  `stage5.authorization_ref_sensitive`, exponer solo
  `sections.source_trace_sensitive` y no mezclarlo con refs faltantes.
- Las referencias finales de cierre (`Stage3EvidenceRef`, `LedgerProofRef`,
  `ReportsProofRef` y `ResponsibleRef`) tambien deben ser no sensibles. Si
  contienen URL, token, credencial o valor sensible, readiness debe clasificar
  `stage5.*_ref_sensitive`, exponer `sections.final_evidence_sensitive` y no
  mezclarlas con refs faltantes.
- `scripts/run-stage5-readiness-gate.ps1` normaliza la ejecucion del gate. En
  modo local crea SQLite bajo `local-evidence/`, corre migraciones y debe
  quedar `classification=parcial`, `ready_for_stage5_contabilidad=false` y
  issue `stage5.source_kind_not_authorized`.
- `audit_company_accounting_progress` entrega un diagnostico por empresa y
  ano comercial para convertir el avance contable en un estado objetivo:
  configuracion fiscal, doce cierres mensuales aprobados, balances mensuales
  aprobados/cuadrados, F29 mensuales, proceso anual, balance anual, RLI/CPT,
  dossier y export local. La salida `ready_for_company_accounting_review`
  significa listo para revision responsable, no cierre contable/tributario
  legal. Es un reporte de progreso; no abre gates, no lee fuentes externas y
  no declara cierre de Etapa 5/6.
- Reporting expone el mismo diagnostico en
  `contabilidad/progreso-empresa/`, con scope por empresa, porcentaje, fases,
  faltantes, proximo bloqueo y trazabilidad sin RUT ni secretos. Esta vista
  permite medir una empresa piloto cuando exista fuente permitida, pero no
  reemplaza el gate de cierre ni una revision contable responsable.
- `audit_company_accounting_candidates` y Reporting
  `contabilidad/candidatos-progreso-empresa/` listan empresas y anos con
  senales internas de cierre, balance, F29 y artefactos anuales para escoger
  el primer caso a medir sin leer `.env`, DB historica, fuentes reales ni
  integraciones externas. Es selector de avance, no evidencia de cierre.
- Para cierre con fuente autorizada, el wrapper exige `-SourceKind
  snapshot_controlado` o `real_autorizado`, `-SourceLabel`,
  `-AuthorizationRef`, `-Stage3EvidenceRef`, `-LedgerProofRef`,
  `-ReportsProofRef`, `-ResponsibleRef` y `-RequireReady`.
- Reportes con origen trazable.
- Reporting financiero mensual expone `control_cierre_mensual` como vista de
  control local de cierre contable, movimientos bancarios no resueltos, banco
  cuadrado, obligaciones PPM/F29 y bloqueadores del periodo por empresa.
- Diferencias registradas o corregidas.

## Salida

Un mes se considera preparado para aprobacion solo si banco, ledger, asientos y
reportes cuadran. Se considera cerrado para efectos del producto solo cuando,
ademas, conserva responsable, evidencia y gate aplicable; esa condicion no
habilita por si sola una presentacion tributaria externa.

## Ejecucion local segura

```powershell
cd "D:/Proyectos/LeaseManager"
.\scripts\run-stage5-readiness-gate.ps1
```
