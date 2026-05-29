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
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna registrada en curso. |
| Motivo de prioridad | Tomar el siguiente frente seguro desde trazabilidad y stage cards cuando se abra un nuevo paquete. |
| Worktree | N/A. |
| Rama | `main`. |
| Estado | Sin paquete tactico abierto. Ultimo paquete cerrado: admin de senales runtime operacionales queda sin alta, edicion ni borrado manual, conservando mutaciones bajo comando validado, dominio y auditoria. |
| Gate esperado | El proximo paquete debe definir su gate proporcional antes de implementar. |
| Estado al cerrar paquete | Etapa 7/Operacion productiva permanece parcial sin cierre falso; paquete validado con focal Core admin, suite Core/observabilidad/permisos, `manage.py check`, migraciones dry-run, gate local Etapa 7, frontend build/lint, acceptance local, higiene repo y `git diff --check`. |
| Bloqueos relacionados | Sin bloqueo externo nuevo; cierre real de Etapa 7 sigue dependiendo de fuente autorizada y evidencia externa/controlada. |
| Politica de reanudacion | Si no existe worktree tactico sucio, abrir el siguiente paquete pequeno, seguro y verificable segun trazabilidad, stage cards y orden de construccion. |
| Siguiente accion | Diagnosticar el siguiente frente seguro desde el estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
