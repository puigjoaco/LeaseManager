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
| Brecha activa | Ninguna abierta. Ultimo paquete cerrado: PR #389 `Redact Conciliacion admin refs`, merge `329260d`. |
| Motivo de prioridad | No aplica mientras no exista paquete abierto; el siguiente frente se selecciona desde el estado real del repo y la trazabilidad vigente. |
| Worktree | N/A. |
| Rama | N/A. |
| Estado | Sin paquete abierto; `main` quedo actualizado tras PR #389. |
| Gate esperado | N/A hasta abrir el siguiente paquete. |
| Estado al cerrar paquete | PR #389 integrado en `main`; CI acceptance remoto paso y el worktree tactico fue eliminado. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no hay worktree tactico sucio, seleccionar el siguiente paquete pequeno, seguro y trazable desde el estado real del repo. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; si no hay paquete abierto, diagnosticar el siguiente frente seguro por orden y trazabilidad antes de crear un worktree `codex/...`. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
