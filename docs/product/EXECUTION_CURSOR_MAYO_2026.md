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
| Fuente exacta | `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`; `docs/product/EVIDENCE_REGISTER_MAYO_2026.md`; `docs/product/STAGE_CARDS/`; `01_Set_Vigente/PRD_CANONICO.md`. |
| Brecha activa | Ninguna registrada en curso. |
| Motivo de prioridad | El paquete de politica de base de renovacion con tramos quedo cerrado en PR #284. |
| Worktree | Solo root principal esperado: `D:/Proyectos/LeaseManager`. |
| Rama | `main`. |
| Estado | Sin paquete activo; listo para elegir el siguiente frente seguro por trazabilidad. |
| Gate esperado | Los gates externos siguen siendo condiciones de cierre real, no de preparacion local. |
| Estado al cerrar paquete | PR #284 mergeado en `main` con merge `8042ea2`; CI `acceptance` pass; worktree tactico y rama remota eliminados. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado` sigue siendo condicion de cierre real de Etapa 1, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Elegir el siguiente paquete seguro desde trazabilidad/cursor, abrir worktree `codex/...` si no es trivial, validar proporcionalmente y cerrar con PR, CI, merge y limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
