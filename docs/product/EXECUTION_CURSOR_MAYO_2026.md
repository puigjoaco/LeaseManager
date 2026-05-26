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
| Frente activo | Etapa 3 - readiness de supersesiones de resoluciones manuales con auditoria alineada. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `audit_stage3_conciliacion_readiness` valida metadata/motivo de `ManualResolution` `superseded`, pero debe bloquear tambien snapshots heredados sin `AuditEvent` `audit.manual_resolution.superseded` alineado. |
| Motivo de prioridad | Etapa 3 ya exige supersesion con evento auditable; sin este control el readiness puede aceptar una traza incompleta antes de cierre banco/conciliacion. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-superseded-audit-event`. |
| Rama | `codex/stage3-superseded-audit-event`. |
| Estado | En implementacion local segura. |
| Gate esperado | Readiness Etapa 3 local debe quedar `classification=parcial`, `ready_for_stage3_conciliacion=false`; no cierra etapa sin fuente autorizada y prueba bancaria/cuadratura. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Bloqueos externos de Etapa 3 siguen como condicion de cierre, no bloquean este hardening local. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge/limpieza o pausar explicitamente aqui. |
| Siguiente accion | Implementar test focal, readiness, docs, validaciones y empaquetado. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
