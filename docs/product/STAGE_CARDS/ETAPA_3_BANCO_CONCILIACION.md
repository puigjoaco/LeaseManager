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
  sensible; la carga manual controlada exige `evidencia_importacion_ref` no
  sensible.
- `audit_stage3_conciliacion_readiness` consolida readiness local de
  conexiones, movimientos, ingresos desconocidos, senales de saldo y
  referencias finales sin conectar bancos ni leer secretos; tambien detecta
  refs sensibles en conexiones bancarias y movimientos existentes.
- Ingresos desconocidos existentes deben coincidir con el movimiento bancario
  que los origina: cuenta recaudadora, monto, fecha, descripcion, tipo abono y
  estado de conciliacion deben ser coherentes; la readiness debe bloquear
  snapshots que conserven discrepancias.
- Las respuestas API y snapshot de Conciliacion redactan refs bancarias
  sensibles ya persistidas antes de exponerlas al backoffice.
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
- Diferencias registradas.
- Saldo sistema igual a saldo banco antes de habilitar cierre.

## Salida

Conciliacion cerrada produce hechos confiables para contabilidad. Sin eso,
Contabilidad no puede cerrar.

## Ejecucion local segura

```powershell
cd "D:/Proyectos/LeaseManager"
.\scripts\run-stage3-readiness-gate.ps1
```
