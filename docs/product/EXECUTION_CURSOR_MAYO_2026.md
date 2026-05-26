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
| Frente activo | Etapa 7 - referencias sensibles en evidencia de release gate. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `run-stage7-readiness-gate.ps1` distingue refs ausentes de refs no sensibles, pero algunas evidencias de restore/smoke/aceptacion con refs sensibles quedan clasificadas como faltantes genericos. |
| Motivo de prioridad | Operacion productiva debe diagnosticar evidencia sensible de cierre sin exponer valores y sin confundirla con ausencia de evidencia. |
| Worktree | `D:/Proyectos/LeaseManager-stage7-sensitive-release-evidence-refs`. |
| Rama | `codex/stage7-sensitive-release-evidence-refs`. |
| Estado | En implementacion local segura. |
| Gate esperado | Readiness Etapa 7 local queda `classification=parcial`, `ready_for_stage7_close=false`; no cierra Operacion productiva sin fuentes/evidencias autorizadas. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Restore autorizado, smoke publico autorizado, Reporting autorizado, observabilidad runtime autorizada y aceptacion final siguen como condicion de cierre externo. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge/limpieza o pausar explicitamente aqui. |
| Siguiente accion | Implementar codigos especificos para refs sensibles en evidencia de restore, smoke publico y aceptacion final, cubrir acceptance y actualizar trazabilidad/evidencia. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
