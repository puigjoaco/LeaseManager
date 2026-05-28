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
| Motivo de prioridad | Paquete `stage5-transfer-event-alignment` cerrado; pendiente seleccionar el siguiente frente util desde trazabilidad, stage cards, PRD y estado real del repo. |
| Worktree | N/A. |
| Rama | N/A. |
| Estado | Paquete Etapa 5/Contabilidad `stage5-transfer-event-alignment` integrado en PR #491, merge `1b6bc17`. |
| Gate esperado | N/A hasta abrir el siguiente paquete. |
| Estado al cerrar paquete | Cerrado con validacion local completa y CI remoto acceptance en verde; worktree tactico y rama remota eliminados. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no existe worktree tactico sucio, seleccionar el siguiente frente seguro desde estado real del repo y documentos rectores. |
| Siguiente accion | Abrir el proximo paquete util, pequeno y verificable segun trazabilidad, stage cards, PRD y estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
