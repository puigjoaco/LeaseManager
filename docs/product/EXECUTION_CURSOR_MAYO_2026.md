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
| Frente activo | Etapa 2 / Canales - identidad autorizada en mensajes salientes. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Mensajes preparados/enviados deben usar una `IdentidadDeEnvio` autorizada para el contrato: override explicito del contrato o asignacion activa del mandato para el mismo canal. |
| Motivo de prioridad | El PRD canonico define que un contrato usa su override explicito de identidad o la asignacion vigente del mandato; Canales no debe preparar/envia mensajes con una identidad activa pero no autorizada para ese contrato. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-message-authorized-identity`. |
| Rama | `codex/stage2-message-authorized-identity`. |
| Estado | Implementado y validado localmente; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Etapa 2 local como diagnostico parcial, sin cierre evidencial. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta commit, PR, CI, merge y limpieza, salvo instruccion explicita del usuario. |
| Siguiente accion | Cerrar paquete con commit, PR, CI, merge y limpieza del worktree tactico. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
