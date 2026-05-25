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
| Fuente exacta | `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`; `docs/product/EVIDENCE_REGISTER_MAYO_2026.md`; `docs/product/STAGE_CARDS/`; `01_Set_Vigente/PRD_CANONICO.md`; estado real de `main`. |
| Brecha activa | Ninguna abierta en este cursor. |
| Motivo de prioridad | PR #280 cerro el paquete anterior; el siguiente frente debe elegirse desde trazabilidad y estado real del repo. |
| Worktree | Ninguno. |
| Rama | Ninguna. |
| Estado | Paquete cerrado e integrado en `main`. |
| Gate esperado | Los gates de etapa siguen segun stage cards y matriz vigente; no declarar cierre sin evidencia suficiente. |
| Estado al cerrar paquete | PR #280 `Warn on late Stage 1 termination notices` integrado con commit `220da1e` y merge `407ab7d`; CI acceptance OK; worktree tactico y rama local/remota eliminados. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado` sigue siendo condicion de cierre real de Etapa 1, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Desde `main` limpio, identificar el siguiente paquete seguro por trazabilidad, abrir worktree `codex/...` si el cambio no es trivial y cerrar con validacion proporcional, PR, CI, merge y limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
