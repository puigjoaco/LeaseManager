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
| Fuente exacta | Estado real de `main` en `bf87cf5` despues de PR #620, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | Sin paquete tactico abierto. |
| Motivo de prioridad | PR #620 cerro la atomicidad de tokens persistentes y auditoria de vista en Auth. |
| Worktree | Solo root principal esperado: `D:/Proyectos/LeaseManager`. |
| Rama | `main`. |
| Estado | Main limpio y listo para diagnosticar el siguiente frente seguro por trazabilidad. |
| Gate esperado | Para el siguiente paquete, definir tests focales, suite impactada, checks, gates locales, frontend si aplica, acceptance local, higiene y CI antes de PR. |
| Estado al cerrar paquete | PR #620 mergeado en `bf87cf5`; CI GitHub acceptance OK; worktree `D:/Proyectos/LeaseManager-auth-token-audit-atomicity` eliminado; rama tactica local/remota eliminada. |
| Bloqueos relacionados | Los cierres evidenciales que dependan de fuentes externas siguen condicionados por autorizacion/fuente controlada y no bloquean trabajo local seguro. |
| Politica de reanudacion | Si no hay worktree tactico abierto, diagnosticar desde `main` limpio y elegir el siguiente frente util por orden de construccion, trazabilidad, stage cards y evidencia vigente. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; luego elegir el siguiente paquete pequeno, local, verificable y cerrable. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
