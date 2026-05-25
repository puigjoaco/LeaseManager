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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 1 - Patrimonio permite planificar representaciones de comunidad futuras no solapadas. |
| Fuente exacta | PR #276; commit `c17e1b7`; merge `f91d3e9`. `backend/patrimonio/models.py`; `backend/patrimonio/migrations/0005_remove_representacioncomunidad_unique_active.py`; `backend/core/stage1_matrix_audit.py`; `backend/patrimonio/tests.py`; `backend/core/tests_stage1_matrix_audit.py`; `docs/product/STAGE_CARDS/ETAPA_1_DATOS_REALES.md`; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`; `docs/product/EVIDENCE_REGISTER_MAYO_2026.md`. |
| Brecha activa | Ninguna abierta en cursor. La brecha donde una unicidad global de filas activas impedia planificar una representacion futura no solapada quedo corregida, manteniendo bloqueo de ventanas efectivas solapadas por dominio y auditor. |
| Motivo de prioridad | Paquete cerrado porque Patrimonio debe permitir planificacion operativa de representaciones sin perder la garantia de una sola representacion vigente por fecha. No requirio `.env`, secretos, DB historica, datos reales, snapshots, backfills, deploys ni integraciones externas. |
| Worktree | Ninguno tactico abierto. |
| Rama | Ninguna tactica abierta. |
| Estado | PR #276 mergeado, CI `acceptance` en verde, main sincronizado y worktree tactico de producto eliminado. |
| Gate esperado | Etapa 1 sigue como diagnostico parcial/no evidencial; no cierra sin fuente `snapshot_controlado` o `real_autorizado`. |
| Estado al cerrar paquete | Cerrado en main con merge `f91d3e9`; siguiente frente debe elegirse por trazabilidad desde estado limpio. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado` sigue siendo condicion de cierre real de Etapa 1, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
