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
| Frente activo | Ninguno. |
| Fuente exacta | `backend/operacion/models.py`; `backend/core/stage1_matrix_audit.py`; `backend/operacion/tests.py`; `backend/core/tests_stage1_matrix_audit.py`; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`; `docs/product/EVIDENCE_REGISTER_MAYO_2026.md`. |
| Brecha activa | Ninguna abierta en este cursor. |
| Motivo de prioridad | El PRD exige una sola cuenta recaudadora vigente para el mandato aplicable; Operacion ya tiene `vigencia_desde`/`vigencia_hasta`, por lo que el cierre local debe distinguir planificacion futura valida de doble mandato vigente en la misma fecha. |
| Worktree | Ninguno. |
| Rama | Ninguna. |
| Estado | Paquete cerrado e integrado en `main`. |
| Gate esperado | Etapa 1 debe seguir como diagnostico parcial/no evidencial; este paquete endurece preparacion local y no cierra sin fuente `snapshot_controlado` o `real_autorizado`. |
| Estado al cerrar paquete | PR #278 `Guard Stage 1 mandate validity windows`; commit de paquete `99c6b22`; merge commit `550d9f1`; CI GitHub `acceptance` OK; worktree tactico eliminado. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado` sigue siendo condicion de cierre real de Etapa 1, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Desde `main` limpio, elegir el siguiente paquete seguro por trazabilidad y abrir un nuevo worktree `codex/...` solo si el cambio no es trivial. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
