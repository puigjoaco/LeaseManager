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
| Frente activo | Ninguno; ultimo paquete cerrado: Etapa 0 - Compliance datos sensibles: auditoria de acceso denegado a exportaciones. |
| Fuente exacta | PR #211 `Audit denied compliance export access`; commit `daf6a64`; merge `e7d0dac`; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `Compliance datos sensibles`; `backend/compliance`; `backend/core/compliance_data_readiness.py`; `scripts/run-compliance-data-readiness-gate.ps1`. |
| Brecha activa | Cerrada localmente: los accesos fallidos a contenido de exportaciones revocadas o expiradas registran `compliance.exportacion_sensible.access_denied` sin exponer payloads. |
| Motivo de prioridad | Paquete integrado; no hay worktree tactico abierto para este frente. |
| Worktree | Ninguno. |
| Rama | `main` sincronizada tras merge `e7d0dac`. |
| Estado | PR #211 integrado con CI `acceptance` verde; worktree `D:/Proyectos/LeaseManager-compliance-denied-export-audit` eliminado y rama tactica local/remota eliminada. |
| Gate esperado | Compliance datos sensibles sigue en `classification=parcial`, `ready_for_compliance_data=false` con fuente local; no cierra Compliance sin fuente autorizada y refs finales. |
| Estado al cerrar paquete | `implementado_sin_evidencia`; avance local preparado, sin cierre real de Compliance. |
| Bloqueos relacionados | Falta fuente `snapshot_controlado` o `real_autorizado`, politica aprobada, responsables, controles, evidencia archivada y validacion legal-operativa no sensibles para cierre real de `Compliance.DatosPersonalesChile2026`; no bloquea preparacion local. |
| Politica de reanudacion | Si `main` esta limpio y no hay worktrees tacticos sucios, seleccionar el siguiente frente util, seguro y trazable desde la matriz/PRD/arquitectura. |
| Siguiente accion | Diagnosticar el siguiente paquete local cerrable y abrir worktree `codex/...` solo si el cambio no es trivial. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
