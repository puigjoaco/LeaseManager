# Etapa 3 - Banco y conciliacion

## Objetivo

Consolidar movimientos bancarios, conciliacion, ingresos desconocidos y saldo
sistema igual a saldo banco.

## Alcance

- Proveedores bancarios.
- Movimientos.
- Reglas de matching.
- Ingresos desconocidos.
- Conciliacion y auditoria.

## Gate

- Banco real o snapshot autorizado con `SourceLabel` y `AuthorizationRef` no
  sensibles.
- Modo no productivo por defecto.
- Conexion bancaria operativa/primaria solo con `credencial_ref`,
  `evidencia_gate_ref`, `prueba_conectividad_ref` y prueba de movimientos o
  saldos segun capacidad marcada, todas como referencias no sensibles.
- Movimiento importado por `provider_sync` solo contra conexion activa,
  primaria de movimientos, readiness trazable y `transaction_id_banco` no
  sensible y no duplicado dentro de la misma conexion por modelo y constraint
  DB; toda `referencia` bancaria de movimiento debe ser no sensible, y la
  carga manual controlada exige `evidencia_importacion_ref` no sensible.
- Movimientos conciliados exactos existentes deben conservar coherencia con su
  target: abonos apuntan a pago mensual pagado o codigo residual pagado de la
  misma cuenta recaudadora; el pago mensual target debe pertenecer al mismo
  periodo economico del movimiento bancario; movimientos no conciliados no
  conservan target.
- Abonos parciales o complementarios conciliados a un `PagoMensual` solo son
  validos con resolucion manual auditada de ingreso desconocido; readiness
  bloquea snapshots donde el movimiento parcial quedo como match exacto sin
  esa traza.
- `audit_stage3_conciliacion_readiness` consolida readiness local de
  conexiones, movimientos, ingresos desconocidos, senales de saldo y
  referencias finales sin conectar bancos ni leer secretos; tambien detecta
  refs sensibles en conexiones bancarias y movimientos existentes.
- Ingresos desconocidos existentes deben coincidir con el movimiento bancario
  que los origina: cuenta recaudadora, monto, fecha, descripcion, tipo abono y
  estado de conciliacion deben ser coherentes; la readiness debe bloquear
  snapshots que conserven discrepancias.
- Ingresos desconocidos resueltos manualmente requieren pago mensual target,
  contrato, periodo economico canonico `YYYY-MM` alineado al mes/anio del
  `PagoMensual`, criterio aplicado, `evidencia_regularizacion_ref` no sensible
  y `rationale`/motivo auditable; la API y el servicio no permiten nuevos
  cierres sin ese contexto, y la readiness bloquea resoluciones heredadas
  resueltas sin motivo, sin contexto, con periodo/target inconsistente o con
  evidencia sensible.
- Cargos bancarios resueltos manualmente requieren `CategoriaMovimiento`,
  entidad afectada, periodo economico canonico `YYYY-MM`, criterio de reparto,
  `evidencia_clasificacion_ref` no sensible y motivo auditable; la API y el
  servicio no permiten nuevos cierres sin ese contexto, y la readiness bloquea
  resoluciones heredadas resueltas sin ese contexto, con periodo/target
  inconsistente o con evidencia sensible.
- Transferencias internas/intercuenta se registran como par cargo/abono en
  `TransferenciaIntercuenta`, con cuenta origen/destino, owner origen/destino,
  periodo economico canonico `YYYY-MM`, criterio de conciliacion, evidencia no
  sensible, responsable y motivo auditable; la API y el servicio no permiten
  resolver una transferencia si los movimientos no son de cuentas distintas,
  no tienen monto opuesto equivalente o conservan targets de pago/codigo
  residual, y la readiness bloquea pares heredados invalidos o refs sensibles.
- Resoluciones manuales abiertas que quedan obsoletas por match exacto o por
  otra resolucion manual no se marcan como resueltas manualmente: se cierran
  como `superseded` con motivo, metadata de origen/target y evento de
  auditoria; la readiness bloquea supersesiones sin traza suficiente.
- Las respuestas API y snapshot de Conciliacion redactan refs bancarias
  sensibles ya persistidas, incluida `referencia` de movimientos, antes de
  exponerlas al backoffice.
- `audit_stage3_conciliacion_readiness` solo puede cerrar con `--source-kind`
  `snapshot_controlado` o `real_autorizado`; `local`, `fixture` y `demo`
  diagnostican brechas pero no habilitan cierre de Etapa 3.
- `scripts/run-stage3-readiness-gate.ps1` normaliza la ejecucion del gate. En
  modo local crea SQLite bajo `local-evidence/`, corre migraciones y debe
  quedar `classification=parcial`, `ready_for_stage3_conciliacion=false` y
  issue `stage3.source_kind_not_authorized`.
- Para cierre con fuente autorizada, el wrapper exige `-SourceKind
  snapshot_controlado` o `real_autorizado`, `-SourceLabel`,
  `-AuthorizationRef`, `-Stage2EvidenceRef`, `-BankProofRef`,
  `-BalanceSquareRef`, `-ResponsibleRef` y `-RequireReady`.
- Cuando hay saldos reportados en movimientos de una misma conexion, el
  auditor valida continuidad local: cada saldo posterior debe continuar desde
  el saldo reportado previo aplicando abonos y cargos intermedios.
- La cuadratura sistema/banco se registra por cuenta recaudadora y periodo en
  `CuadraturaBancaria`, con saldo sistema, saldo banco, diferencia calculada,
  fecha de cuadratura alineada al periodo economico, evidencia no sensible y
  responsable no sensible.
- Las diferencias banco/sistema quedan registradas con motivo auditable, pero
  no habilitan cierre: readiness bloquea cuadraturas faltantes, invalidas, con
  referencias sensibles, con periodo/fecha desalineados, con diferencia
  distinta de cero o sin estado `cuadrada`.
- Saldo sistema igual a saldo banco antes de habilitar cierre.

## Salida

Conciliacion cerrada produce hechos confiables para contabilidad. Sin eso,
Contabilidad no puede cerrar.

## Ejecucion local segura

```powershell
cd "D:/Proyectos/LeaseManager"
.\scripts\run-stage3-readiness-gate.ps1
```
