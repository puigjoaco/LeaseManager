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
| Brecha activa | Ninguna abierta. |
| Motivo de prioridad | Pendiente seleccionar el siguiente frente util desde trazabilidad, stage cards, PRD y estado real del repo. |
| Worktree | N/A. |
| Rama | N/A. |
| Estado | Paquete Etapa 1/Cobranza `stage1-guarantee-history-justification-redaction` integrado en PR #447, merge `45b6e58`. |
| Gate esperado | N/A hasta abrir el siguiente paquete. |
| Estado al cerrar paquete | Cerrado con CI remoto acceptance en verde; worktree y rama tactica de implementacion limpiados. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no existe worktree tactico sucio, elegir el siguiente frente seguro desde trazabilidad y abrir un nuevo paquete pequeno y verificable. |
| Siguiente accion | Diagnosticar el estado real y seleccionar el proximo paquete seguro desde PRD, stage cards, trazabilidad y evidencia. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
