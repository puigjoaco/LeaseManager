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
| Frente activo | Etapa 1 - Patrimonio. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | La transferencia patrimonial valida `evidence_ref` no sensible, pero permite que `motivo` con URL, token, correo o credencial quede persistido en `AuditEvent.metadata`. |
| Motivo de prioridad | Primer frente no cerrado en el orden de construccion; la stage card exige motivo/evidencia no sensibles para transferencias de participaciones. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-participation-transfer-reason-redaction`. |
| Rama | `codex/stage1-participation-transfer-reason-redaction`. |
| Estado | En desarrollo. |
| Gate esperado | Tests focales Patrimonio/Auditor Etapa 1, suite impactada, acceptance local y CI remoto verdes; no requiere fuentes externas. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar solo este worktree hasta PR/CI/merge/limpieza o pausar aqui con estado explicito. |
| Siguiente accion | Validar y auditar que el motivo de transferencia patrimonial no contenga referencias sensibles. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
