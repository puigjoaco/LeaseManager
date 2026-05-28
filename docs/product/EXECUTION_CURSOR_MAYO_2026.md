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
| Frente activo | `compliance-policy-api-redaction`. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | API de politicas de retencion de Compliance expone `evento_inicio` heredado crudo aunque admin y dominio ya lo tratan como sensible. |
| Motivo de prioridad | Primer frente incompleto por trazabilidad con brecha local cerrable sin datos externos: superficie API de Compliance datos sensibles. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-policy-api-redaction`. |
| Rama | `codex/compliance-policy-api-redaction`. |
| Estado | Validado localmente; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Compliance local sigue `parcial`; el paquete solo cierra redaccion API y no declara cierre de Compliance. |
| Estado al cerrar paquete | Pendiente PR, CI, merge y limpieza. Validacion local completa en verde. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta validacion, PR, CI, merge y limpieza antes de abrir otro frente. |
| Siguiente accion | Validar serializer, tests focales/impactados, gate Compliance local, acceptance, higiene y PR. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
