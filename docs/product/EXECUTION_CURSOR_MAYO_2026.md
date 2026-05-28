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
| Frente activo | Ningun paquete tactico abierto. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Pendiente de seleccionar desde trazabilidad, stage cards y orden de construccion. |
| Motivo de prioridad | No aplica mientras no haya paquete abierto. |
| Worktree | `D:/Proyectos/LeaseManager`. |
| Rama | `main`. |
| Estado | PR #503 integrado en `main` (`ec8236c`); cursor listo para seleccionar el siguiente paquete. |
| Gate esperado | Ejecutar el gate proporcional del siguiente frente seleccionado. |
| Estado al cerrar paquete | PR #503 cerro la superficie generica de resoluciones manuales especializadas de Etapa 3 sin banco externo. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Confirmar `git status --short --branch` y `git worktree list`; si no hay worktree tactico sucio, seleccionar el siguiente frente seguro desde trazabilidad y orden de construccion. |
| Siguiente accion | Abrir un nuevo paquete pequeno, trazable y validable segun la proxima brecha real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
