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
| Fuente exacta | Estado real de `main` en `866beae` despues de PR #614, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | Ninguna abierta en cursor. |
| Motivo de prioridad | El paquete Etapa 3 - atomicidad del reintento manual de match exacto fue integrado y validado. |
| Worktree | Ninguno. |
| Rama | Ninguna. |
| Estado | Sin paquete tactico abierto. |
| Gate esperado | Antes de abrir un nuevo paquete, diagnosticar desde `main`, confirmar estado real con `git status --short --branch` y `git worktree list`, y elegir el siguiente frente local seguro segun trazabilidad y orden de construccion. |
| Estado al cerrar paquete | PR #614 mergeado en `866beae`; CI acceptance remoto OK; worktree tactico y rama local/remota eliminados. |
| Bloqueos relacionados | Los cierres evidenciales que dependan de fuentes externas siguen condicionados por autorizacion y evidencia suficiente; no bloquean abrir paquetes locales seguros. |
| Politica de reanudacion | Si no existe worktree tactico abierto, partir desde este cursor y el estado real de `main`; no reabrir paquetes ya integrados. |
| Siguiente accion | Diagnosticar el siguiente frente util y seguro desde `main`, abrir worktree `codex/...` si corresponde y ejecutar el paquete con validacion proporcional. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
