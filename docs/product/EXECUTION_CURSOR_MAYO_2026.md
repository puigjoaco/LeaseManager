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
| Frente activo | Etapa 7 - referencias finales sensibles en readiness Reporting. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `audit_stage7_reporting_readiness` no clasifica explicitamente refs finales sensibles de ProcesoRentaAnual, DDJJ y F22; quedan diluidas como validacion de modelo. |
| Motivo de prioridad | Reporting debe bloquear referencias finales sensibles sin exponer valores y con diagnostico especifico antes del cierre trazable. |
| Worktree | `D:/Proyectos/LeaseManager-stage7-sensitive-final-ref-readiness`. |
| Rama | `codex/stage7-sensitive-final-ref-readiness`. |
| Estado | En implementacion local segura. |
| Gate esperado | Readiness Etapa 7 local queda `classification=parcial`, `ready_for_stage7_reporting=false`; no cierra etapa sin fuente autorizada, ledger, renta anual, API, backoffice y responsables. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Bloqueos externos de Reporting siguen como condicion de cierre, no bloquean hardening local. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge/limpieza o pausar explicitamente aqui. |
| Siguiente accion | Implementar issues especificos, tests, docs, validaciones y empaquetado. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
