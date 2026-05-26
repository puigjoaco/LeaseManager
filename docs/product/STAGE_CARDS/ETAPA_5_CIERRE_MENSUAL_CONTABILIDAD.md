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
- La reapertura posterior al cierre debe aplicar un efecto contable trazable:
  `reverso` o `asiento_complementario`, segun la politica activa. El efecto
  exige motivo, efecto esperado, monto, evidencia no sensible y genera un
  `EventoContable` contabilizado en el periodo posterior; la reapertura no se
  guarda si falta regla/matriz activa para ese efecto.
- `audit_stage5_contabilidad_readiness` detecta cierres reabiertos sin efecto
  de reapertura, efectos sin evento contable contabilizado o referencias
  sensibles en motivo/evidencia del efecto.
- Movimientos de asiento obligatorios, con sumas debe/haber iguales a los
  totales del asiento y cuentas contables de la misma empresa del evento.
  `MovimientoAsiento.clean()` bloquea nuevas escrituras con cuentas de otra
  empresa y readiness conserva la deteccion de snapshots heredados.
- Transferencias intercuenta conciliadas que involucren cuentas recaudadoras
  con owner empresa deben generar eventos contables idempotentes de salida y/o
  entrada (`TransferenciaIntercuentaSalida`,
  `TransferenciaIntercuentaEntrada`) antes de considerar el ledger preparado
  para cierre.
- Eventos, movimientos, obligaciones, libros, balances y cierres no pueden
  persistir nuevas URLs, tokens, credenciales, correos ni referencias sensibles
  en payloads, `storage_ref` o `centro_resultado_ref`.
- APIs de contabilidad y reporting de libros redactan payloads y referencias
  sensibles heredadas antes de exponerlas al backoffice.
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
