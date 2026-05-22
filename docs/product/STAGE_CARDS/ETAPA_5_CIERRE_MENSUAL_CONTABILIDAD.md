# Etapa 5 - Cierre mensual y contabilidad

## Objetivo

Cerrar ledger mensual, asientos, liquidaciones, PPM, F29/F21 y reportes
contables desde hechos conciliados.

## Alcance

- Eventos contables.
- Reglas y matriz contable.
- Asientos y movimientos.
- Cierre mensual.
- Liquidaciones y reportes.

## Gate

- Conciliacion cerrada.
- Preparar o aprobar cierre mensual bloquea si existen movimientos bancarios
  del periodo para cuentas de la empresa en `pendiente`,
  `ingreso_desconocido` o `manual_requerida`.
- Reglas contables vigentes.
- Asientos balanceados.
- Movimientos de asiento obligatorios, con sumas debe/haber iguales a los
  totales del asiento y cuentas contables de la misma empresa del evento.
- `audit_stage5_contabilidad_readiness` consolida configuracion fiscal,
  reglas/matriz, eventos, asientos, integridad de movimientos, snapshots,
  cierres mensuales y conciliacion del periodo sin presentar impuestos ni
  conectar servicios externos.
- `audit_stage5_contabilidad_readiness` solo puede cerrar con `--source-kind`
  `snapshot_controlado` o `real_autorizado`; `local`, `fixture` y `demo`
  diagnostican brechas pero no habilitan cierre de Etapa 5.
- Las fuentes autorizadas deben declarar `SourceLabel` y `AuthorizationRef` no
  sensibles.
- `scripts/run-stage5-readiness-gate.ps1` normaliza la ejecucion del gate. En
  modo local crea SQLite bajo `local-evidence/`, corre migraciones y debe
  quedar `classification=parcial`, `ready_for_stage5_contabilidad=false` y
  issue `stage5.source_kind_not_authorized`.
- Para cierre con fuente autorizada, el wrapper exige `-SourceKind
  snapshot_controlado` o `real_autorizado`, `-SourceLabel`,
  `-AuthorizationRef`, `-Stage3EvidenceRef`, `-LedgerProofRef`,
  `-ReportsProofRef`, `-ResponsibleRef` y `-RequireReady`.
- Reportes con origen trazable.
- Diferencias registradas o corregidas.

## Salida

Un mes se considera cerrado solo si banco, ledger, asientos y reportes cuadran.

## Ejecucion local segura

```powershell
cd "D:/Proyectos/LeaseManager"
.\scripts\run-stage5-readiness-gate.ps1
```
