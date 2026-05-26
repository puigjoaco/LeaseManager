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
| Frente activo | Ninguno abierto en `main`; ultimo paquete cerrado: Etapa 7 - referencias sensibles en evidencia de release gate. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna pendiente en cursor. El ultimo paquete hizo que `run-stage7-readiness-gate.ps1` clasifique refs sensibles de restore, smoke publico y aceptacion final con codigos especificos sin exponer valores. |
| Motivo de prioridad | El paquete cerro diagnostico de evidencia sensible en el release gate para no confundir referencias sensibles con faltantes genericos. |
| Worktree | Ninguno tactico activo. |
| Rama | `main`. |
| Estado | Paquete validado, integrado y worktree tactico eliminado. |
| Gate esperado | Si `main` esta limpio, elegir el siguiente frente seguro por trazabilidad y orden de construccion. No cerrar Operacion productiva sin fuentes/evidencias autorizadas. |
| Estado al cerrar paquete | PR #349 mergeado en `main` como `4c92f88`; CI acceptance remoto OK; validacion local OK con parser PS, focal gate Etapa 7, acceptance 907 tests, frontend build, higiene y `git diff --check`. |
| Bloqueos relacionados | Restore autorizado, smoke publico autorizado, Reporting autorizado, observabilidad runtime autorizada y aceptacion final siguen como condicion de cierre externo. |
| Politica de reanudacion | Confirmar `git status --short --branch` y `git worktree list`; si `main` esta limpio, seleccionar el siguiente frente seguro desde trazabilidad. |
| Siguiente accion | Seleccionar nuevo paquete pequeno, seguro y verificable segun cursor, PRD/stage cards, trazabilidad y bloqueos vigentes. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
