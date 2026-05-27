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
| Frente activo | Sin paquete activo. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Pendiente de seleccionar segun trazabilidad vigente y estado real del repo. |
| Motivo de prioridad | El paquete anterior quedo cerrado; el siguiente frente debe elegirse en la proxima apertura operativa. |
| Worktree | N/A. |
| Rama | `main`. |
| Estado | Sin paquete activo; ultimo paquete integrado en PR #397 (`Validate compliance policy bootstrap`). |
| Gate esperado | Definir al abrir el siguiente paquete. |
| Estado al cerrar paquete | PR #397 integrado en `main` con merge `d3d69ab`; el bootstrap demo de politicas de retencion valida todo el set canonico antes de persistir y evita escrituras parciales con parametros invalidos o sensibles. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no hay worktree tactico sucio, elegir el siguiente frente util y seguro desde trazabilidad vigente. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; seleccionar el siguiente paquete pequeno, verificable y cerrable. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
