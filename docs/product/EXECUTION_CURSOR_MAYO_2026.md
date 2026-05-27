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
| Frente activo | Etapa 5 - Documentos, auditoria de formalizacion alineada con evidencia, firmas y notaria. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | El endpoint `formalizar/` registra auditoria, pero readiness solo comprobaba existencia del evento; debe exigir actor y metadata alineada con `evidencia_formalizacion_ref`, firmas, recepcion y comprobante notarial. |
| Motivo de prioridad | Brecha local de trazabilidad documental, cerrable sin storage real, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-document-formalization-audit-alignment`. |
| Rama | `codex/document-formalization-audit-alignment`. |
| Estado | En desarrollo. |
| Gate esperado | Tests focales de Documentos/readiness, suite `documentos`, `manage.py check`, migraciones dry-run, gate local Etapa 5 Documentos parcial, frontend build/lint si aplica, acceptance local, higiene y `git diff --check`. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Ningun bloqueo externo nuevo; no cierra Documentos sin fuente autorizada/prueba PDF controlada. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge/limpieza o pausar explicitamente aqui. |
| Siguiente accion | Completar implementacion, validar y cerrar el paquete. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
