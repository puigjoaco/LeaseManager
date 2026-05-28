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
| Frente activo | PlataformaBase / Compliance - estados terminales de exportaciones sensibles. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `ExportacionSensible` expirada es terminal para descarga, pero la revocacion operativa aun puede sobreescribir ese estado. |
| Motivo de prioridad | Frente local seguro de PlataformaBase/Compliance: endurece control de datos sensibles sin requerir `.env`, datos reales, DB historicas, backfills, deploys ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-export-terminal-state`. |
| Rama | `codex/compliance-export-terminal-state`. |
| Estado | Abierto para bloquear revocaciones sobre exportaciones expiradas o ya revocadas, cubrir readiness y evidencia. |
| Gate esperado | Tests focales Compliance/readiness, suite impactada Compliance/Core, `manage.py check`, migraciones dry-run, readiness local Compliance, frontend build/lint, acceptance local, higiene repo y CI remoto. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge o pausar explicitamente aqui si aparece un bloqueo real. |
| Siguiente accion | Implementar guard de estado terminal, actualizar tests/evidencia/trazabilidad y cerrar paquete. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
