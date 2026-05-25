# Cursor operativo - mayo 2026

Este archivo fija el frente activo de ejecucion. No reemplaza al PRD, AGENTS,
fuente de verdad, arquitectura, matriz, stage cards, evidencia ni bloqueos. Su
funcion es evitar que una reanudacion convierta contexto auxiliar en tarea
nueva.

## Regla de uso

- Antes de abrir o continuar cambios no triviales, leer este cursor.
- Confirmar el estado real con `git status --short --branch` y
  `git worktree list`.
- Si existe un worktree tactico sucio, se debe terminar, pausar de forma
  explicita en este cursor o descartar con instruccion segura antes de abrir un
  frente distinto.
- Solo el estado real del repo y este cursor definen la siguiente accion
  operativa.
- El contexto auxiliar no autoriza secretos, no abre gates y no crea tareas
  nuevas salvo solicitud textual actual del usuario.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 0 - Compliance verifica integridad payload/hash antes de descargar exportaciones sensibles. |
| Fuente exacta | PR #272; commit `9180dd4`; merge `cc09eca`. `backend/compliance/services.py`; `backend/core/compliance_data_readiness.py`; `backend/compliance/tests.py`; `backend/core/tests_compliance_data_readiness.py`; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`; `docs/product/EVIDENCE_REGISTER_MAYO_2026.md`. |
| Brecha activa | Ninguna abierta en cursor. La brecha donde un payload cifrado manipulado podia descargarse aunque ya no coincidiera con `payload_hash` quedo corregida y validada en PR #272. |
| Motivo de prioridad | Paquete cerrado porque Compliance ya exigia hash canonico, pero faltaba verificar que el contenido descifrado siguiera alineado antes de entregar la exportacion. El cambio niega la descarga, audita `access_denied` y hace que readiness reporte `compliance.export_payload_hash_mismatch` para datos heredados. No requirio `.env`, secretos, DB historica, datos reales, snapshots, backfills, deploys ni integraciones externas. |
| Worktree | Ninguno tactico abierto. |
| Rama | Ninguna tactica abierta. |
| Estado | PR #272 mergeado, CI `acceptance` en verde, main sincronizado y worktree tactico de producto eliminado. |
| Gate esperado | Compliance.DatosPersonalesChile2026 sigue como diagnostico parcial/no evidencial; no cierra sin fuente autorizada, politica aprobada, responsables, controles, evidencia archivada y validacion legal-operativa no sensibles. |
| Estado al cerrar paquete | Cerrado en main con merge `cc09eca`; siguiente frente debe elegirse por trazabilidad desde estado limpio. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado`, `SourceLabel`, `AuthorizationRef`, politica aprobada, responsables, controles, evidencia archivada y validacion legal-operativa siguen siendo condicion de cierre real de Compliance, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
